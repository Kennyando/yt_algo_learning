#this will be where i get adn store the data from youtube
from dotenv import load_dotenv
import os
import requests
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import pandas as pd
import json
import time


load_dotenv()
api_key = os.getenv("YOUTUBE_API_KEY")

#construct object to interact with the youtube api
youtube = build("youtube",'v3', developerKey = api_key)

#get channel id from youtube website with cltr f 
channel_id = 'UCrPseYLGpNygVi34QpGNqpA' #ludwigs channel id
#search query and video upload costs 1 unit of 

#use youtube object to do function calls or class methods
#youtube.<resource>().<method>(<parameters>).execute()
#channels list
response =youtube.channels().list(part = 'contentDetails',
                                  id = channel_id,
                                  ).execute()

print(response)

#github https https://github.com/Kennyando/yt_algo_learning.git