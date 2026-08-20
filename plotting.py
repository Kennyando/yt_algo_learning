import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import pandas as pd
import numpy as np

#import data from other file over
all_dfs = pd.read_pickle('ludwig_data.pkl')
df = all_dfs['all']
df_videos = all_dfs['videos']
df_vods = all_dfs['vods']
df_shorts = all_dfs['shorts']

print(df.info())
print(df.head())
#need to figure out how to do the dashboarding thing
#plot views against time scatter is better
fig = px.scatter(df_videos, x = 'upload_date', y = 'views', title = 'views per video over channel lifespan')
fig.show()

#plot views against duration


#plot likes against views


#plot comments against views


#plot upload time by distribution can split in 2 graphs, all time and one for 2026 and 2025

#