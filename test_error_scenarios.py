import unittest
from unittest.mock import Mock, patch, MagicMock
import os
import tempfile
import requests
from main import VideoWorkflow
from script_generator import ScriptGenerator
from image_fetcher import ImageFetcher
from voice_generator import VoiceGenerator
from video_creator import VideoCreator
from config import Config


class TestNetworkErrorScenarios(unittest.TestCase):
    """Test network error scenarios across all components"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = Mock(spec=Config)
        self.config.temp_dir = tempfile.mkdtemp()
        self.config.output_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.config.temp_dir, ignore_errors=True)
        shutil.rmtree(self.config.output_dir, ignore_errors=True)
    
    @patch('script_generator.genai.configure')
    @patch('script_generator.genai.GenerativeModel')
    def test_gemini_network_error(self, mock_model_class, mock_configure):
        """Test network error during Gemini API call"""
        mock_model = Mock()
        mock_model.generate_content.side_effect = requests.exceptions.ConnectionError("Network unreachable")
        mock_model_class.return_value = mock_model
        
        generator = ScriptGenerator(self.config)
        
        with self.assertRaises(RuntimeError) as context:
            generator.generate_script("test theme")
        
        self.assertIn("Script generation failed", str(context.exception))
    
    @patch('requests.Session.get')
    def test_unsplash_network_error(self, mock_get):
        """Test network error during Unsplash API call"""
        self.config.unsplash_access_key = "test_key"
        mock_get.side_effect = requests.exceptions.ConnectionError("Network unreachable")
        
        fetcher = ImageFetcher(self.config)
        
        with self.assertRaises(RuntimeError) as context:
            fetcher._search_images("test", 5)
        
        self.assertIn("Network error while searching", str(context.exception))
    
    @patch('requests.Session.post')
    def test_voicevox_network_error(self, mock_post):
        """Test network error during VOICEVOX API call"""
        mock_post.side_effect = requests.exceptions.ConnectionError("Connection refused")
        
        generator = VoiceGenerator(self.config)
        
        with self.assertRaises(RuntimeError) as context:
            generator._create_audio_query("test text")
        
        self.assertIn("Cannot connect to VOICEVOX server", str(context.exception))


class TestAPIKeyErrorScenarios(unittest.TestCase):
    """Test API key related error scenarios"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = Mock(spec=Config)
    
    @patch('script_generator.genai.configure')
    def test_invalid_gemini_api_key(self, mock_configure):
        """Test invalid Gemini API key error"""
        mock_configure.side_effect = Exception("Invalid API key")
        
        with self.assertRaises(RuntimeError) as context:
            ScriptGenerator(self.config)
        
        self.assertIn("Failed to initialize Gemini client", str(context.exception))
    
    @patch('requests.Session.get')
    def test_invalid_unsplash_api_key(self, mock_get):
        """Test invalid Unsplash API key error"""
        self.config.unsplash_access_key = "invalid_key"
        
        mock_response = Mock()
        mock_response.status_code = 403
        mock_get.return_value = mock_response
        
        fetcher = ImageFetcher(self.config)
        
        with self.assertRaises(RuntimeError) as context:
            fetcher._search_images("test", 5)
        
        self.assertIn("access denied", str(context.exception))


class TestDiskSpaceErrorScenarios(unittest.TestCase):
    """Test disk space related error scenarios"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = Mock(spec=Config)
        self.config.temp_dir = tempfile.mkdtemp()
        self.config.output_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.config.temp_dir, ignore_errors=True)
        shutil.rmtree(self.config.output_dir, ignore_errors=True)
    
    def test_image_download_disk_full(self):
        """Test image download when disk is full"""
        self.config.unsplash_access_key = "test_key"
        fetcher = ImageFetcher(self.config)
        
        with patch('builtins.open', side_effect=OSError("No space left on device")):
            result = fetcher._download_image("http://example.com/image.jpg", "/tmp/test.jpg")
            
            self.assertFalse(result)
    
    def test_audio_save_disk_full(self):
        """Test audio file save when disk is full"""
        generator = VoiceGenerator(self.config)
        
        with patch('builtins.open', side_effect=OSError("No space left on device")):
            with self.assertRaises(RuntimeError) as context:
                generator._save_audio_file(b"audio data", "/tmp/test.wav")
            
            self.assertIn("Failed to save audio file", str(context.exception))
    
    @patch('video_creator.VideoFileClip.write_videofile')
    def test_video_render_disk_full(self, mock_write):
        """Test video rendering when disk is full"""
        mock_write.side_effect = Exception("No space left on disk")
        
        creator = VideoCreator(self.config)
        mock_clip = Mock()
        
        with self.assertRaises(RuntimeError) as context:
            creator._render_video(mock_clip, "/tmp/test.mp4")
        
        self.assertIn("Insufficient disk space", str(context.exception))


class TestMemoryErrorScenarios(unittest.TestCase):
    """Test memory related error scenarios"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = Mock(spec=Config)
        self.config.temp_dir = tempfile.mkdtemp()
        self.config.output_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.config.temp_dir, ignore_errors=True)
        shutil.rmtree(self.config.output_dir, ignore_errors=True)
    
    @patch('video_creator.ImageClip')
    def test_video_creation_memory_error(self, mock_image_clip):
        """Test video creation with memory error"""
        mock_image_clip.side_effect = MemoryError("Out of memory")
        
        creator = VideoCreator(self.config)
        
        with self.assertRaises(RuntimeError) as context:
            creator._create_image_slideshow([{'local_path': 'test.jpg'}], 30.0)
        
        self.assertIn("Failed to create image slideshow", str(context.exception))
    
    @patch('video_creator.VideoFileClip.write_videofile')
    def test_video_render_memory_error(self, mock_write):
        """Test video rendering with memory error"""
        mock_write.side_effect = MemoryError("Insufficient memory")
        
        creator = VideoCreator(self.config)
        mock_clip = Mock()
        
        with self.assertRaises(RuntimeError) as context:
            creator._render_video(mock_clip, "/tmp/test.mp4")
        
        self.assertIn("Insufficient memory", str(context.exception))


class TestFilePermissionErrorScenarios(unittest.TestCase):
    """Test file permission related error scenarios"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = Mock(spec=Config)
        self.config.temp_dir = "/restricted/temp"
        self.config.output_dir = "/restricted/output"
    
    @patch('os.makedirs')
    def test_config_directory_permission_error(self, mock_makedirs):
        """Test configuration with directory permission error"""
        mock_makedirs.side_effect = PermissionError("Permission denied")
        
        config = Config()
        config.output_dir = "/restricted/output"
        config.temp_dir = "/restricted/temp"
        
        with patch('os.path.exists', return_value=False), \
             patch.dict(os.environ, {'GEMINI_API_KEY': 'test', 'UNSPLASH_ACCESS_KEY': 'test'}):
            
            with self.assertRaises(ValueError) as context:
                config.validate()
            
            self.assertIn("Cannot create", str(context.exception))
    
    @patch('os.access')
    @patch('os.path.exists')
    def test_config_directory_not_writable(self, mock_exists, mock_access):
        """Test configuration with non-writable directories"""
        mock_exists.return_value = True
        mock_access.return_value = False  # Not writable
        
        config = Config()
        
        with patch.dict(os.environ, {'GEMINI_API_KEY': 'test', 'UNSPLASH_ACCESS_KEY': 'test'}), \
             patch.object(config, '_check_voicevox_connection', return_value=True):
            
            with self.assertRaises(ValueError) as context:
                config.validate()
            
            self.assertIn("not writable", str(context.exception))
    
    def test_image_save_permission_error(self):
        """Test image save with permission error"""
        fetcher = ImageFetcher(self.config)
        
        with patch('builtins.open', side_effect=PermissionError("Permission denied")):
            result = fetcher._download_image("http://example.com/image.jpg", "/restricted/test.jpg")
            
            self.assertFalse(result)
    
    def test_audio_save_permission_error(self):
        """Test audio save with permission error"""
        generator = VoiceGenerator(self.config)
        
        with patch('builtins.open', side_effect=PermissionError("Permission denied")):
            with self.assertRaises(RuntimeError) as context:
                generator._save_audio_file(b"audio data", "/restricted/test.wav")
            
            self.assertIn("Failed to save audio file", str(context.exception))
    
    @patch('video_creator.VideoFileClip.write_videofile')
    def test_video_save_permission_error(self, mock_write):
        """Test video save with permission error"""
        mock_write.side_effect = PermissionError("Permission denied")
        
        creator = VideoCreator(self.config)
        mock_clip = Mock()
        
        with self.assertRaises(RuntimeError) as context:
            creator._render_video(mock_clip, "/restricted/test.mp4")
        
        self.assertIn("Permission denied", str(context.exception))


class TestCorruptedFileErrorScenarios(unittest.TestCase):
    """Test corrupted file handling scenarios"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = Mock(spec=Config)
        self.config.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.config.temp_dir, ignore_errors=True)
    
    @patch('PIL.Image.open')
    def test_corrupted_image_validation(self, mock_image_open):
        """Test validation of corrupted image files"""
        mock_image_open.side_effect = Exception("Cannot identify image file")
        
        fetcher = ImageFetcher(self.config)
        
        result = fetcher._validate_image("/path/to/corrupted.jpg")
        
        self.assertFalse(result)
    
    @patch('wave.open')
    @patch('os.path.exists')
    def test_corrupted_audio_validation(self, mock_exists, mock_wave_open):
        """Test validation of corrupted audio files"""
        mock_exists.return_value = True
        mock_wave_open.side_effect = Exception("Not a WAV file")
        
        generator = VoiceGenerator(self.config)
        
        with patch('builtins.open', create=True):
            with self.assertRaises(RuntimeError) as context:
                generator._save_audio_file(b"not audio data", "/tmp/test.wav")
            
            # The error should be caught during validation
            self.assertIn("Generated audio file is corrupted", str(context.exception))
    
    @patch('video_creator.VideoFileClip')
    def test_corrupted_video_info(self, mock_video_clip):
        """Test getting info from corrupted video file"""
        mock_video_clip.side_effect = Exception("Cannot read video file")
        
        creator = VideoCreator(self.config)
        
        with patch('os.path.exists', return_value=True):
            result = creator.get_video_info("/path/to/corrupted.mp4")
            
            self.assertIsNone(result)


class TestServiceUnavailableScenarios(unittest.TestCase):
    """Test service unavailable scenarios"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = Mock(spec=Config)
        self.config.voicevox_server_url = "http://localhost:50021"
        self.config.speaker_id = 1
    
    @patch('requests.Session.post')
    def test_voicevox_service_unavailable(self, mock_post):
        """Test VOICEVOX service unavailable error"""
        mock_response = Mock()
        mock_response.status_code = 503
        mock_post.return_value = mock_response
        
        generator = VoiceGenerator(self.config)
        
        with self.assertRaises(RuntimeError) as context:
            generator._create_audio_query("test text")
        
        self.assertIn("VOICEVOX server is not running", str(context.exception))
    
    @patch('requests.Session.get')
    def test_unsplash_service_unavailable(self, mock_get):
        """Test Unsplash service unavailable error"""
        self.config.unsplash_access_key = "test_key"
        
        mock_response = Mock()
        mock_response.status_code = 503
        mock_get.return_value = mock_response
        
        fetcher = ImageFetcher(self.config)
        
        with self.assertRaises(RuntimeError) as context:
            fetcher._search_images("test", 5)
        
        self.assertIn("API error: 503", str(context.exception))


class TestWorkflowErrorRecovery(unittest.TestCase):
    """Test error recovery in the full workflow"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = Mock(spec=Config)
        self.config.temp_dir = tempfile.mkdtemp()
        self.config.output_dir = tempfile.mkdtemp()
        self.config.max_images = 5
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.config.temp_dir, ignore_errors=True)
        shutil.rmtree(self.config.output_dir, ignore_errors=True)
    
    @patch('main.VideoCreator')
    @patch('main.VoiceGenerator')
    @patch('main.ImageFetcher')
    @patch('main.ScriptGenerator')
    def test_workflow_script_generation_error(self, mock_script_class, mock_image_class, 
                                            mock_voice_class, mock_video_class):
        """Test workflow error recovery when script generation fails"""
        # Mock components
        mock_script_gen = Mock()
        mock_script_gen.generate_script.side_effect = Exception("Script generation failed")
        mock_script_class.return_value = mock_script_gen
        
        mock_image_fetcher = Mock()
        mock_voice_gen = Mock()
        mock_video_creator = Mock()
        
        mock_image_class.return_value = mock_image_fetcher
        mock_voice_class.return_value = mock_voice_gen
        mock_video_class.return_value = mock_video_creator
        
        # Mock config validation
        self.config.validate.return_value = True
        
        workflow = VideoWorkflow(self.config)
        
        with self.assertRaises(RuntimeError) as context:
            workflow.generate_video("test theme")
        
        self.assertIn("動画生成中にエラーが発生しました", str(context.exception))
        
        # Verify cleanup was called even after error
        mock_image_fetcher.cleanup_temp_images.assert_called_once()
        mock_voice_gen.cleanup_temp_audio.assert_called_once()
        mock_video_creator.cleanup_temp_files.assert_called_once()
    
    @patch('main.VideoCreator')
    @patch('main.VoiceGenerator')
    @patch('main.ImageFetcher')
    @patch('main.ScriptGenerator')
    def test_workflow_image_fetching_error(self, mock_script_class, mock_image_class,
                                         mock_voice_class, mock_video_class):
        """Test workflow error recovery when image fetching fails"""
        # Mock successful script generation
        mock_script_gen = Mock()
        mock_script_gen.generate_script.return_value = {
            'title': 'Test', 'script': 'Test script', 'keywords': 'test'
        }
        mock_script_class.return_value = mock_script_gen
        
        # Mock failed image fetching
        mock_image_fetcher = Mock()
        mock_image_fetcher.fetch_images.side_effect = Exception("Image fetching failed")
        mock_image_class.return_value = mock_image_fetcher
        
        mock_voice_gen = Mock()
        mock_video_creator = Mock()
        mock_voice_class.return_value = mock_voice_gen
        mock_video_class.return_value = mock_video_creator
        
        self.config.validate.return_value = True
        
        workflow = VideoWorkflow(self.config)
        
        with self.assertRaises(RuntimeError) as context:
            workflow.generate_video("test theme")
        
        # Should have attempted script generation
        mock_script_gen.generate_script.assert_called_once()
        
        # Should have attempted image fetching
        mock_image_fetcher.fetch_images.assert_called_once()
        
        # Should not have attempted voice or video generation
        mock_voice_gen.generate_voice.assert_not_called()
        mock_video_creator.create_video.assert_not_called()
    
    @patch('main.VideoCreator')
    @patch('main.VoiceGenerator')
    @patch('main.ImageFetcher')
    @patch('main.ScriptGenerator')
    def test_workflow_partial_failure_cleanup(self, mock_script_class, mock_image_class,
                                             mock_voice_class, mock_video_class):
        """Test cleanup after partial workflow failure"""
        # Mock successful components up to video creation
        mock_script_gen = Mock()
        mock_script_gen.generate_script.return_value = {
            'title': 'Test', 'script': 'Test script', 'keywords': 'test'
        }
        mock_script_class.return_value = mock_script_gen
        
        mock_image_fetcher = Mock()
        mock_image_fetcher.fetch_images.return_value = [{'local_path': 'test.jpg'}]
        mock_image_class.return_value = mock_image_fetcher
        
        mock_voice_gen = Mock()
        mock_voice_gen.generate_voice.return_value = "/tmp/audio.wav"
        mock_voice_class.return_value = mock_voice_gen
        
        # Mock failed video creation
        mock_video_creator = Mock()
        mock_video_creator.create_video.side_effect = Exception("Video creation failed")
        mock_video_class.return_value = mock_video_creator
        
        self.config.validate.return_value = True
        
        workflow = VideoWorkflow(self.config)
        
        with self.assertRaises(RuntimeError):
            workflow.generate_video("test theme")
        
        # Verify all cleanup methods were called
        mock_image_fetcher.cleanup_temp_images.assert_called_once()
        mock_voice_gen.cleanup_temp_audio.assert_called_once()
        mock_video_creator.cleanup_temp_files.assert_called_once()


class TestResourceExhaustionScenarios(unittest.TestCase):
    """Test resource exhaustion scenarios"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = Mock(spec=Config)
        self.config.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.config.temp_dir, ignore_errors=True)
    
    @patch('requests.Session.get')
    def test_unsplash_quota_exhausted(self, mock_get):
        """Test Unsplash API quota exhaustion"""
        self.config.unsplash_access_key = "test_key"
        
        mock_response = Mock()
        mock_response.status_code = 429  # Too Many Requests
        mock_get.return_value = mock_response
        
        fetcher = ImageFetcher(self.config)
        
        with self.assertRaises(RuntimeError) as context:
            fetcher._search_images("test", 5)
        
        self.assertIn("rate limit exceeded", str(context.exception))
    
    @patch('requests.Session.post')
    def test_voicevox_timeout(self, mock_post):
        """Test VOICEVOX API timeout"""
        mock_post.side_effect = requests.exceptions.Timeout("Request timeout")
        
        generator = VoiceGenerator(self.config)
        
        with self.assertRaises(RuntimeError) as context:
            generator._create_audio_query("test text")
        
        self.assertIn("VOICEVOX server timeout", str(context.exception))


if __name__ == '__main__':
    unittest.main()