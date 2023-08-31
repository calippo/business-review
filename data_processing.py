import pandas as pd

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

status_weights = {
    'Won': 1.0,
    'In formal signing': 0.8,
    'In Negotiation': 0.65,
    'Committed to offer': 0.5,
    'Backlog': 0.1,
}

def column_to_status(column_name: str):
    won = 'Won'
    match column_name:
        case 'In Negotiation' | 'Committed to offer' | 'Opportunities' | 'In formal signing' | 'Lost' | 'Backlog':
            return column_name
        case 'Active contract' | 'Expired' | 'Expired, with actions or invoices pending':
            return won

statuses = list(status_weights.keys())

def process_opportunities(opportunities, year_):
    opportunities['year'] = opportunities['date'].apply(year)
    opportunities['quarter'] = opportunities['date'].apply(quarter)
    opportunities['oyov'] = opportunities['value']
    opportunities['status'] = opportunities['status'].apply(lambda x: column_to_status(x))
    #opportunities = opportunities[(opportunities['status'] != 'Lost') & (opportunities['status'] != 'Backlog') & (opportunities['status'] != 'Active contract')]
    remove = opportunities[~(opportunities['status'].isin(status_weights.keys()))]
    opportunities = opportunities[opportunities['status'].isin(status_weights.keys())]
    opportunities['weight'] = opportunities['status'].apply(lambda x: status_weights[x])
    opportunities['weighted_oyov'] = opportunities[['oyov', 'status']].apply(lambda o: o[0] * status_weights[o[1]], axis=1)
    opportunities['hr_weighted_oyov'] = opportunities['weighted_oyov'].apply(lambda x: f'{x:9.2f} k€')
    opportunities['hr_oyov'] = opportunities['oyov'].apply(lambda x: f'{x:9.2f} k€')
    all_time_opportunities = opportunities[['weighted_oyov', 'source', 'date', 'title']]
    this_year_opportunities = opportunities[opportunities['year'] == year_]
    return (all_time_opportunities, this_year_opportunities)