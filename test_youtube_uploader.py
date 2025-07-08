import unittest
from unittest.mock import Mock, patch, mock_open, MagicMock, call
import os
import tempfile
import shutil
import pickle
from youtube_uploader import YouTubeUploader, create_youtube_uploader
from config import Config


class TestYouTubeUploader(unittest.TestCase):
    """Test cases for YouTubeUploader class"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create a mock config
        self.mock_config = Mock(spec=Config)
        self.mock_config.youtube_token_file = "/test/youtube_token.json"
        self.mock_config.youtube_credentials_file = "/test/youtube_credentials.json"
        
        # Create test directories
        self.test_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_init(self):
        """Test YouTubeUploader initialization"""
        uploader = YouTubeUploader(self.mock_config)
        
        self.assertEqual(uploader.config, self.mock_config)
        self.assertIsNone(uploader.service)
        self.assertIsNone(uploader.credentials)
        self.assertEqual(uploader.SCOPES, ['https://www.googleapis.com/auth/youtube.upload'])
    
    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    @patch('pickle.load')
    @patch('googleapiclient.discovery.build')
    def test_authenticate_with_existing_valid_token(self, mock_build, mock_pickle_load, mock_file, mock_exists):
        """Test authentication with existing valid token"""
        uploader = YouTubeUploader(self.mock_config)
        
        # Mock existing token file
        mock_exists.return_value = True
        
        # Mock valid credentials
        mock_creds = Mock()
        mock_creds.valid = True
        mock_pickle_load.return_value = mock_creds
        
        # Mock service build
        mock_service = Mock()
        mock_build.return_value = mock_service
        
        result = uploader.authenticate()
        
        self.assertTrue(result)
        self.assertEqual(uploader.credentials, mock_creds)
        self.assertEqual(uploader.service, mock_service)
        mock_build.assert_called_once_with('youtube', 'v3', credentials=mock_creds)
    
    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    @patch('pickle.load')
    @patch('pickle.dump')
    @patch('googleapiclient.discovery.build')
    @patch('google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file')
    def test_authenticate_with_expired_token_refresh(self, mock_flow, mock_build, mock_pickle_dump, 
                                                   mock_pickle_load, mock_file, mock_exists):
        """Test authentication with expired token that can be refreshed"""
        uploader = YouTubeUploader(self.mock_config)
        
        # Mock existing token file
        mock_exists.return_value = True
        
        # Mock expired but refreshable credentials
        mock_creds = Mock()
        mock_creds.valid = False
        mock_creds.expired = True
        mock_creds.refresh_token = "refresh_token"
        mock_pickle_load.return_value = mock_creds
        
        # Mock successful refresh
        mock_creds.refresh = Mock()
        mock_creds.refresh.side_effect = lambda req: setattr(mock_creds, 'valid', True)
        
        # Mock service build
        mock_service = Mock()
        mock_build.return_value = mock_service
        
        result = uploader.authenticate()
        
        self.assertTrue(result)
        mock_creds.refresh.assert_called_once()
        mock_pickle_dump.assert_called_once()
    
    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    @patch('pickle.dump')
    @patch('googleapiclient.discovery.build')
    @patch('google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file')
    def test_authenticate_new_oauth_flow(self, mock_flow_class, mock_build, mock_pickle_dump, 
                                       mock_file, mock_exists):
        """Test authentication with new OAuth flow"""
        uploader = YouTubeUploader(self.mock_config)
        
        # Mock credentials file exists, but no token file
        def mock_exists_side_effect(path):
            return path == self.mock_config.youtube_credentials_file
        
        mock_exists.side_effect = mock_exists_side_effect
        
        # Mock OAuth flow
        mock_flow = Mock()
        mock_flow_class.return_value = mock_flow
        
        mock_new_creds = Mock()
        mock_new_creds.valid = True
        mock_flow.run_local_server.return_value = mock_new_creds
        
        # Mock service build
        mock_service = Mock()
        mock_build.return_value = mock_service
        
        result = uploader.authenticate()
        
        self.assertTrue(result)
        mock_flow.run_local_server.assert_called_once_with(port=0)
        mock_pickle_dump.assert_called_once()
        self.assertEqual(uploader.credentials, mock_new_creds)
    
    @patch('os.path.exists')
    def test_authenticate_missing_credentials_file(self, mock_exists):
        """Test authentication failure when credentials file is missing"""
        uploader = YouTubeUploader(self.mock_config)
        
        # Mock no files exist
        mock_exists.return_value = False
        
        result = uploader.authenticate()
        
        self.assertFalse(result)
    
    def test_generate_video_metadata(self):
        """Test video metadata generation"""
        uploader = YouTubeUploader(self.mock_config)
        
        theme = "人工知能の未来"
        script = "人工知能は急速に発展しています。\n機械学習が社会を変えています。\n未来はAIと共にあります。"
        
        metadata = uploader.generate_video_metadata(theme, script)
        
        # Check metadata structure
        self.assertIn('title', metadata)
        self.assertIn('description', metadata)
        self.assertIn('tags', metadata)
        self.assertIn('categoryId', metadata)
        
        # Check content
        self.assertIn(theme, metadata['title'])
        self.assertIn("30秒で学ぶ", metadata['title'])
        self.assertIn(theme, metadata['description'])
        self.assertIn("人工知能は急速に発展しています。", metadata['description'])
        self.assertIn('教育', metadata['tags'])
        self.assertEqual(metadata['categoryId'], '27')  # Education category
        
        # Check title length constraint
        self.assertLessEqual(len(metadata['title']), 100)
    
    def test_generate_video_metadata_long_theme(self):
        """Test video metadata generation with long theme"""
        uploader = YouTubeUploader(self.mock_config)
        
        # Very long theme
        theme = "これは非常に長いテーマ名で、YouTubeのタイトル制限を超える可能性があるテーマです。さらに文字を追加して制限をテストします。"
        script = "テストスクリプトです。"
        
        metadata = uploader.generate_video_metadata(theme, script)
        
        # Title should be truncated to fit within 100 characters
        self.assertLessEqual(len(metadata['title']), 100)
        self.assertIn("...", metadata['title'])
    
    @patch('os.path.exists')
    def test_validate_video_file_success(self, mock_exists):
        """Test successful video file validation"""
        uploader = YouTubeUploader(self.mock_config)
        
        # Mock file exists and has reasonable size
        mock_exists.return_value = True
        
        with patch('os.path.getsize', return_value=50 * 1024 * 1024):  # 50MB
            result = uploader.validate_video_file("/test/video.mp4")
        
        self.assertTrue(result)
    
    @patch('os.path.exists')
    def test_validate_video_file_not_found(self, mock_exists):
        """Test video file validation when file doesn't exist"""
        uploader = YouTubeUploader(self.mock_config)
        
        mock_exists.return_value = False
        
        result = uploader.validate_video_file("/test/nonexistent.mp4")
        
        self.assertFalse(result)
    
    @patch('os.path.exists')
    def test_validate_video_file_too_large(self, mock_exists):
        """Test video file validation when file is too large"""
        uploader = YouTubeUploader(self.mock_config)
        
        mock_exists.return_value = True
        
        # Mock file size too large (3GB)
        with patch('os.path.getsize', return_value=3 * 1024 * 1024 * 1024):
            result = uploader.validate_video_file("/test/large_video.mp4")
        
        self.assertFalse(result)
    
    @patch('os.path.exists')
    def test_validate_video_file_empty(self, mock_exists):
        """Test video file validation when file is empty"""
        uploader = YouTubeUploader(self.mock_config)
        
        mock_exists.return_value = True
        
        with patch('os.path.getsize', return_value=0):
            result = uploader.validate_video_file("/test/empty.mp4")
        
        self.assertFalse(result)
    
    @patch('os.path.exists')
    def test_validate_video_file_invalid_extension(self, mock_exists):
        """Test video file validation with invalid extension"""
        uploader = YouTubeUploader(self.mock_config)
        
        mock_exists.return_value = True
        
        with patch('os.path.getsize', return_value=50 * 1024 * 1024):
            result = uploader.validate_video_file("/test/video.txt")
        
        self.assertFalse(result)
    
    def test_upload_video_not_authenticated(self):
        """Test video upload when not authenticated"""
        uploader = YouTubeUploader(self.mock_config)
        
        # Service is not set (not authenticated)
        result = uploader.upload_video("/test/video.mp4", "テスト", "テストスクリプト")
        
        self.assertIsNone(result)
    
    @patch('os.path.exists')
    def test_upload_video_file_not_found(self, mock_exists):
        """Test video upload when file doesn't exist"""
        uploader = YouTubeUploader(self.mock_config)
        
        # Mock authenticated state
        uploader.service = Mock()
        
        # Mock file doesn't exist
        mock_exists.return_value = False
        
        result = uploader.upload_video("/test/nonexistent.mp4", "テスト", "テストスクリプト")
        
        self.assertIsNone(result)
    
    @patch('os.path.exists')
    @patch('googleapiclient.http.MediaFileUpload')
    def test_upload_video_success(self, mock_media_upload, mock_exists):
        """Test successful video upload"""
        uploader = YouTubeUploader(self.mock_config)
        
        # Mock authenticated state
        mock_service = Mock()
        uploader.service = mock_service
        
        # Mock file exists
        mock_exists.return_value = True
        
        # Mock media upload
        mock_media = Mock()
        mock_media_upload.return_value = mock_media
        
        # Mock API response
        mock_insert_request = Mock()
        mock_service.videos().insert.return_value = mock_insert_request
        
        # Mock successful upload
        mock_insert_request.next_chunk.return_value = (None, {'id': 'test_video_id'})
        
        result = uploader.upload_video("/test/video.mp4", "テストテーマ", "テストスクリプト", 'private')
        
        expected_url = "https://www.youtube.com/watch?v=test_video_id"
        self.assertEqual(result, expected_url)
        
        # Verify API call
        mock_service.videos().insert.assert_called_once()
        call_args = mock_service.videos().insert.call_args
        self.assertIn('body', call_args[1])
        self.assertIn('media_body', call_args[1])
    
    @patch('os.path.exists')
    @patch('googleapiclient.http.MediaFileUpload')
    def test_upload_video_with_progress_callback(self, mock_media_upload, mock_exists):
        """Test video upload with progress callback"""
        uploader = YouTubeUploader(self.mock_config)
        
        # Mock authenticated state
        mock_service = Mock()
        uploader.service = mock_service
        
        # Mock file exists
        mock_exists.return_value = True
        
        # Mock media upload
        mock_media = Mock()
        mock_media_upload.return_value = mock_media
        
        # Mock API response with progress
        mock_insert_request = Mock()
        mock_service.videos().insert.return_value = mock_insert_request
        
        # Mock upload progress
        mock_status = Mock()
        mock_status.progress.return_value = 0.5  # 50% progress
        
        # Mock upload steps: first call returns progress, second call returns final result
        mock_insert_request.next_chunk.side_effect = [
            (mock_status, None),  # Progress update
            (None, {'id': 'test_video_id'})  # Final result
        ]
        
        # Mock callback
        callback_calls = []
        def test_callback(message):
            callback_calls.append(message)
        
        result = uploader.upload_video("/test/video.mp4", "テスト", "スクリプト", 'private', test_callback)
        
        # Check result
        expected_url = "https://www.youtube.com/watch?v=test_video_id"
        self.assertEqual(result, expected_url)
        
        # Check callback was called
        self.assertGreater(len(callback_calls), 0)
        self.assertTrue(any("progress" in call.lower() or "upload" in call.lower() for call in callback_calls))
    
    def test_get_upload_quota_usage_not_authenticated(self):
        """Test quota usage check when not authenticated"""
        uploader = YouTubeUploader(self.mock_config)
        
        result = uploader.get_upload_quota_usage()
        
        self.assertIsNone(result)
    
    def test_get_upload_quota_usage_success(self):
        """Test successful quota usage check"""
        uploader = YouTubeUploader(self.mock_config)
        
        # Mock authenticated state
        mock_service = Mock()
        uploader.service = mock_service
        
        # Mock API response
        mock_request = Mock()
        mock_service.channels().list.return_value = mock_request
        mock_request.execute.return_value = {"items": [{"snippet": {"title": "Test Channel"}}]}
        
        result = uploader.get_upload_quota_usage()
        
        self.assertIsNotNone(result)
        self.assertIn('quota_used', result)
        self.assertIn('quota_limit', result)
        self.assertEqual(result['quota_used'], 1)
        self.assertEqual(result['quota_limit'], 10000)
    
    def test_check_authentication_status(self):
        """Test authentication status check"""
        uploader = YouTubeUploader(self.mock_config)
        
        # Initially not authenticated
        self.assertFalse(uploader.check_authentication_status())
        
        # Set authenticated state
        uploader.service = Mock()
        uploader.credentials = Mock()
        
        self.assertTrue(uploader.check_authentication_status())
    
    @patch('os.path.exists')
    @patch('os.remove')
    def test_revoke_credentials_success(self, mock_remove, mock_exists):
        """Test successful credential revocation"""
        uploader = YouTubeUploader(self.mock_config)
        
        # Set authenticated state
        uploader.service = Mock()
        uploader.credentials = Mock()
        
        # Mock token file exists
        mock_exists.return_value = True
        
        result = uploader.revoke_credentials()
        
        self.assertTrue(result)
        mock_remove.assert_called_once_with(self.mock_config.youtube_token_file)
        self.assertIsNone(uploader.service)
        self.assertIsNone(uploader.credentials)
    
    @patch('os.path.exists')
    def test_revoke_credentials_no_token_file(self, mock_exists):
        """Test credential revocation when token file doesn't exist"""
        uploader = YouTubeUploader(self.mock_config)
        
        # Mock token file doesn't exist
        mock_exists.return_value = False
        
        result = uploader.revoke_credentials()
        
        self.assertTrue(result)
        self.assertIsNone(uploader.service)
        self.assertIsNone(uploader.credentials)
    
    @patch('os.path.exists')
    @patch('os.remove')
    def test_revoke_credentials_error(self, mock_remove, mock_exists):
        """Test credential revocation error handling"""
        uploader = YouTubeUploader(self.mock_config)
        
        # Mock token file exists but removal fails
        mock_exists.return_value = True
        mock_remove.side_effect = OSError("Permission denied")
        
        result = uploader.revoke_credentials()
        
        self.assertFalse(result)


class TestCreateYouTubeUploader(unittest.TestCase):
    """Test cases for create_youtube_uploader factory function"""
    
    def test_create_youtube_uploader(self):
        """Test YouTubeUploader factory function"""
        mock_config = Mock(spec=Config)
        
        uploader = create_youtube_uploader(mock_config)
        
        self.assertIsInstance(uploader, YouTubeUploader)
        self.assertEqual(uploader.config, mock_config)


class TestYouTubeUploaderIntegration(unittest.TestCase):
    """Integration tests for YouTubeUploader"""
    
    def setUp(self):
        """Set up integration test fixtures"""
        self.mock_config = Mock(spec=Config)
        self.mock_config.youtube_token_file = "/test/token.json"
        self.mock_config.youtube_credentials_file = "/test/credentials.json"
    
    def test_metadata_generation_with_real_data(self):
        """Test metadata generation with realistic data"""
        uploader = YouTubeUploader(self.mock_config)
        
        # Test with various themes and scripts
        test_cases = [
            ("AI技術", "人工知能について説明します。"),
            ("宇宙探査の未来", "宇宙探査技術の発展について。火星探査が注目されています。"),
            ("量子コンピュータ", "量子コンピュータは従来のコンピュータとは異なる仕組みで動作します。")
        ]
        
        for theme, script in test_cases:
            with self.subTest(theme=theme):
                metadata = uploader.generate_video_metadata(theme, script)
                
                # Check required fields exist
                self.assertIn('title', metadata)
                self.assertIn('description', metadata)
                self.assertIn('tags', metadata)
                self.assertIn('categoryId', metadata)
                
                # Check content quality
                self.assertIn(theme, metadata['title'])
                self.assertIn(script.split('。')[0], metadata['description'])
                self.assertIn('教育', metadata['tags'])
                self.assertIn(theme, metadata['tags'])
    
    def test_file_validation_edge_cases(self):
        """Test file validation with edge cases"""
        uploader = YouTubeUploader(self.mock_config)
        
        # Test various file extensions
        valid_extensions = ['.mp4', '.mov', '.avi', '.wmv', '.flv', '.webm']
        invalid_extensions = ['.txt', '.pdf', '.jpg', '.png', '.doc']
        
        with patch('os.path.exists', return_value=True), \
             patch('os.path.getsize', return_value=50 * 1024 * 1024):  # 50MB
            
            for ext in valid_extensions:
                with self.subTest(extension=ext):
                    result = uploader.validate_video_file(f"/test/video{ext}")
                    self.assertTrue(result, f"Should accept {ext} files")
            
            for ext in invalid_extensions:
                with self.subTest(extension=ext):
                    result = uploader.validate_video_file(f"/test/file{ext}")
                    self.assertFalse(result, f"Should reject {ext} files")


if __name__ == '__main__':
    unittest.main()