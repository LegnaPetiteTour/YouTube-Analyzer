import os
import anthropic
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class ClaudeClient:
    def __init__(self):
        # Get API key from environment variables
        self.api_key = os.environ.get('ANTHROPIC_API_KEY')
        if not self.api_key:
            raise ValueError("Anthropic API key not found. Set ANTHROPIC_API_KEY in .env file.")
        
        print("Initializing Claude client...")
        # Initialize client with only the API key
        self.client = anthropic.Anthropic(api_key=self.api_key)
        
        # Use a model that's likely to be available
        self.model = "claude-3-5-sonnet-20240620"
    
    def analyze_video_data(self, video_data, instruction):
        """
        Analyze video data according to the given instruction
        """
        try:
            # Convert video data to string representation for prompt
            video_data_str = "Video Information:\n"
            for key, value in video_data.items():
                video_data_str += f"{key}: {value}\n"
            
            # Create the message to send to Claude
            message = f"{video_data_str}\n\n{instruction}"
            
            # Get response from Claude
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                messages=[
                    {"role": "user", "content": message}
                ]
            )
            
            # Extract text from the response
            return response.content[0].text
            
        except Exception as e:
            print(f"Error calling Claude API: {e}")
            return f"Error analyzing video data: {str(e)}"
    
    def analyze_multiple_videos(self, videos_list, instruction):
        """
        Analyze a list of videos according to the given instruction
        """
        try:
            # Convert video list to string representation for prompt
            videos_data_str = "Videos Information:\n\n"
            for i, video in enumerate(videos_list, 1):
                videos_data_str += f"Video {i}:\n"
                for key, value in video.items():
                    videos_data_str += f"  {key}: {value}\n"
                videos_data_str += "\n"
            
            # Create the message to send to Claude
            message = f"{videos_data_str}\n\n{instruction}"
            
            # Get response from Claude
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1500,
                messages=[
                    {"role": "user", "content": message}
                ]
            )
            
            # Extract text from the response
            return response.content[0].text
            
        except Exception as e:
            print(f"Error calling Claude API: {e}")
            return f"Error analyzing videos: {str(e)}"
    
    def analyze_comments(self, comments, instruction):
        """
        Analyze video comments according to the given instruction
        """
        try:
            # Convert comments to string representation for prompt
            comments_str = "Video Comments:\n\n"
            for i, comment in enumerate(comments, 1):
                comments_str += f"Comment {i}:\n"
                for key, value in comment.items():
                    if key != 'id':  # Skip technical IDs
                        comments_str += f"  {key}: {value}\n"
                comments_str += "\n"
        
            # Create the message to send to Claude
            message = f"{comments_str}\n\n{instruction}"
        
            # Get response from Claude
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                messages=[
                    {"role": "user", "content": message}
                ]
            )
        
            return response.content[0].text
        
        except Exception as e:
            print(f"Error calling Claude API: {e}")
            return f"Error analyzing comments: {str(e)}"
        
    def analyze_channel_data(self, channel_data, videos_data, instruction):
        """
        Analyze channel and its videos according to the given instruction
        """
        try:
            # Convert channel data to string representation for prompt
            channel_str = "Channel Information:\n"
            for key, value in channel_data.items():
                if key != 'playlist_id':  # Skip technical details
                    channel_str += f"{key}: {value}\n"
        
            # Add video data
            videos_str = "\nRecent Videos:\n"
            for i, video in enumerate(videos_data, 1):
                videos_str += f"\nVideo {i}:\n"
                for key, value in video.items():
                    if key in ['id', 'title', 'published_at', 'view_count']:
                        videos_str += f"  {key}: {value}\n"
        
            # Create the message to send to Claude
            message = f"{channel_str}\n{videos_str}\n\n{instruction}"
        
            # Get response from Claude
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1500,
                messages=[
                    {"role": "user", "content": message}
                ]
            )
        
            # Extract text from the response
            return response.content[0].text
        
        except Exception as e:
            print(f"Error calling Claude API: {e}")
            return f"Error analyzing channel data: {str(e)}"