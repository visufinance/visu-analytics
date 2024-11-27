import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import boto3
from boto3.dynamodb.conditions import Key
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

table = dynamodb.Table('visuAnalytics')


# Set the title and favicon that appear in the Browser's tab bar.
st.set_page_config(
    page_title='VISU Analytics',
    page_icon=':earth_americas:', # This is an emoji shortcode. Could be a URL too.
    layout='wide'
)

# -----------------------------------------------------------------------------
# Declare some useful functions.


# Function to convert seconds to hours, minutes, and seconds
def convert_seconds(seconds):
    hours = round(seconds // 3600)
    minutes = round((seconds % 3600) // 60)
    seconds = round(seconds % 60)
    result = []
    if hours > 0:
        result.append(f"{hours} hour{'s' if hours > 1 else ''}")
    if minutes > 0:
        result.append(f"{minutes} minute{'s' if minutes > 1 else ''}")
    if seconds > 0 or not result:
        result.append(f"{seconds} second{'s' if seconds > 1 else ''}")
    return ', '.join(result)


@st.cache_data(ttl='120')
def get_db_data(delta_t='Today'):
    if delta_t == 'Today':
        start_date = pd.Timestamp('now', tz='America/New_York').replace(hour=0, minute=0, second=0, microsecond=0)
    elif delta_t == 'Last 24 hours':
        start_date = datetime.now() - timedelta(hours=25)
    elif delta_t == 'Last 7 days':
        start_date = datetime.now() - timedelta(days=7)
    elif delta_t == 'Last 30 days':
        start_date = datetime.now() - timedelta(days=30)
    elif delta_t == 'Last 90 days':
        start_date = datetime.now() - timedelta(days=90)
    elif delta_t == 'Last year':
        start_date = datetime.now() - timedelta(days=365)
    start_date = int(start_date.timestamp()) * 1000

    response = table.query(
        IndexName='timestamp-index',
        KeyConditionExpression=Key('dummy').eq('d') & Key('createdAt').gt(start_date),
        ScanIndexForward=False,
        # Limit=1
    )
    if 'LastEvaluatedKey' in response.keys():
        st.subheader('Table larger than 1MB. Response is paginated.')

    return response['Items']



# -----------------------------------------------------------------------------
# Draw the actual page

# Set the title that appears at the top of the page.
'''
# :earth_americas: Visu Analytics
'''

# Add some spacing
''
''
''
''

options = ['Today', 'Last 24 hours', 'Last 7 days', 'Last 30 days', 'Last 90 days', 'Last year']
delta_t = st.segmented_control(
    "a", options, selection_mode="single", default=['Today'], label_visibility='collapsed'
)
if delta_t:
    df = pd.DataFrame(get_db_data(delta_t))
else:
    st.stop()

''
''

filter_cities = st.multiselect(
    "Filter cities",
    df.city.dropna().unique()
)

''
''
''
''

if filter_cities:
    dff = df[['uat','city']].loc[df.city.isin(filter_cities)].copy()
    dff = dff.drop_duplicates()
    uats = dff.uat.dropna().unique()
    df = df.loc[~df.uat.isin(uats)].copy()


df.createdAt = df.createdAt.astype(int)
df['date'] = pd.to_datetime(
    df['createdAt'], unit='ms'
).dt.tz_localize('UTC').dt.tz_convert('America/Sao_Paulo') #'America/New_York'
df = df.sort_values(by='createdAt', ascending=False)
df.insert(0, 'date', df.pop('date'))

# front_cols = ['date', 'uat', 'saidi', 'referrer', 'urlParams', 'country', 'region', 'city', 'operatingSystem', 'deviceType', 'browser']
# back_cols = [i for i in df.columns if i not in front_cols]
# df = df[front_cols + back_cols]
# st.dataframe(df, hide_index=True)


dfg = df.copy()
if delta_t in ['Today', 'Last 24 hours', 'Last 7 days']:
    dfg['date_str'] = dfg.date.dt.strftime('%b. %d, %-I%p')
else:
    dfg['date_str'] = dfg.date.dt.strftime('%b. %d, %Y')

df_users = dfg[['date_str','uat']].drop_duplicates(keep='first').groupby(['date_str']).count()

dfg['Events'] = 1
df_events = dfg[['date_str','Events']].groupby(['date_str']).sum()


df_events = pd.concat([df_users, df_events], axis=1)
df_events.rename(columns={'uat':'Unique Visitors'}, inplace=True)

order = dfg.sort_values(by='createdAt', ascending=False)['date_str'].drop_duplicates().to_list()
order.reverse()

df_events.reset_index(inplace=True)
df_events['date_str'] = pd.Categorical(df_events['date_str'], categories=order, ordered=True)
df_events = df_events.sort_values('date_str')
df_events.set_index('date_str', inplace=True)
st.bar_chart(df_events, height=450)


''
''

unique_visitors = len(df.uat.unique())
total_events = len(df)
col1, col2, col3 = st.columns(3, gap='large')
with col1:
    st.subheader('Unique Visitors')
    st.subheader(unique_visitors)

with col2:
    st.subheader('Events')
    st.subheader(total_events)

''
''
''
''

col1, col2, col3 = st.columns(3, gap='large')
with col1:
    st.subheader("Countries")
    dfc = pd.DataFrame(df['country'].value_counts())
    dfc['%'] = (dfc / dfc.sum() * 100).round(2)
    dfc['%'] = dfc['%'].astype(str) + '%'
    st.write(dfc)

with col2:
    st.subheader("URL Params")
    st.dataframe(df['urlParams'].value_counts())

with col3:
    st.subheader("Referrers")
    st.dataframe(df['referrer'].value_counts())
    

''
''
''
''


col1, col2 = st.columns(2, gap='large')
with col1:
    st.subheader("Dash Layouts")
    st.bar_chart(df['dashLayout'].value_counts(), horizontal=True)

with col2:
    st.subheader("Page Views")
    st.bar_chart(df['pageView'].value_counts(), horizontal=True)


''
''
''
''


col1, col2, col3 = st.columns(3, gap='large')
with col1:
    st.subheader("Read More Clicks")
    if 'readMoreClick' in df.columns:
        metric = df['readMoreClick'].value_counts().sum()
    else:
        metric = 0
    st.subheader(str(metric))

with col2:
    st.subheader("Dash Dropdown Change")
    if 'dashDropdownChange' in df.columns:
        metric = df['dashDropdownChange'].value_counts().sum()
    else:
        metric = 0
    st.subheader(str(metric))

with col3:
    st.subheader("Ping Clicks")
    if 'pingClick' in df.columns:
        metric = df['pingClick'].value_counts().sum()
    else:
        metric = 0
    st.subheader(str(metric))

''
''
''
''

col1, col2, col3 = st.columns(3, gap='large')
with col1:
    st.subheader("Mini-Chart Clicks")
    if 'miniChartClick' in df.columns:
        metric = df['miniChartClick'].value_counts().sum()
    else:
        metric = 0
    st.subheader(str(metric))

with col2:
    st.subheader("Fundamentals Scroll")
    if 'fundTab' in df.columns:
        metric = df['fundTab'].value_counts().sum()
    else:
        metric = 0
    st.subheader(str(metric))


''
''
''
''


col1, col2, col3 = st.columns(3, gap='large')
with col1:
    st.subheader("Article Clicks")
    if 'articleClick' in df.columns:
        metric = df['articleClick'].value_counts().sum()
    else:
        metric = 0
    st.subheader(str(metric))

with col2:
    st.subheader("News Type")
    if 'newsType' in df.columns:
        metric = df['newsType'].value_counts()
    else:
        metric = 0
    st.write(metric)

''
''
''
''


st.header('Unique visits by country and city')
dfg = df[['country','region','city']].copy()
dfg['count'] = 1
dfg = dfg.groupby([
    'country','region','city'
]).count().sort_values(by='count', ascending=False)
dfg.reset_index(inplace=True)
st.dataframe(dfg, hide_index=True)

''
''

st.header('Unique visits by token and location')
dfg = df[['uat','country','region','city']].copy()
dfg['count'] = 1
dfg = dfg.groupby([
    'uat','country','region','city'
]).count().sort_values(by='count', ascending=False)
dfg.reset_index(inplace=True)
st.dataframe(dfg, hide_index=True)

''
''

# SESSION DURATION
st.header('Session duration')
df_first = df[['uat','saidi','createdAt']].groupby(['uat','saidi']).first()
df_last = df[['uat','saidi','createdAt']].groupby(['uat','saidi']).last()
df_first = pd.concat([df_first, df_last], axis=0)
df_duration = df_first.sort_values(by=['uat','saidi','createdAt'], ascending=True)
df_duration = df_duration.groupby(['uat','saidi']).diff().dropna()
df_duration.rename(columns={'createdAt':'seconds'}, inplace=True)
df_duration.seconds = (df_duration.seconds / 1000).round(0)
df_duration['totalTime'] = df_duration.seconds.apply(convert_seconds)
df_cols = df[['uat','saidi','country','region','city','deviceType']].copy().dropna(subset='country')
df_duration = df_duration.merge(df_cols, how='left', on='saidi')

df_params = df[['saidi','urlParams']].copy()
df_params.urlParams = df_params.urlParams.astype(str)
df_params.urlParams = df_params.urlParams.replace('[]', None)
df_params.urlParams = df_params.urlParams.replace('nan', None)
df_params = df_params.dropna(subset='urlParams').drop_duplicates()
df_duration = df_duration.merge(df_params, how='left', on='saidi')

df_params = df[['saidi','referrer']].copy()
df_params.referrer = df_params.referrer.astype(str)
df_params.referrer = df_params.referrer.replace('nan', None)
df_params = df_params.dropna(subset='referrer').drop_duplicates()
df_duration = df_duration.merge(df_params, how='left', on='saidi')
df_duration.referrer = df_duration.referrer + ' ' + df_duration.urlParams
df_duration.drop(columns='urlParams', inplace=True)
df_duration.drop_duplicates(inplace=True)

df_duration = df_duration.sort_values(by='seconds', ascending=False)
df_duration = df_duration[['uat','saidi','country','region','city','deviceType','referrer','totalTime']]
st.dataframe(df_duration.reset_index(drop=True), hide_index=True)


# USER INTERACTIONS
st.header('Interactions count')
dff = df[['uat','country','region','city','deviceType']].dropna().reset_index(drop=True)
dff = dff.drop_duplicates()
dfsc = pd.DataFrame(df.uat.value_counts()).reset_index()
dfsc = dfsc.merge(dff, how='left', on='uat')
dfsc = dfsc[['uat','country','region','city','deviceType','count']]
st.dataframe(dfsc, hide_index=True)


# SESSION LOOKUP
st.header('Session lookup')
useID = st.toggle('Use session ID', False)
filter_field = 'saidi' if useID else 'uat'
token = st.text_input('a', placeholder=f'Enter a {filter_field} to see the full session', label_visibility='collapsed')
if token:
    dfu = df.loc[df[filter_field] == token].copy()
    remove_cols = ['uat','country','region','operatingSystem','deviceType','browser','ttl','createdAt','dummy','deviceType','isMobile','clientInfo']
    dfu = dfu.sort_values(by='createdAt', ascending=True)
    dfu.urlParams = dfu.urlParams.astype(str)
    dfu.urlParams = dfu.urlParams.replace('nan', None)
    dfu = dfu.drop(columns=remove_cols)
    sessions = dfu.saidi.unique()
    for i, sess in enumerate(sessions):
        st.subheader(f'Session {i+1}')
        dfs = dfu.loc[dfu.saidi == sess].copy()
        dfs.dropna(axis=1, how='all', inplace=True)
        if 'referrer' in dfs.columns:
            referrers = dfs.referrer.dropna().unique()
            referrers = ', '.join(referrers)
            st.write('Referrers:', referrers or 'None')
        if 'urlParams' in dfs.columns:
            url_params = dfs.urlParams.dropna().unique()
            st.write('URL Params:', str(url_params) or 'None')
        cols_to_use = ['saidi','referrer','urlParams']
        cols = [i for i in cols_to_use if i in dfs.columns]
        if len(cols) > 0:
            dfs = dfs.drop(columns=['saidi','referrer','urlParams'])
        dfs.date = dfs.date.dt.strftime('%b. %d, %Y %H:%M:%S')
        st.dataframe(dfs, hide_index=True)

''
''
''
''

st.header('Last sessions')
n_sessions = st.number_input('Show last sessions:', min_value=0, max_value=50, value=0)
if n_sessions > 0:
    sessions = df.saidi.drop_duplicates(keep='first').to_list()[:n_sessions]
    cols_to_use = [
        'date', 'pageView', 'urlParams', 'country', 'city', 'region', 'deviceType', 'referrer', 'dashLayout',
        'readMoreClick', 'articleClick', 'pingClick', 'miniChartClick', 'filingClick', 'fundTab', 'dashDropdownChange',
    ]
    cols = [i for i in cols_to_use if i in df.columns]
    for sess in sessions:
        col1, col2 = st.columns([2, 10], gap='small')
        with col1:
            st.write(f'Session ID:')
        with col2:
            st.write(sess)
        dfs = df.loc[df.saidi == sess].sort_values(by='createdAt', ascending=True).copy()
        uat = dfs.uat.dropna().unique()[0]
        dfs = dfs[cols].copy()
        col1, col2 = st.columns([2, 10], gap='small')
        with col1:
            st.write(f'UAT:')
        with col2:
            st.write(uat)
        dfs.fillna('EMPTY', inplace=True)
        dfs.set_index('date', inplace=True)
        for i, row in enumerate(dfs.itertuples(index=False)):
            col1, col2 = st.columns([2, 10], gap='small')
            row = row._asdict()
            row = {k: v for k, v in row.items() if v != 'EMPTY'}
            with col1:
                st.write(dfs.index[i].strftime('%b. %d, %Y %H:%M:%S'))
            with col2:
                for k, v in row.items():
                    st.write(f'**{k}**: \u0020\u0020 {v}')
            st.write('')
        st.write('---')
