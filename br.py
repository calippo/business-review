import streamlit as st

# Import numeric libraries
# The following libraries depend on `numpy`, in case this causes issues try changing kernel

import pandas as pd
import numpy as np

# Plotting library imports and configurations
from bokeh.palettes import Paired, viridis
from bokeh.plotting import figure
from bokeh.models import ColumnDataSource, BasicTickFormatter, FactorRange
from bokeh.transform import factor_cmap
from bokeh.layouts import layout

import jira_client
from data_processing import statuses, process_opportunities

opportunities = pd.DataFrame.from_dict(jira_client.issues())


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

(all_time_opportunities, opportunities) = process_opportunities(opportunities, YEAR)
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
The "ordered value" is computed by considering the value of each opportunity for both the current year and the next year.
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
The "ordered value" is computed by considering the value of each opportunity for both the current year and the next year.
""")

st.bokeh_chart(p)

st.write("""
# Customer acquisition source
""")

def customerAcquisition(df):
    df = df.dropna(subset=['source', 'date'])
    df['date'] = pd.to_datetime(df['date'])
    
    # Extract year and quarter
    df['year_quarter'] = df['date'].dt.to_period("Q").astype(str)
    
    # Convert source column to string to avoid comparison errors
    df['source'] = df['source'].astype(str)
    
    # Pivot table
    pivot_df = df.pivot_table(index='year_quarter', columns='source', values='weighted_oyov', aggfunc='sum', fill_value=0)
    pivot_df = pivot_df.reset_index()
    
    # Sort by year_quarter
    pivot_df = pivot_df.sort_values(by='year_quarter')
    
    source = ColumnDataSource(pivot_df)
    sources = sorted(df['source'].unique().tolist())
    
    # Create figure
    p = figure(y_range=FactorRange(*pivot_df['year_quarter'].astype(str).unique()), height=350, width=800,
               title="Weighted Oyov per Source Grouped by Year-Quarter",
               tooltips='$name: @$name{int} k€',
               toolbar_location='right')
    
    # Horizontal stacked bars
    p.hbar_stack(sources, y='year_quarter', height=0.4, color=colors,
                 source=source, legend_label=["%s" % x for x in sources])
    
    # Customize the plot
    p.y_range.range_padding = 0.1
    p.legend.title = 'Source'
    p.legend.location = "top_right"
    
    # Set x-axis label to indicate unit of measure in k euros
    p.xaxis.axis_label = 'Amount (k€)'
    
    return p

st.bokeh_chart(customerAcquisition(all_time_opportunities))
