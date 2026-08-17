import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px

df = pd.read_csv("ludwig_analytics.csv")

#clean duration col in iso 8601 standard, will become time delta
df['duration'] = pd.to_timedelta(df['duration'])

#clean upload time
# raw API format: YYYY-MM-DDTHH:MM:SSZ (ISO 8601, UTC)
# upload_time format: YYYY-MM-DD HH:MM:SS+00:00 (UTC) offset from utc(coordinated universal time)
df['upload_time'] = pd.to_datetime(df['upload_time'])

#make an upload hour,date col
df['upload_date'] = df['upload_time'].dt.date
df['upload_hour'] = df['upload_time'].dt.hour


#make a column for shorts, max length is 3mins
df['is_short'] = df['duration'] <= pd.Timedelta(seconds= 90)

#rearrange column order
df = df[['title', 'views', 'likes', 'comment_count', 'duration', 'upload_time', 'upload_date', 'upload_hour', 'is_short', 'is_vod']]

#deal with overlap cases where the stream is less than 90s because of some announcement etc, anyway if it is a stream , it cannot be a short
df.loc[(df['is_short'] == True) & (df['is_vod'] == True), 'is_short'] = False

#get dataframe of only his videos
#& is normally a bitwise operator but it works in pandas to compare each row against each other like in this case, important to include parenthesis or else the False and is_vod will be grouped together 
df_videos = df[(df['is_short'] == False) & (df['is_vod'] == False)]
df_shorts = df[df['is_short'] == True]
df_vods = df[df['is_vod'] == True]

all_dfs = {
    'all' : df,
    'videos' : df_videos,
    'shorts' : df_shorts,
    'vods' : df_vods
}


#convert to file so that the plotting file can run it without doing the cleaning everytime
pd.to_pickle(all_dfs, 'ludwig_data.pkl')

#for the most part less than 90 sec is a good indicator of it being a youtube short but there are some outliers, music videos, old school youtube with shorter videos
#print(df[(df['duration'] <= pd.Timedelta(minutes = 3)) & (df['duration'] > pd.Timedelta(seconds= 90))])