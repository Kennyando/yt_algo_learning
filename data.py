#this will be where i get adn store the data from youtube
from dotenv import load_dotenv
import os
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import pandas as pd
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
#items is a list with one item so indexing 0 will give you everything
upload_playlist_id = lugwig_yt['items'][0]['contentDetails']['relatedPlaylists']['uploads']

next_page_token = None
all_video_ids = []

#use while to parse through all uploads
while True:
    playlist_items_request = youtube.playlistItems().list(
        part = 'snippet,contentDetails',
        playlistId = upload_playlist_id,
        maxResults = 50, #edit to 50 after the rest of the stuff works
        pageToken = next_page_token
    ) #http request object , when printed is giving the memory location in computer, need to execute to get the response

    playlist_items_response = playlist_items_request.execute() #this one actually returns the videos 

    #index into the video stats from this video is under id
    #storing video id and position into dictionary
    video_ids = {}
    #api docs for playlist structure https://developers.google.com/youtube/v3/docs/playlistItems#resource
    #append the 50 into the list
    for item in playlist_items_response['items']:
        all_video_ids.append(item['contentDetails']['videoId'])

    #get next page token, get to get a dictionary value, if no next page token None is return
    next_page_token = playlist_items_response.get('nextPageToken')

    #break if no more page token not None = True
    if not next_page_token:
        break

# need to batch the video id list to 50 each because the api will only take in 50 per call
#need to get the video using video function, construct the object first
#dict will give you the key, so id in this case will give the number and you need to index into the dictionary
for i in range(0, len(all_video_ids), 50):
    chunk = all_video_ids[i:i+50]
    id_string = ','.join(chunk) #convert to string so can pass as a parameter

    video_stats = youtube.videos().list(
        part = 'snippet,statistics,contentDetails,LiveStreamingDetails',
        id = id_string
    )

    video_stats_response = video_stats.execute() #contains the batch of 50 videos

    rows_data = [] #initialize list to store dict and then subsequently pass that as a pandas dataframe
    for video in video_stats_response['items']:
        #items is a list with only one entry
        title = video['snippet']['localized']['title']
        views = video['statistics']['viewCount']
        likes = video['statistics']['likeCount']
        comment_count = video['statistics']['commentCount']
        duration = video['contentDetails']['duration']
        upload_time = video['snippet']['publishedAt']
        is_vod = 'liveStreamingDetails' in video

        #append to dictionary
        rows_data.append({
            'title': title,
            'views': views,
            'likes': likes,
            'comment_count': comment_count,
            'duration': duration,
            'upload_time': upload_time,
            'is_vod': is_vod
        })

#convert to pd dataframe
df = pd.DataFrame(rows_data)

print(df)

#consider converting to csv and just making the thing a function so i just need to run it once and its done
#it almost works but is only calling out 13 videos now

#filter out only videos from the list 'kind': 'youtube#video', currently includes shorts, 
#maybe try using contentDetails.duration to filter out <5 mins and > 1hr videos
#contentDetails.duration uses ISO8601 
#metrics i want to measure, view count, like count, comment count, upload time, frequency between uploads, title, description tags
#description of live streams have #live
#shorts

#github https https://github.com/Kennyando/yt_algo_learning.git