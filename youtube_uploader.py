import os
import pickle
import json
from typing import Optional, Dict, Any
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError
from config import Config

class YouTubeUploader:
    """YouTube Data API v3 client for uploading videos"""
    
    # YouTube API scopes
    SCOPES = ['https://www.googleapis.com/auth/youtube.upload']
    
    def __init__(self, config: Config):
        """Initialize YouTube uploader with configuration"""
        self.config = config
        self.service = None
        self.credentials = None
        
    def authenticate(self) -> bool:
        """Authenticate with YouTube API using OAuth 2.0"""
        try:
            creds = None
            
            # Check if token file exists and load existing credentials
            if os.path.exists(self.config.youtube_token_file):
                try:
                    with open(self.config.youtube_token_file, 'rb') as token:
                        creds = pickle.load(token)
                except Exception as e:
                    print(f"Error loading existing token: {e}")
                    creds = None
            
            # If there are no (valid) credentials available, let the user log in
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    try:
                        creds.refresh(Request())
                    except Exception as e:
                        print(f"Error refreshing token: {e}")
                        creds = None
                
                if not creds:
                    # Check if credentials file exists
                    if not os.path.exists(self.config.youtube_credentials_file):
                        raise ValueError(
                            f"YouTube credentials file not found: {self.config.youtube_credentials_file}\n"
                            "Please download the OAuth 2.0 client credentials from Google Cloud Console and save as credentials.json"
                        )
                    
                    # Run OAuth flow
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.config.youtube_credentials_file, 
                        self.SCOPES
                    )
                    creds = flow.run_local_server(port=0)
                
                # Save the credentials for the next run
                with open(self.config.youtube_token_file, 'wb') as token:
                    pickle.dump(creds, token)
            
            self.credentials = creds
            
            # Build the YouTube API service
            self.service = build('youtube', 'v3', credentials=creds)
            
            print("YouTube API authentication successful")
            return True
            
        except Exception as e:
            print(f"Error during YouTube authentication: {e}")
            return False
    
    def generate_video_metadata(self, theme: str, script: str) -> Dict[str, Any]:
        """Generate video title and description based on theme and script"""
        # Extract key points from script for description
        script_lines = script.split('\n')
        first_sentence = script_lines[0] if script_lines else theme
        
        # Generate title (max 100 characters for YouTube)
        title = f"{theme}について - 30秒で学ぶ"
        if len(title) > 100:
            title = f"{theme[:80]}... - 30秒で学ぶ"
        
        # Generate description
        description = f"""
{first_sentence}

このチャンネルでは、様々なトピックについて30秒の短時間で学べる動画を配信しています。

🎯 テーマ: {theme}
⏰ 時間: 30秒
📚 カテゴリ: 教育・学習

#教育 #学習 #30秒 #{theme.replace(' ', '')}

自動生成された動画です。
        """.strip()
        
        return {
            'title': title,
            'description': description,
            'tags': ['教育', '学習', '30秒', theme],
            'categoryId': '27'  # Education category
        }
    
    def upload_video(
        self, 
        video_path: str, 
        theme: str, 
        script: str, 
        privacy_status: str = 'private',
        callback=None
    ) -> Optional[str]:
        """
        Upload video to YouTube
        
        Args:
            video_path: Path to the video file
            theme: Video theme for title generation
            script: Video script for description generation
            privacy_status: Video privacy ('private', 'public', 'unlisted')
            callback: Progress callback function
            
        Returns:
            Video URL if successful, None otherwise
        """
        if not self.service:
            print("Error: YouTube API not authenticated. Call authenticate() first.")
            return None
        
        if not os.path.exists(video_path):
            print(f"Error: Video file not found: {video_path}")
            return None
        
        try:
            # Generate video metadata
            metadata = self.generate_video_metadata(theme, script)
            
            # Prepare video metadata for upload
            body = {
                'snippet': {
                    'title': metadata['title'],
                    'description': metadata['description'],
                    'tags': metadata['tags'],
                    'categoryId': metadata['categoryId']
                },
                'status': {
                    'privacyStatus': privacy_status,
                    'selfDeclaredMadeForKids': False
                }
            }
            
            # Create media upload object
            media = MediaFileUpload(
                video_path, 
                chunksize=-1,  # Upload in one request
                resumable=True
            )
            
            print(f"Starting upload of video: {metadata['title']}")
            print(f"Privacy status: {privacy_status}")
            
            # Execute upload request
            insert_request = self.service.videos().insert(
                part=','.join(body.keys()),
                body=body,
                media_body=media
            )
            
            # Upload with progress tracking
            response = None
            error = None
            retry = 0
            
            while response is None:
                try:
                    if callback:
                        callback("Uploading...")
                    
                    status, response = insert_request.next_chunk()
                    
                    if status and callback:
                        progress = int(status.progress() * 100)
                        callback(f"Upload progress: {progress}%")
                    
                except HttpError as e:
                    if e.resp.status in [500, 502, 503, 504]:
                        # Retryable error
                        retry += 1
                        if retry > 3:
                            print(f"Upload failed after {retry} retries: {e}")
                            return None
                        print(f"Retryable error occurred, retrying ({retry}/3)...")
                    else:
                        print(f"Non-retryable error occurred: {e}")
                        return None
                except Exception as e:
                    print(f"Unexpected error during upload: {e}")
                    return None
            
            if response is not None:
                video_id = response['id']
                video_url = f"https://www.youtube.com/watch?v={video_id}"
                
                print(f"Upload successful!")
                print(f"Video ID: {video_id}")
                print(f"Video URL: {video_url}")
                
                if callback:
                    callback("Upload completed successfully!")
                
                return video_url
            else:
                print("Upload failed: No response received")
                return None
                
        except Exception as e:
            print(f"Error during video upload: {e}")
            return None
    
    def get_upload_quota_usage(self) -> Optional[Dict[str, int]]:
        """Get current quota usage information"""
        if not self.service:
            return None
        
        try:
            # This is a simple request that uses minimal quota
            request = self.service.channels().list(
                part='snippet',
                mine=True
            )
            response = request.execute()
            
            # YouTube API doesn't directly provide quota usage info
            # This is just a placeholder to check if API is working
            return {
                'quota_used': 1,  # Each API call uses at least 1 quota unit
                'quota_limit': 10000  # Default daily quota limit
            }
            
        except Exception as e:
            print(f"Error checking quota usage: {e}")
            return None
    
    def validate_video_file(self, video_path: str) -> bool:
        """Validate video file for YouTube upload"""
        if not os.path.exists(video_path):
            print(f"Error: Video file not found: {video_path}")
            return False
        
        # Check file size (YouTube limit is 256GB, but we'll check for reasonable size)
        file_size = os.path.getsize(video_path)
        max_size = 2 * 1024 * 1024 * 1024  # 2GB limit for safety
        
        if file_size > max_size:
            print(f"Error: Video file too large: {file_size / (1024*1024):.1f}MB (max: {max_size / (1024*1024):.1f}MB)")
            return False
        
        if file_size == 0:
            print("Error: Video file is empty")
            return False
        
        # Check file extension
        valid_extensions = ['.mp4', '.mov', '.avi', '.wmv', '.flv', '.webm']
        file_ext = os.path.splitext(video_path)[1].lower()
        
        if file_ext not in valid_extensions:
            print(f"Error: Unsupported video format: {file_ext}")
            print(f"Supported formats: {', '.join(valid_extensions)}")
            return False
        
        print(f"Video file validation passed: {os.path.basename(video_path)} ({file_size / (1024*1024):.1f}MB)")
        return True
    
    def check_authentication_status(self) -> bool:
        """Check if currently authenticated with YouTube API"""
        return self.service is not None and self.credentials is not None
    
    def revoke_credentials(self) -> bool:
        """Revoke stored credentials"""
        try:
            # Remove token file
            if os.path.exists(self.config.youtube_token_file):
                os.remove(self.config.youtube_token_file)
                print("YouTube credentials revoked successfully")
            
            self.service = None
            self.credentials = None
            return True
            
        except Exception as e:
            print(f"Error revoking credentials: {e}")
            return False


def create_youtube_uploader(config: Config) -> YouTubeUploader:
    """Factory function to create YouTubeUploader instance"""
    return YouTubeUploader(config)


# Example usage and testing
if __name__ == "__main__":
    from config import create_config
    
    # Create configuration
    config = create_config()
    
    # Create uploader
    uploader = create_youtube_uploader(config)
    
    # Test authentication
    print("Testing YouTube authentication...")
    if uploader.authenticate():
        print("Authentication successful!")
        
        # Check quota usage
        quota_info = uploader.get_upload_quota_usage()
        if quota_info:
            print(f"Quota usage: {quota_info}")
        
        # Test video validation
        test_video = "./output/test_video.mp4"
        if os.path.exists(test_video):
            print(f"Testing video validation for: {test_video}")
            is_valid = uploader.validate_video_file(test_video)
            print(f"Video validation result: {is_valid}")
            
            if is_valid:
                # Test metadata generation
                test_theme = "テスト動画"
                test_script = "これはテスト用の動画です。"
                metadata = uploader.generate_video_metadata(test_theme, test_script)
                print("Generated metadata:")
                print(f"  Title: {metadata['title']}")
                print(f"  Description: {metadata['description'][:100]}...")
                print(f"  Tags: {metadata['tags']}")
        else:
            print(f"Test video not found: {test_video}")
    else:
        print("Authentication failed!")