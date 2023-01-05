import streamlit as st
# Import basic libraries
import requests

# Import numeric libraries
# The following libraries depend on `numpy`, in case this causes issues try changing kernel

import pandas as pd
import numpy as np

# Plotting library imports and configurations
from bokeh.palettes import Paired
from bokeh.plotting import figure
from bokeh.models import ColumnDataSource, BasicTickFormatter

import jira_client

opportunities = pd.DataFrame.from_dict(jira_client.issues())

def column_to_status(column_name: str):
    won = 'Won'
    match column_name:
        case 'In Negotiation' | 'Committed to offer' | 'Opportunities' | 'In formal signing' | 'Lost' | 'Backlog':
            return column_name
        case 'Active contract' | 'Expired' | 'Expired, with actions or invoices pending':
            return won

st.title('Monthy Business Review')

st.write("""
Objective: monthly evaluation of the sales pipeline and cumulative ordered value per quarter.

Summary:

- Sales Pipeline
- Business Review by quarter
- Customers
- New Business

"""
)

TARGET_DEFAULT = st.secrets["TARGET_DEFAULT"]
TARGET = st.number_input('Insert target', value=TARGET_DEFAULT)
YEAR = st.number_input('Insert year', value=2023)

status_weights = {
    'Won': 1.0,
    'In formal signing': 0.8,
    'In Negotiation': 0.65,
    'Committed to offer': 0.5,
    'Opportunities': 0.1,
}

statuses = list(status_weights.keys())

#def expected_closing_date(json):
#    d = json.get('id_15322')
#    if (d is None):
#        d = json.get('id_15321')
#    if (d is None):
#        return None
#    return d['date']

def quarter(j):
    if j is None:
        return None
    else:
        return pd.to_datetime(j).quarter

def year(j):
    if j is None:
        return None
    else:
        return int(j[:4])

opportunities['year'] = opportunities['date'].apply(year)
opportunities['quarter'] = opportunities['date'].apply(quarter)
opportunities['oyov'] = opportunities['value']
opportunities['status'] = opportunities['status'].apply(lambda x: column_to_status(x))
remove = opportunities[(opportunities['status'] == 'Lost') | (opportunities['status'] == 'Backlog')]
#opportunities = opportunities[(opportunities['status'] != 'Lost') & (opportunities['status'] != 'Backlog') & (opportunities['status'] != 'Active contract')]
opportunities = opportunities[opportunities['status'].isin(status_weights.keys())]
opportunities['weight'] = opportunities['status'].apply(lambda x: status_weights[x])
opportunities['weighted_oyov'] = opportunities[['oyov', 'status']].apply(lambda o: o[0] * status_weights[o[1]], axis=1)
opportunities['hr_weighted_oyov'] = opportunities['weighted_oyov'].apply(lambda x: f'{x:9.2f} k€')
opportunities['hr_oyov'] = opportunities['oyov'].apply(lambda x: f'{x:9.2f} k€')
opportunities = opportunities[opportunities['year'] == YEAR]

won_opportunities=opportunities[opportunities['status']=='Won'].sort_values(
    by=['weight', 'weighted_oyov'], ascending=[0, 0])[
    ['title', 'hr_oyov', 'hr_weighted_oyov', 'status', 'weight']]

st.write("""
# Won opportunities
""")
st.table(won_opportunities)

major_opportunities=opportunities[opportunities['status']!='Won'].sort_values(
    by=['weight', 'weighted_oyov'], ascending=[0, 0])[
    ['title', 'hr_oyov', 'hr_weighted_oyov', 'status', 'weight']]

st.write("""
# Sales Pipeline
Open opportunities sorted by status and weighted oyov.
""")

st.table(major_opportunities)

ordered_value = "weighted_oyov"
group = opportunities[[ordered_value, 'quarter', 'status']].groupby(['quarter', 'status']).sum()
quarters = ['1', '2', '3', '4']

data = { s:[group[ordered_value].get((int(q), s), default=0) for q in quarters] + [0, 0]
        for s in statuses }
data['Baseline'] = [0] + list(np.cumsum([sum([group[ordered_value].get((int(q), s), default=0) for s in statuses])
        for q in quarters ]))[:-1] + [0, 0]

data['Target'] = [0, 0, 0, 0, TARGET, 0]
gap = TARGET - sum([d[3] for d in data.values()])
data['Gap'] = [0, 0, 0, 0, 0, gap]

data['quarters'] = quarters + ['Target'] + ['Gap']

def filterBaseline(data):
    import pandas as pd
    import datetime as dt
    quarter = pd.Timestamp(dt.date.today()).quarter
    data['Baseline'] = [0 if i >= quarter else x for i, x in enumerate(data['Baseline'])]
    return data

#data = filterBaseline(data)
source = ColumnDataSource(data)

from bokeh.palettes import Spectral6
colors = ['#d3d3d3'] + list(Spectral6)[:5] + ['#016450', '#872300']
statusesWBaseline = ['Baseline'] + statuses + ['Target'] + ['Gap']

p = figure(x_range=data['quarters'], title='Weighted oyov by quarter'
           , tooltips='$name: @$name{int} k', plot_height=500, plot_width=900)
p.yaxis.formatter = BasicTickFormatter(use_scientific=False)

p.y_range.start = 0
p.x_range.range_padding = 0.1
p.xgrid.grid_line_color = None
p.axis.minor_tick_line_color = None
p.outline_line_color = None

p.vbar_stack(statusesWBaseline, x='quarters', source=data,
             legend_label=statusesWBaseline, fill_color=colors,
             line_color='white',
             hatch_color='white',
             hatch_alpha=0.05,
            hatch_pattern=['criss_cross', 'blank', 'blank','blank','blank','blank','diagonal_cross','cross'])
p.legend.location = 'top_left'

st.write("""
# Ordered value by quarter
""")

st.bokeh_chart(p, use_container_width=True)

customers = st.secrets["CUSTOMERS"]

def mapToCustomer(title):
    splitted = title.split("-")
    if len(splitted) > 1:
        return splitted[0].strip()
    else:
        return title.split("—")[0].strip()
    # for c in customers:
    #     if c.lower() in title.lower():
    #         return c
    # return np.nan

opportunities['customer'] = opportunities['title'].apply(mapToCustomer)
#opportunities[opportunities['customer'].isnull()][['title', 'oyov']]

group = opportunities[['weighted_oyov', 'oyov']].groupby(opportunities['customer']).sum()
group['oyov_diff']=group['oyov'] - group['weighted_oyov']
ordered = group.sort_values(by=['oyov_diff'], ascending=[0])
group=group[['weighted_oyov','oyov_diff']]
source = ColumnDataSource(group)

colors = list(Paired[3][:2])
colors.reverse()

p = figure(y_range=list(ordered.index)[::-1], title='Customers by oyov', toolbar_location='right', plot_height=500, plot_width=900,
          tooltips='$name: @$name{int} k€')

p.hbar_stack(['weighted_oyov', 'oyov_diff'], line_color='white', y='customer', color=colors,source=source, legend_label=['weighted oyov', 'oyov diff'])
p.legend.location = 'bottom_right'

st.write("""
# Customers by required focus
""")

st.bokeh_chart(p)

#kaitenUrl = st.secrets["SALES_PIPELINE_BOARD"]
#headers = {
#    'Content-Type': 'application/json',
#    'Authorization': f'Bearer {kaitenToken}'
#}
#res = requests.get(kaitenUrl, headers=headers)
#prospects = pd.DataFrame.from_dict(res.json()['cards'])
#hot = prospects[prospects['column_id']==308017]
#
#st.write("""
## New Business
### Hot Prospects
#""")
#
#st.table(hot[['title', 'created', 'updated']])
