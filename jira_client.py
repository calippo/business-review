from jira import JIRA
import os

JIRA_TOKEN = os.getenv('JIRA_TOKEN')
jira = JIRA(server="https://buildo.atlassian.net", basic_auth=('claudio@buildo.io', JIRA_TOKEN))



def get_fields(i):
    summary = i.fields.summary
    #customfield_10089 value this year 
    #customfield_10087 expected closing date
    #customfield_10090 next year
    value_next_year = i.fields.customfield_10090
    value = i.fields.customfield_10089
    if value_next_year is None:
        value = value
    elif value is None:
        value = value_next_year
    else:
        value = value + value_next_year
    date = i.fields.customfield_10087
    status = i.fields.status.name
    project = i.fields.project.name
    source = i.fields.customfield_10119
    return {
        "title": summary,
        "value": value,
        "value_next_year": value_next_year,
        "date": date,
        "status": status,
        "project": project,
        "source": source
    }

def issues():
    issues_in_proj = jira.search_issues('project=TPCCCM AND issuetype=Task AND component="Customer contracts"', maxResults=100)
    field_map = {field['name']: field['id'] for field in jira.fields()}
    issues = [get_fields(i) for i in issues_in_proj]
    return issues