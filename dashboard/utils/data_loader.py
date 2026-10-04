from functools import lru_cache
from pathlib import Path

import pandas as pd

# resolve next to the dashboard folder so the app works no matter where it is launched from
DATA_DIR = Path(__file__).resolve().parent.parent


@lru_cache(maxsize=1)
def load_data():
    """
    loads the cleaned data from the pickle file generated from clean_Data.py
    dfs are all, videos, shorts, vods
    """
    return pd.read_pickle(DATA_DIR / "ludwig_data.pkl")


@lru_cache(maxsize=1)
def load_channel_stats():
    """
    loads the general channel stats, total subs, views and upload counter
    """
    return pd.read_pickle(DATA_DIR / "ludwig_channel_stats.pkl")


@lru_cache(maxsize=1)
def data_as_of():
    """
    when the data was last pulled from the API (pickle's modified time).
    used to hide the current, still-incomplete month from the monthly charts
    """
    return pd.Timestamp((DATA_DIR / "ludwig_data.pkl").stat().st_mtime, unit="s", tz="UTC")
