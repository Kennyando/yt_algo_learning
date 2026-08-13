#this will be where i get adn store the data from youtube
from dotenv import load_dotenv
import os
import requests
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import pandas as pd
import json
import time
from pprint import pprint

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
lugwig_yt =youtube.channels().list(part = 'statistics,contentDetails,snippet',
                                  id = channel_id,
                                  ).execute()
#keys that i may want to index into 
#relatedPlaylists, uploads
upload_playlist_id = lugwig_yt['items'][0]['contentDetails']['relatedPlaylists']['uploads']

playlist_items_request = youtube.playlistItems().list(
    part = 'snippet,contentDetails',
    playlistId = upload_playlist_id,
    maxResults = 50
) #http request object , when printed is giving the memory location in computer, need to execute to get the response

playlist_items_response = playlist_items_request.execute() #this one actually returns the videos 

#index into the video stats from this video is under id
#storing video id and position into dictionary
video_ids = {}
#api docs for playlist structure https://developers.google.com/youtube/v3/docs/playlistItems#resource
for item in playlist_items_response['items']:
    position = item['snippet']['position']
    id = item['contentDetails']['videoId']
    video_ids[position] = id

#need to get the video using video function, construct the object first
#dict will give you the key, so id in this case will give the number and you need to index into the dictionary
for id in video_ids:
    video_stats = youtube.videos().list(
        part = 'snippet,statistics',
        id = video_ids[id]
    )
    video_stats_response = video_stats.execute()
    pprint(video_stats_response)

#github https https://github.com/Kennyando/yt_algo_learning.git