from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

class YouTubeClient:
    def __init__(self):
        # Get API key from environment variables
        self.api_key = os.environ.get('YOUTUBE_API_KEY')
        if not self.api_key:
            raise ValueError("YouTube API key not found. Set YOUTUBE_API_KEY in .env file.")
        
        print(f"Using YouTube API key from environment variables")
        self.max_results = 10
        self.youtube = build('youtube', 'v3', developerKey=self.api_key)
    
    def search_videos(self, query, max_results=None, order=None, video_duration=None, published_after=None, published_before=None):
        """Search for videos matching the query with advanced filters"""
        try:
            if max_results is None:
                max_results = self.max_results
            
            # Build search parameters
            search_params = {
                'q': query,
                'part': 'snippet',
                'maxResults': max_results,
                'type': 'video'
            }
            
            # Add optional parameters if provided
            if order and order != 'relevance':
                search_params['order'] = order
            
            if video_duration:
                search_params['videoDuration'] = video_duration
            
            if published_after:
                search_params['publishedAfter'] = published_after
            
            if published_before:
                search_params['publishedBefore'] = published_before
            
            search_response = self.youtube.search().list(**search_params).execute()
            
            videos = []
            for item in search_response.get('items', []):
                video = {
                    'id': item['id']['videoId'],
                    'title': item['snippet']['title'],
                    'description': item['snippet']['description'],
                    'thumbnail': item['snippet']['thumbnails']['high']['url'],
                    'channel': item['snippet']['channelTitle'],
                    'published_at': item['snippet']['publishedAt']
                }
                videos.append(video)
            
            return videos
        
        except HttpError as e:
            print(f"An HTTP error {e.resp.status} occurred: {e.content}")
            return []
    
    def get_video_details(self, video_id):
        """Get detailed information about a specific video"""
        try:
            video_response = self.youtube.videos().list(
                part='snippet,contentDetails,statistics',
                id=video_id
            ).execute()
            
            if not video_response.get('items'):
                return None
                
            item = video_response['items'][0]
            video_details = {
                'id': item['id'],
                'title': item['snippet']['title'],
                'description': item['snippet']['description'],
                'published_at': item['snippet']['publishedAt'],
                'channel': item['snippet']['channelTitle'],
                'tags': item['snippet'].get('tags', []),
                'category_id': item['snippet']['categoryId'],
                'duration': item['contentDetails']['duration'],
                'view_count': item['statistics'].get('viewCount', 0),
                'like_count': item['statistics'].get('likeCount', 0),
                'comment_count': item['statistics'].get('commentCount', 0)
            }
            
            return video_details
            
        except HttpError as e:
            print(f"An HTTP error {e.resp.status} occurred: {e.content}")
            return None
    
    def get_video_comments(self, video_id, max_results=None, page_token=None):
        """Get comments for a specific video with pagination support"""
        try:
            if max_results is None:
                max_results = self.max_results
            
            params = {
                'part': 'snippet',
                'videoId': video_id,
                'maxResults': max_results,
                'textFormat': 'plainText'
            }
        
            if page_token:
                params['pageToken'] = page_token
            
            comments_response = self.youtube.commentThreads().list(**params).execute()
        
            comments = []
            for item in comments_response.get('items', []):
                comment = {
                    'id': item['id'],
                    'text': item['snippet']['topLevelComment']['snippet']['textDisplay'],
                    'author': item['snippet']['topLevelComment']['snippet']['authorDisplayName'],
                    'published_at': item['snippet']['topLevelComment']['snippet']['publishedAt'],
                    'like_count': item['snippet']['topLevelComment']['snippet']['likeCount']
                }
                comments.append(comment)
        
            next_page_token = comments_response.get('nextPageToken')
        
            return comments, next_page_token
        
        except HttpError as e:
            print(f"An HTTP error {e.resp.status} occurred: {e.content}")
            return [], None

    def get_video_transcript(self, video_id):
        """Get transcript for a specific video using YouTube Transcript API"""
        try:
            from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled

            try:
                # First try to get English transcript
                transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'])
                transcript_text = ""
                for item in transcript_list:
                    transcript_text += item['text'] + " "
                return transcript_text
            except NoTranscriptFound:
                # If no English transcript, try to get transcript in any language
                try:
                    transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
                
                    # Get the first available transcript
                    for transcript in transcript_list:
                        # Try to get either a manually created transcript or auto-generated one
                        try:
                            # Try to use an English translation if available
                            if transcript.is_translatable:
                                transcript = transcript.translate('en')
                                translated = True
                            else:
                                translated = False
                            
                            fetched_transcript = transcript.fetch()
                        
                            transcript_text = ""
                            for item in fetched_transcript:
                                transcript_text += item['text'] + " "
                            
                            language_info = f" (Translated from {transcript.language_code})" if translated else f" (Original language: {transcript.language_code})"
                            return transcript_text + language_info
                        except Exception:
                            continue
                
                    # If we got here, we couldn't get any transcript
                    return "No usable transcript could be found for this video."
                except Exception as e:
                    return f"No transcript available: {str(e)}"
            except TranscriptsDisabled:
                return "Transcripts are disabled for this video."
            
        except Exception as e:
            print(f"Error retrieving transcript: {e}")
            return f"Error retrieving transcript: {str(e)}"
        
    def get_channel_details(self, channel_id):
        """Get detailed information about a specific channel"""
        try:
            channel_response = self.youtube.channels().list(
                part='snippet,statistics,contentDetails',
                id=channel_id
            ).execute()
        
            if not channel_response.get('items'):
                return None
                
            item = channel_response['items'][0]
            channel_details = {
                'id': item['id'],
                'title': item['snippet']['title'],
                'description': item['snippet']['description'],
                'created_at': item['snippet']['publishedAt'],
                'thumbnail': item['snippet']['thumbnails']['high']['url'],
                'subscriber_count': item['statistics'].get('subscriberCount', 0),
                'video_count': item['statistics'].get('videoCount', 0),
                'view_count': item['statistics'].get('viewCount', 0),
                'playlist_id': item['contentDetails']['relatedPlaylists']['uploads']
            }
        
            return channel_details
            
        except HttpError as e:
            print(f"An HTTP error {e.resp.status} occurred: {e.content}")
            return None
        
    def get_channel_videos(self, channel_id, max_results=10):
        """Get videos from a specific channel"""
        try:
            # First get the channel's uploads playlist
            channel = self.get_channel_details(channel_id)
            if not channel:
                return []
        
            playlist_id = channel['playlist_id']
        
            # Then get videos from that playlist
            playlist_response = self.youtube.playlistItems().list(
                part='snippet,contentDetails',
                playlistId=playlist_id,
                maxResults=max_results
            ).execute()
        
            videos = []
            for item in playlist_response.get('items', []):
                video = {
                    'id': item['contentDetails']['videoId'],
                    'title': item['snippet']['title'],
                    'description': item['snippet']['description'],
                    'thumbnail': item['snippet']['thumbnails']['high']['url'] if 'high' in item['snippet']['thumbnails'] else item['snippet']['thumbnails']['default']['url'],
                    'channel': item['snippet']['channelTitle'],
                    'published_at': item['snippet']['publishedAt']
                }
                videos.append(video)
        
            return videos
        
        except HttpError as e:
            print(f"An HTTP error {e.resp.status} occurred: {e.content}")
            return []    
        
    def search_channels(self, query, max_results=5):
        """Search for channels matching the query"""
        try:
            search_params = {
                'q': query,
                'part': 'snippet',
                'maxResults': max_results,
                'type': 'channel'
            }
        
            search_response = self.youtube.search().list(**search_params).execute()
        
            channels = []
            for item in search_response.get('items', []):
                channel = {
                    'id': item['id']['channelId'],
                    'title': item['snippet']['title'],
                    'description': item['snippet']['description'],
                    'thumbnail': item['snippet']['thumbnails']['high']['url'] if 'high' in item['snippet']['thumbnails'] else item['snippet']['thumbnails']['default']['url'],
                    'published_at': item['snippet']['publishedAt']
                }
                channels.append(channel)
        
            return channels
        
        except HttpError as e:
            print(f"An HTTP error {e.resp.status} occurred: {e.content}")
            return []