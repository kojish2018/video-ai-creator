import os
import requests
from dotenv import load_dotenv

class Config:
    """Configuration management class"""
    
    def __init__(self):
        # Load environment variables from .env file
        load_dotenv()
        
        # API Configuration
        self.gemini_api_key = os.getenv('GEMINI_API_KEY')
        self.unsplash_access_key = os.getenv('UNSPLASH_ACCESS_KEY')
        self.pexels_api_key = os.getenv('PEXELS_API_KEY')
        
        # YouTube API Configuration
        self.youtube_client_id = os.getenv('YOUTUBE_CLIENT_ID')
        self.youtube_client_secret = os.getenv('YOUTUBE_CLIENT_SECRET')
        self.youtube_credentials_file = os.getenv('YOUTUBE_CREDENTIALS_FILE', './credentials/youtube_credentials.json')
        self.youtube_token_file = os.getenv('YOUTUBE_TOKEN_FILE', './credentials/youtube_token.json')
        
        # VOICEVOX Configuration
        self.voicevox_server_url = os.getenv('VOICEVOX_SERVER_URL', 'http://127.0.0.1:50021')
        
        # Directory Configuration
        self.output_dir = os.getenv('OUTPUT_DIR', './output')
        self.temp_dir = os.getenv('TEMP_DIR', './temp')
        
        # Video Configuration
        self.video_duration = 30  # seconds
        self.video_width = 1920
        self.video_height = 1080
        self.video_fps = 24
        
        # Image Configuration
        self.max_images = 5
        self.min_images = 3
        
        # Video Configuration (for Pexels API)
        self.max_videos = 5
        self.min_videos = 1
        
        # Audio Configuration
        self.audio_format = 'wav'
        self.speaker_id = 3  # VOICEVOX speaker ID
        
        # Create directories if they don't exist
        self._create_directories()
        self._create_credentials_dir()
        
    def _create_directories(self):
        """Create output and temp directories if they don't exist"""
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.temp_dir, exist_ok=True)
        
    def _create_credentials_dir(self):
        """Create credentials directory if it doesn't exist"""
        credentials_dir = os.path.dirname(self.youtube_credentials_file)
        if credentials_dir:
            os.makedirs(credentials_dir, exist_ok=True)
        
    def validate(self):
        """Validate configuration settings"""
        errors = []
        
        # API Keys validation
        if not self.gemini_api_key:
            errors.append("GEMINI_API_KEY is not set. Please check your .env file.")
            
        if not self.unsplash_access_key:
            errors.append("UNSPLASH_ACCESS_KEY is not set. Please check your .env file.")
            
        if not self.pexels_api_key:
            errors.append("PEXELS_API_KEY is not set. Please check your .env file.")
            
        # YouTube API validation (optional - only validate if trying to use YouTube features)
        # Note: YouTube credentials are validated separately during authentication
        
        # Directory validation
        if not os.path.exists(self.output_dir):
            try:
                os.makedirs(self.output_dir, exist_ok=True)
            except Exception as e:
                errors.append(f"Cannot create output directory: {e}")
                
        if not os.path.exists(self.temp_dir):
            try:
                os.makedirs(self.temp_dir, exist_ok=True)
            except Exception as e:
                errors.append(f"Cannot create temp directory: {e}")
        
        # Check directory permissions
        if not os.access(self.output_dir, os.W_OK):
            errors.append(f"Output directory is not writable: {self.output_dir}")
            
        if not os.access(self.temp_dir, os.W_OK):
            errors.append(f"Temp directory is not writable: {self.temp_dir}")
        
        # Video configuration validation
        if self.video_duration <= 0 or self.video_duration > 300:
            errors.append("Video duration must be between 1 and 300 seconds")
            
        if self.video_width <= 0 or self.video_height <= 0:
            errors.append("Video dimensions must be positive")
            
        if self.video_fps <= 0 or self.video_fps > 60:
            errors.append("Video FPS must be between 1 and 60")
        
        # Image configuration validation
        if self.max_images <= 0 or self.max_images > 20:
            errors.append("Max images must be between 1 and 20")
            
        if self.min_images <= 0 or self.min_images > self.max_images:
            errors.append("Min images must be positive and not greater than max images")
        
        # Video configuration validation
        if self.max_videos <= 0 or self.max_videos > 10:
            errors.append("Max videos must be between 1 and 10")
            
        if self.min_videos <= 0 or self.min_videos > self.max_videos:
            errors.append("Min videos must be positive and not greater than max videos")
        
        # VOICEVOX configuration validation
        if self.speaker_id < 0:
            errors.append("Speaker ID must be non-negative")
        
        # Check VOICEVOX server connectivity
        if not self._check_voicevox_connection():
            errors.append("VOICEVOX server is not accessible. Please start VOICEVOX application.")
            
        if errors:
            raise ValueError("Configuration errors:\n" + "\n".join(f"  - {error}" for error in errors))
        
        return True
    
    def _check_voicevox_connection(self):
        """Check if VOICEVOX server is accessible"""
        try:
            response = requests.get(f"{self.voicevox_server_url}/version", timeout=5)
            return response.status_code == 200
        except Exception:
            return False
    
    def get_configuration_summary(self) -> dict:
        """Get a summary of current configuration"""
        return {
            'api_keys': {
                'gemini_configured': bool(self.gemini_api_key),
                'unsplash_configured': bool(self.unsplash_access_key),
                'pexels_configured': bool(self.pexels_api_key),
                'youtube_configured': bool(self.youtube_client_id and self.youtube_client_secret)
            },
            'directories': {
                'output_dir': self.output_dir,
                'temp_dir': self.temp_dir,
                'output_writable': os.access(self.output_dir, os.W_OK) if os.path.exists(self.output_dir) else False,
                'temp_writable': os.access(self.temp_dir, os.W_OK) if os.path.exists(self.temp_dir) else False
            },
            'video_settings': {
                'duration': self.video_duration,
                'width': self.video_width,
                'height': self.video_height,
                'fps': self.video_fps
            },
            'image_settings': {
                'max_images': self.max_images,
                'min_images': self.min_images
            },
            'video_fetching_settings': {
                'max_videos': self.max_videos,
                'min_videos': self.min_videos
            },
            'audio_settings': {
                'speaker_id': self.speaker_id,
                'format': self.audio_format
            },
            'voicevox': {
                'server_url': self.voicevox_server_url,
                'accessible': self._check_voicevox_connection()
            }
        }
    
    def load_config_from_dict(self, config_dict: dict):
        """Load configuration from dictionary"""
        for section, settings in config_dict.items():
            if section == 'video_settings':
                self.video_duration = settings.get('duration', self.video_duration)
                self.video_width = settings.get('width', self.video_width)
                self.video_height = settings.get('height', self.video_height)
                self.video_fps = settings.get('fps', self.video_fps)
            elif section == 'image_settings':
                self.max_images = settings.get('max_images', self.max_images)
                self.min_images = settings.get('min_images', self.min_images)
            elif section == 'video_fetching_settings':
                self.max_videos = settings.get('max_videos', self.max_videos)
                self.min_videos = settings.get('min_videos', self.min_videos)
            elif section == 'audio_settings':
                self.speaker_id = settings.get('speaker_id', self.speaker_id)
                self.audio_format = settings.get('format', self.audio_format)
            elif section == 'directories':
                self.output_dir = settings.get('output_dir', self.output_dir)
                self.temp_dir = settings.get('temp_dir', self.temp_dir)
        
        # Recreate directories with new paths
        self._create_directories()
    
    def reset_to_defaults(self):
        """Reset configuration to default values"""
        self.__init__()


def create_config() -> Config:
    """Factory function to create Config instance"""
    return Config()