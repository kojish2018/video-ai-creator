import unittest
from unittest.mock import Mock, patch, mock_open
import os
import tempfile
import requests
from config import Config


class TestConfig(unittest.TestCase):
    """Test cases for Config class"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create temporary directories for testing
        self.test_temp_dir = tempfile.mkdtemp()
        self.test_output_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test fixtures"""
        # Clean up temporary directories
        import shutil
        shutil.rmtree(self.test_temp_dir, ignore_errors=True)
        shutil.rmtree(self.test_output_dir, ignore_errors=True)
    
    @patch('config.load_dotenv')
    @patch.dict(os.environ, {
        'GEMINI_API_KEY': 'test_gemini_key',
        'UNSPLASH_ACCESS_KEY': 'test_unsplash_key',
        'YOUTUBE_CLIENT_ID': 'test_youtube_client_id',
        'YOUTUBE_CLIENT_SECRET': 'test_youtube_client_secret',
        'YOUTUBE_CREDENTIALS_FILE': '/test/youtube_credentials.json',
        'YOUTUBE_TOKEN_FILE': '/test/youtube_token.json',
        'VOICEVOX_SERVER_URL': 'http://localhost:50021',
        'OUTPUT_DIR': '/test/output',
        'TEMP_DIR': '/test/temp'
    })
    @patch('os.makedirs')
    def test_init_with_env_vars(self, mock_makedirs, mock_load_dotenv):
        """Test Config initialization with environment variables"""
        config = Config()
        
        # Check that dotenv was loaded
        mock_load_dotenv.assert_called_once()
        
        # Check API keys
        self.assertEqual(config.gemini_api_key, 'test_gemini_key')
        self.assertEqual(config.unsplash_access_key, 'test_unsplash_key')
        
        # Check YouTube API settings
        self.assertEqual(config.youtube_client_id, 'test_youtube_client_id')
        self.assertEqual(config.youtube_client_secret, 'test_youtube_client_secret')
        self.assertEqual(config.youtube_credentials_file, '/test/youtube_credentials.json')
        self.assertEqual(config.youtube_token_file, '/test/youtube_token.json')
        
        # Check server URL
        self.assertEqual(config.voicevox_server_url, 'http://localhost:50021')
        
        # Check directories
        self.assertEqual(config.output_dir, '/test/output')
        self.assertEqual(config.temp_dir, '/test/temp')
        
        # Check that directories were created
        mock_makedirs.assert_any_call('/test/output', exist_ok=True)
        mock_makedirs.assert_any_call('/test/temp', exist_ok=True)
        mock_makedirs.assert_any_call('/test', exist_ok=True)  # credentials directory
    
    @patch('config.load_dotenv')
    @patch.dict(os.environ, {}, clear=True)
    @patch('os.makedirs')
    def test_init_with_defaults(self, mock_makedirs, mock_load_dotenv):
        """Test Config initialization with default values"""
        config = Config()
        
        # Check default values
        self.assertIsNone(config.gemini_api_key)
        self.assertIsNone(config.unsplash_access_key)
        self.assertIsNone(config.youtube_client_id)
        self.assertIsNone(config.youtube_client_secret)
        self.assertEqual(config.youtube_credentials_file, './credentials/youtube_credentials.json')
        self.assertEqual(config.youtube_token_file, './credentials/youtube_token.json')
        self.assertEqual(config.voicevox_server_url, 'http://127.0.0.1:50021')
        self.assertEqual(config.output_dir, './output')
        self.assertEqual(config.temp_dir, './temp')
        
        # Check video settings
        self.assertEqual(config.video_duration, 30)
        self.assertEqual(config.video_width, 1920)
        self.assertEqual(config.video_height, 1080)
        self.assertEqual(config.video_fps, 24)
        
        # Check image settings
        self.assertEqual(config.max_images, 5)
        self.assertEqual(config.min_images, 3)
        
        # Check audio settings
        self.assertEqual(config.audio_format, 'wav')
        self.assertEqual(config.speaker_id, 3)
    
    @patch('os.makedirs')
    def test_create_directories_success(self, mock_makedirs):
        """Test successful directory creation"""
        with patch('config.load_dotenv'):
            config = Config()
            config.output_dir = '/test/output'
            config.temp_dir = '/test/temp'
            
            config._create_directories()
            
            mock_makedirs.assert_any_call('/test/output', exist_ok=True)
            mock_makedirs.assert_any_call('/test/temp', exist_ok=True)
    
    @patch('config.load_dotenv')
    @patch('os.makedirs')
    def test_create_directories_called_in_init(self, mock_makedirs, mock_load_dotenv):
        """Test that _create_directories is called during initialization"""
        Config()
        
        # Should be called at least once during __init__
        self.assertTrue(mock_makedirs.called)
    
    @patch('config.load_dotenv')
    @patch.dict(os.environ, {'GEMINI_API_KEY': 'test_key', 'UNSPLASH_ACCESS_KEY': 'test_key'})
    @patch('os.path.exists')
    @patch('os.access')
    @patch.object(Config, '_check_voicevox_connection')
    def test_validate_success(self, mock_voicevox, mock_access, mock_exists, mock_load_dotenv):
        """Test successful configuration validation"""
        config = Config()
        
        # Mock all checks to pass
        mock_exists.return_value = True
        mock_access.return_value = True
        mock_voicevox.return_value = True
        
        result = config.validate()
        
        self.assertTrue(result)
    
    @patch('config.load_dotenv')
    @patch.dict(os.environ, {}, clear=True)
    def test_validate_missing_api_keys(self, mock_load_dotenv):
        """Test validation with missing API keys"""
        config = Config()
        
        with patch('os.path.exists', return_value=True), \
             patch('os.access', return_value=True), \
             patch.object(config, '_check_voicevox_connection', return_value=True):
            
            with self.assertRaises(ValueError) as context:
                config.validate()
            
            error_msg = str(context.exception)
            self.assertIn("GEMINI_API_KEY is not set", error_msg)
            self.assertIn("UNSPLASH_ACCESS_KEY is not set", error_msg)
    
    @patch('config.load_dotenv')
    @patch.dict(os.environ, {'GEMINI_API_KEY': 'test', 'UNSPLASH_ACCESS_KEY': 'test'})
    @patch('os.path.exists')
    @patch('os.makedirs')
    def test_validate_directory_creation_error(self, mock_makedirs, mock_exists, mock_load_dotenv):
        """Test validation when directory creation fails"""
        config = Config()
        
        # Mock directory doesn't exist, and makedirs fails
        mock_exists.return_value = False
        mock_makedirs.side_effect = PermissionError("Permission denied")
        
        with patch('os.access', return_value=True), \
             patch.object(config, '_check_voicevox_connection', return_value=True):
            
            with self.assertRaises(ValueError) as context:
                config.validate()
            
            error_msg = str(context.exception)
            self.assertIn("Cannot create output directory", error_msg)
    
    @patch('config.load_dotenv')
    @patch.dict(os.environ, {'GEMINI_API_KEY': 'test', 'UNSPLASH_ACCESS_KEY': 'test'})
    @patch('os.path.exists')
    @patch('os.access')
    def test_validate_directory_not_writable(self, mock_access, mock_exists, mock_load_dotenv):
        """Test validation when directories are not writable"""
        config = Config()
        
        mock_exists.return_value = True
        mock_access.return_value = False  # Not writable
        
        with patch.object(config, '_check_voicevox_connection', return_value=True):
            
            with self.assertRaises(ValueError) as context:
                config.validate()
            
            error_msg = str(context.exception)
            self.assertIn("not writable", error_msg)
    
    @patch('config.load_dotenv')
    @patch.dict(os.environ, {'GEMINI_API_KEY': 'test', 'UNSPLASH_ACCESS_KEY': 'test'})
    def test_validate_invalid_video_settings(self, mock_load_dotenv):
        """Test validation with invalid video settings"""
        config = Config()
        
        # Set invalid values
        config.video_duration = 0  # Invalid
        config.video_width = -100  # Invalid
        config.video_fps = 100  # Invalid
        
        with patch('os.path.exists', return_value=True), \
             patch('os.access', return_value=True), \
             patch.object(config, '_check_voicevox_connection', return_value=True):
            
            with self.assertRaises(ValueError) as context:
                config.validate()
            
            error_msg = str(context.exception)
            self.assertIn("Video duration must be", error_msg)
            self.assertIn("Video dimensions must be", error_msg)
            self.assertIn("Video FPS must be", error_msg)
    
    @patch('config.load_dotenv')
    @patch.dict(os.environ, {'GEMINI_API_KEY': 'test', 'UNSPLASH_ACCESS_KEY': 'test'})
    def test_validate_invalid_image_settings(self, mock_load_dotenv):
        """Test validation with invalid image settings"""
        config = Config()
        
        # Set invalid values
        config.max_images = 0  # Invalid
        config.min_images = 10  # Greater than max_images
        
        with patch('os.path.exists', return_value=True), \
             patch('os.access', return_value=True), \
             patch.object(config, '_check_voicevox_connection', return_value=True):
            
            with self.assertRaises(ValueError) as context:
                config.validate()
            
            error_msg = str(context.exception)
            self.assertIn("Max images must be", error_msg)
            self.assertIn("Min images must be", error_msg)
    
    @patch('config.load_dotenv')
    @patch.dict(os.environ, {'GEMINI_API_KEY': 'test', 'UNSPLASH_ACCESS_KEY': 'test'})
    def test_validate_invalid_speaker_id(self, mock_load_dotenv):
        """Test validation with invalid speaker ID"""
        config = Config()
        
        config.speaker_id = -1  # Invalid
        
        with patch('os.path.exists', return_value=True), \
             patch('os.access', return_value=True), \
             patch.object(config, '_check_voicevox_connection', return_value=True):
            
            with self.assertRaises(ValueError) as context:
                config.validate()
            
            error_msg = str(context.exception)
            self.assertIn("Speaker ID must be non-negative", error_msg)
    
    @patch('config.load_dotenv')
    @patch.dict(os.environ, {'GEMINI_API_KEY': 'test', 'UNSPLASH_ACCESS_KEY': 'test'})
    def test_validate_voicevox_not_accessible(self, mock_load_dotenv):
        """Test validation when VOICEVOX server is not accessible"""
        config = Config()
        
        with patch('os.path.exists', return_value=True), \
             patch('os.access', return_value=True), \
             patch.object(config, '_check_voicevox_connection', return_value=False):
            
            with self.assertRaises(ValueError) as context:
                config.validate()
            
            error_msg = str(context.exception)
            self.assertIn("VOICEVOX server is not accessible", error_msg)
    
    @patch('requests.get')
    def test_check_voicevox_connection_success(self, mock_get):
        """Test successful VOICEVOX connection check"""
        with patch('config.load_dotenv'):
            config = Config()
            
            mock_response = Mock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response
            
            result = config._check_voicevox_connection()
            
            self.assertTrue(result)
            mock_get.assert_called_once_with(f"{config.voicevox_server_url}/version", timeout=5)
    
    @patch('requests.get')
    def test_check_voicevox_connection_failure(self, mock_get):
        """Test VOICEVOX connection check failure"""
        with patch('config.load_dotenv'):
            config = Config()
            
            # Test HTTP error
            mock_response = Mock()
            mock_response.status_code = 500
            mock_get.return_value = mock_response
            
            result = config._check_voicevox_connection()
            self.assertFalse(result)
            
            # Test network error
            mock_get.side_effect = requests.exceptions.RequestException("Network error")
            
            result = config._check_voicevox_connection()
            self.assertFalse(result)
    
    @patch('config.load_dotenv')
    @patch.dict(os.environ, {'GEMINI_API_KEY': 'test', 'UNSPLASH_ACCESS_KEY': 'test'})
    @patch('os.path.exists')
    @patch('os.access')
    def test_get_configuration_summary(self, mock_access, mock_exists, mock_load_dotenv):
        """Test configuration summary generation"""
        config = Config()
        
        # Mock directory checks
        mock_exists.return_value = True
        mock_access.return_value = True
        
        with patch.object(config, '_check_voicevox_connection', return_value=True):
            summary = config.get_configuration_summary()
        
        # Check structure
        self.assertIn('api_keys', summary)
        self.assertIn('directories', summary)
        self.assertIn('video_settings', summary)
        self.assertIn('image_settings', summary)
        self.assertIn('audio_settings', summary)
        self.assertIn('voicevox', summary)
        
        # Check specific values
        self.assertTrue(summary['api_keys']['gemini_configured'])
        self.assertTrue(summary['api_keys']['unsplash_configured'])
        self.assertTrue(summary['api_keys']['youtube_configured'])
        self.assertTrue(summary['directories']['output_writable'])
        self.assertTrue(summary['directories']['temp_writable'])
        self.assertTrue(summary['voicevox']['accessible'])
        
        self.assertEqual(summary['video_settings']['duration'], 30)
        self.assertEqual(summary['video_settings']['width'], 1920)
        self.assertEqual(summary['image_settings']['max_images'], 5)
        self.assertEqual(summary['audio_settings']['speaker_id'], 3)
    
    @patch('config.load_dotenv')
    @patch('os.makedirs')
    def test_create_credentials_dir(self, mock_makedirs, mock_load_dotenv):
        """Test credentials directory creation"""
        with patch.dict(os.environ, {'YOUTUBE_CREDENTIALS_FILE': '/test/creds/youtube.json'}):
            config = Config()
            
            # Should create credentials directory
            mock_makedirs.assert_any_call('/test/creds', exist_ok=True)
    
    @patch('config.load_dotenv')
    @patch('os.makedirs')
    def test_create_credentials_dir_no_path(self, mock_makedirs, mock_load_dotenv):
        """Test credentials directory creation with no directory path"""
        with patch.dict(os.environ, {'YOUTUBE_CREDENTIALS_FILE': 'youtube.json'}):
            config = Config()
            
            # Should not try to create directory for file in current dir
            # (os.path.dirname returns empty string for files without path)
            config._create_credentials_dir()
    
    @patch('config.load_dotenv')
    @patch.dict(os.environ, {
        'GEMINI_API_KEY': 'test_key',
        'UNSPLASH_ACCESS_KEY': 'test_key',
        'YOUTUBE_CLIENT_ID': 'test_youtube_id',
        'YOUTUBE_CLIENT_SECRET': 'test_youtube_secret'
    })
    @patch('os.path.exists')
    @patch('os.access')
    def test_get_configuration_summary_youtube_configured(self, mock_access, mock_exists, mock_load_dotenv):
        """Test configuration summary with YouTube API configured"""
        config = Config()
        
        # Mock directory checks
        mock_exists.return_value = True
        mock_access.return_value = True
        
        with patch.object(config, '_check_voicevox_connection', return_value=True):
            summary = config.get_configuration_summary()
        
        # Check YouTube configuration
        self.assertTrue(summary['api_keys']['youtube_configured'])
    
    @patch('config.load_dotenv')
    @patch.dict(os.environ, {
        'GEMINI_API_KEY': 'test_key',
        'UNSPLASH_ACCESS_KEY': 'test_key',
        'YOUTUBE_CLIENT_ID': 'test_youtube_id'
        # Missing YOUTUBE_CLIENT_SECRET
    })
    @patch('os.path.exists')
    @patch('os.access')
    def test_get_configuration_summary_youtube_partial(self, mock_access, mock_exists, mock_load_dotenv):
        """Test configuration summary with partial YouTube API configuration"""
        config = Config()
        
        # Mock directory checks
        mock_exists.return_value = True
        mock_access.return_value = True
        
        with patch.object(config, '_check_voicevox_connection', return_value=True):
            summary = config.get_configuration_summary()
        
        # Check YouTube configuration - should be False since client_secret is missing
        self.assertFalse(summary['api_keys']['youtube_configured'])
    
    @patch('config.load_dotenv')
    @patch('os.makedirs')
    def test_load_config_from_dict(self, mock_makedirs, mock_load_dotenv):
        """Test loading configuration from dictionary"""
        config = Config()
        
        config_dict = {
            'video_settings': {
                'duration': 45,
                'width': 1280,
                'height': 720,
                'fps': 30
            },
            'image_settings': {
                'max_images': 8,
                'min_images': 2
            },
            'audio_settings': {
                'speaker_id': 5,
                'format': 'mp3'
            },
            'directories': {
                'output_dir': '/custom/output',
                'temp_dir': '/custom/temp'
            }
        }
        
        config.load_config_from_dict(config_dict)
        
        # Check that values were updated
        self.assertEqual(config.video_duration, 45)
        self.assertEqual(config.video_width, 1280)
        self.assertEqual(config.video_height, 720)
        self.assertEqual(config.video_fps, 30)
        
        self.assertEqual(config.max_images, 8)
        self.assertEqual(config.min_images, 2)
        
        self.assertEqual(config.speaker_id, 5)
        self.assertEqual(config.audio_format, 'mp3')
        
        self.assertEqual(config.output_dir, '/custom/output')
        self.assertEqual(config.temp_dir, '/custom/temp')
        
        # Check that directories were recreated
        mock_makedirs.assert_any_call('/custom/output', exist_ok=True)
        mock_makedirs.assert_any_call('/custom/temp', exist_ok=True)
    
    @patch('config.load_dotenv')
    def test_load_config_from_dict_partial(self, mock_load_dotenv):
        """Test loading partial configuration from dictionary"""
        config = Config()
        
        original_duration = config.video_duration
        original_width = config.video_width
        
        # Only update some values
        config_dict = {
            'video_settings': {
                'duration': 60  # Only update duration
            }
        }
        
        config.load_config_from_dict(config_dict)
        
        # Duration should be updated
        self.assertEqual(config.video_duration, 60)
        # Width should remain the same
        self.assertEqual(config.video_width, original_width)
    
    @patch('config.load_dotenv')
    def test_load_config_from_dict_unknown_section(self, mock_load_dotenv):
        """Test loading configuration with unknown section"""
        config = Config()
        
        original_duration = config.video_duration
        
        config_dict = {
            'unknown_section': {
                'some_setting': 'value'
            },
            'video_settings': {
                'duration': 60
            }
        }
        
        # Should not raise error and should process known sections
        config.load_config_from_dict(config_dict)
        
        self.assertEqual(config.video_duration, 60)
    
    @patch('config.load_dotenv')
    @patch.object(Config, '__init__')
    def test_reset_to_defaults(self, mock_init, mock_load_dotenv):
        """Test resetting configuration to defaults"""
        # Mock __init__ to avoid recursion issues in testing
        mock_init.return_value = None
        
        config = Config()
        config.reset_to_defaults()
        
        # Should call __init__ again
        self.assertEqual(mock_init.call_count, 2)  # Once for creation, once for reset


class TestCreateConfig(unittest.TestCase):
    """Test cases for create_config factory function"""
    
    @patch('config.Config')
    def test_create_config(self, mock_config_class):
        """Test factory function creates Config instance"""
        from config import create_config
        
        mock_config = Mock()
        mock_config_class.return_value = mock_config
        
        result = create_config()
        
        self.assertEqual(result, mock_config)
        mock_config_class.assert_called_once()


if __name__ == '__main__':
    unittest.main()