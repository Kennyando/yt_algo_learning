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

print(df.shape, df_videos.shape, df_vods.shape, df_shorts.shape)
#plot views against time

#plot views against duration

#plot likes against views

#plot comments against views

#plot upload time by distribution can split in 2 graphs, all time and one for 2026 and 2025

#