import pandas as pd

def load_data():
    """
    loads the cleaned data from the pickle file generated from clean_Data.py
    dfs are all, videos, shorts, vods
    """
    all_dfs = pd.read_pickle('ludwig_data.pkl')
    return all_dfs