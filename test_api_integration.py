import unittest
from unittest.mock import Mock, patch, MagicMock
import os
import tempfile
import requests
import json
from script_generator import ScriptGenerator
from image_fetcher import ImageFetcher
from voice_generator import VoiceGenerator
from config import Config


class TestGeminiAPIIntegration(unittest.TestCase):
    """Integration tests for Gemini API functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = Mock(spec=Config)
        self.config.gemini_api_key = "test_gemini_key"
    
    @patch('script_generator.genai.configure')
    @patch('script_generator.genai.GenerativeModel')
    def test_gemini_api_integration_success(self, mock_model_class, mock_configure):
        """Test successful integration with Gemini API"""
        # Mock Gemini API response
        mock_response = Mock()
        mock_response.text = '''
        {
            "title": "AI技術の未来",
            "script": "人工知能技術は急速に発展しており、私たちの生活を大きく変えています。機械学習や深層学習の進歩により、これまで不可能だった作業が可能になっています。",
            "keywords": "AI, 人工知能, 機械学習, 技術革新, 未来"
        }
        '''
        
        mock_model = Mock()
        mock_model.generate_content.return_value = mock_response
        mock_model_class.return_value = mock_model
        
        generator = ScriptGenerator(self.config)
        result = generator.generate_script("AI技術の未来について")
        
        # Verify API was configured correctly
        mock_configure.assert_called_once_with(api_key="test_gemini_key")
        mock_model_class.assert_called_once_with('gemini-1.5-flash')
        
        # Verify script generation
        self.assertEqual(result['title'], "AI技術の未来")
        self.assertIn("人工知能技術", result['script'])
        self.assertEqual(result['keywords'], "AI, 人工知能, 機械学習, 技術革新, 未来")
        
        # Verify prompt was sent to API
        mock_model.generate_content.assert_called_once()
        prompt_arg = mock_model.generate_content.call_args[0][0]
        self.assertIn("AI技術の未来について", prompt_arg)
        self.assertIn("JSON形式", prompt_arg)
    
    @patch('script_generator.genai.configure')
    @patch('script_generator.genai.GenerativeModel')
    def test_gemini_api_error_handling(self, mock_model_class, mock_configure):
        """Test Gemini API error handling"""
        # Test API key error
        mock_configure.side_effect = Exception("Invalid API key")
        
        with self.assertRaises(RuntimeError) as context:
            ScriptGenerator(self.config)
        
        self.assertIn("Failed to initialize Gemini client", str(context.exception))
    
    @patch('script_generator.genai.configure')
    @patch('script_generator.genai.GenerativeModel')
    def test_gemini_api_quota_exceeded(self, mock_model_class, mock_configure):
        """Test Gemini API quota exceeded handling"""
        mock_model = Mock()
        mock_model.generate_content.side_effect = Exception("Quota exceeded")
        mock_model_class.return_value = mock_model
        
        generator = ScriptGenerator(self.config)
        
        with self.assertRaises(RuntimeError) as context:
            generator.generate_script("test theme")
        
        self.assertIn("API quota exceeded", str(context.exception))
    
    @patch('script_generator.genai.configure')
    @patch('script_generator.genai.GenerativeModel')
    def test_gemini_api_malformed_response(self, mock_model_class, mock_configure):
        """Test handling of malformed Gemini API response"""
        mock_response = Mock()
        mock_response.text = "This is not valid JSON"
        
        mock_model = Mock()
        mock_model.generate_content.return_value = mock_response
        mock_model_class.return_value = mock_model
        
        generator = ScriptGenerator(self.config)
        
        with self.assertRaises(ValueError) as context:
            generator.generate_script("test theme")
        
        self.assertIn("No valid JSON found", str(context.exception))


class TestUnsplashAPIIntegration(unittest.TestCase):
    """Integration tests for Unsplash API functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = Mock(spec=Config)
        self.config.unsplash_access_key = "test_unsplash_key"
        self.config.temp_dir = tempfile.mkdtemp()
        self.config.min_images = 3
        self.config.max_images = 5
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.config.temp_dir, ignore_errors=True)
    
    @patch('requests.Session.get')
    def test_unsplash_api_integration_success(self, mock_get):
        """Test successful integration with Unsplash API"""
        # Mock Unsplash API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'results': [
                {
                    'id': 'test_image_1',
                    'urls': {
                        'regular': 'https://images.unsplash.com/photo-1?w=1080',
                        'full': 'https://images.unsplash.com/photo-1?q=80'
                    },
                    'description': 'Beautiful AI visualization',
                    'alt_description': 'Artificial intelligence concept',
                    'width': 1920,
                    'height': 1080,
                    'user': {'name': 'Tech Photographer'}
                },
                {
                    'id': 'test_image_2',
                    'urls': {
                        'regular': 'https://images.unsplash.com/photo-2?w=1080',
                        'full': 'https://images.unsplash.com/photo-2?q=80'
                    },
                    'description': 'Future technology',
                    'alt_description': 'Technology and innovation',
                    'width': 1920,
                    'height': 1080,
                    'user': {'name': 'Innovation Studio'}
                }
            ]
        }
        mock_get.return_value = mock_response
        
        fetcher = ImageFetcher(self.config)
        
        # Mock image download and validation
        with patch.object(fetcher, '_download_image', return_value=True), \
             patch.object(fetcher, '_validate_image', return_value=True):
            
            result = fetcher._search_images("AI technology", 5)
            
            # Verify API call
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            
            # Check URL
            self.assertIn('/search/photos', call_args[0][0])
            
            # Check parameters
            params = call_args[1]['params']
            self.assertEqual(params['query'], 'AI technology')
            self.assertEqual(params['per_page'], 5)
            self.assertEqual(params['orientation'], 'landscape')
            self.assertEqual(params['content_filter'], 'high')
            
            # Check headers (should include authorization)
            self.assertIn('Authorization', fetcher.session.headers)
            self.assertIn('test_unsplash_key', fetcher.session.headers['Authorization'])
            
            # Verify results
            self.assertEqual(len(result), 2)
            self.assertEqual(result[0]['id'], 'test_image_1')
            self.assertEqual(result[0]['photographer'], 'Tech Photographer')
            self.assertEqual(result[1]['description'], 'Future technology')
    
    @patch('requests.Session.get')
    def test_unsplash_api_rate_limit(self, mock_get):
        """Test Unsplash API rate limit handling"""
        mock_response = Mock()
        mock_response.status_code = 429  # Too Many Requests
        mock_get.return_value = mock_response
        
        fetcher = ImageFetcher(self.config)
        
        with self.assertRaises(RuntimeError) as context:
            fetcher._search_images("test", 5)
        
        self.assertIn("rate limit exceeded", str(context.exception))
    
    @patch('requests.Session.get')
    def test_unsplash_api_forbidden(self, mock_get):
        """Test Unsplash API forbidden access handling"""
        mock_response = Mock()
        mock_response.status_code = 403  # Forbidden
        mock_get.return_value = mock_response
        
        fetcher = ImageFetcher(self.config)
        
        with self.assertRaises(RuntimeError) as context:
            fetcher._search_images("test", 5)
        
        self.assertIn("access denied", str(context.exception))
    
    @patch('requests.Session.get')
    def test_unsplash_api_network_error(self, mock_get):
        """Test Unsplash API network error handling"""
        mock_get.side_effect = requests.exceptions.ConnectionError("Network error")
        
        fetcher = ImageFetcher(self.config)
        
        with self.assertRaises(RuntimeError) as context:
            fetcher._search_images("test", 5)
        
        self.assertIn("Network error while searching", str(context.exception))
    
    @patch('requests.get')
    @patch('requests.Session.get')
    def test_unsplash_image_download_integration(self, mock_session_get, mock_get):
        """Test complete image download integration"""
        # Mock search response
        search_response = Mock()
        search_response.status_code = 200
        search_response.json.return_value = {
            'results': [{
                'id': 'test_img',
                'urls': {
                    'regular': 'https://images.unsplash.com/test.jpg',
                    'full': 'https://images.unsplash.com/test_full.jpg'
                },
                'description': 'Test image',
                'width': 1920,
                'height': 1080,
                'user': {'name': 'Test User'}
            }]
        }
        mock_session_get.return_value = search_response
        
        # Mock image download
        download_response = Mock()
        download_response.iter_content.return_value = [b'fake image data']
        download_response.raise_for_status.return_value = None
        mock_get.return_value = download_response
        
        fetcher = ImageFetcher(self.config)
        
        # Mock image validation
        with patch.object(fetcher, '_validate_image', return_value=True), \
             patch('builtins.open', create=True) as mock_open:
            
            mock_file = Mock()
            mock_open.return_value.__enter__.return_value = mock_file
            
            images = fetcher._search_images("test", 1)
            downloaded = fetcher._download_and_validate_images(images)
            
            self.assertEqual(len(downloaded), 1)
            self.assertIn('local_path', downloaded[0])
            self.assertIn('filename', downloaded[0])
            
            # Verify download was called
            mock_get.assert_called_once_with(
                'https://images.unsplash.com/test_full.jpg',
                stream=True,
                timeout=30
            )


class TestVOICEVOXAPIIntegration(unittest.TestCase):
    """Integration tests for VOICEVOX API functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = Mock(spec=Config)
        self.config.voicevox_server_url = "http://localhost:50021"
        self.config.speaker_id = 1
        self.config.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.config.temp_dir, ignore_errors=True)
    
    @patch('requests.Session.post')
    @patch('requests.Session.get')
    def test_voicevox_api_integration_success(self, mock_get, mock_post):
        """Test successful integration with VOICEVOX API"""
        # Mock connection test
        version_response = Mock()
        version_response.status_code = 200
        mock_get.return_value = version_response
        
        # Mock audio query response
        query_response = Mock()
        query_response.status_code = 200
        query_response.json.return_value = {
            'accent_phrases': [
                {'moras': [{'text': 'テ'}, {'text': 'ス'}, {'text': 'ト'}]}
            ],
            'speedScale': 1.0
        }
        
        # Mock synthesis response
        synthesis_response = Mock()
        synthesis_response.status_code = 200
        synthesis_response.content = b'fake WAV audio data'
        
        mock_post.side_effect = [query_response, synthesis_response]
        
        generator = VoiceGenerator(self.config)
        
        # Test connection
        self.assertTrue(generator.test_connection())
        
        # Mock file operations
        with patch('builtins.open', create=True), \
             patch('wave.open') as mock_wave, \
             patch('os.path.exists', return_value=True):
            
            mock_wav_file = Mock()
            mock_wav_file.getnframes.return_value = 1000
            mock_wave.return_value.__enter__.return_value = mock_wav_file
            
            audio_path = generator.generate_voice("テスト音声です")
            
            # Verify API calls
            self.assertEqual(mock_post.call_count, 2)
            
            # Check audio query call
            query_call = mock_post.call_args_list[0]
            self.assertIn('/audio_query', query_call[0][0])
            self.assertEqual(query_call[1]['params']['text'], 'テスト音声です、')
            self.assertEqual(query_call[1]['params']['speaker'], 1)
            
            # Check synthesis call
            synthesis_call = mock_post.call_args_list[1]
            self.assertIn('/synthesis', synthesis_call[0][0])
            self.assertEqual(synthesis_call[1]['params']['speaker'], 1)
            self.assertIn('accent_phrases', synthesis_call[1]['json'])
            
            # Verify result
            self.assertIsInstance(audio_path, str)
            self.assertTrue(audio_path.endswith('.wav'))
    
    @patch('requests.Session.get')
    def test_voicevox_connection_test_failure(self, mock_get):
        """Test VOICEVOX connection test failure"""
        # Mock connection failure
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection refused")
        
        generator = VoiceGenerator(self.config)
        
        self.assertFalse(generator.test_connection())
    
    @patch('requests.Session.post')
    def test_voicevox_audio_query_error(self, mock_post):
        """Test VOICEVOX audio query error handling"""
        mock_response = Mock()
        mock_response.status_code = 400  # Bad Request
        mock_post.return_value = mock_response
        
        generator = VoiceGenerator(self.config)
        
        with self.assertRaises(RuntimeError) as context:
            generator._create_audio_query("test text")
        
        self.assertIn("Invalid text or speaker ID", str(context.exception))
    
    @patch('requests.Session.post')
    def test_voicevox_server_not_running(self, mock_post):
        """Test VOICEVOX server not running error"""
        mock_response = Mock()
        mock_response.status_code = 503  # Service Unavailable
        mock_post.return_value = mock_response
        
        generator = VoiceGenerator(self.config)
        
        with self.assertRaises(RuntimeError) as context:
            generator._create_audio_query("test text")
        
        self.assertIn("VOICEVOX server is not running", str(context.exception))
    
    @patch('requests.Session.post')
    def test_voicevox_synthesis_error(self, mock_post):
        """Test VOICEVOX synthesis error handling"""
        # Mock successful audio query
        query_response = Mock()
        query_response.status_code = 200
        query_response.json.return_value = {'accent_phrases': []}
        
        # Mock failed synthesis
        synthesis_response = Mock()
        synthesis_response.status_code = 500
        
        mock_post.side_effect = [query_response, synthesis_response]
        
        generator = VoiceGenerator(self.config)
        
        with self.assertRaises(RuntimeError) as context:
            generator._synthesize_voice({'accent_phrases': []})
        
        self.assertIn("Voice synthesis failed: 500", str(context.exception))
    
    @patch('requests.Session.get')
    def test_voicevox_get_speakers(self, mock_get):
        """Test getting available speakers from VOICEVOX"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                'name': 'ずんだもん',
                'speaker_uuid': 'zundamon-uuid',
                'styles': [{'id': 0, 'name': 'ノーマル'}]
            },
            {
                'name': '四国めたん',
                'speaker_uuid': 'metan-uuid', 
                'styles': [{'id': 1, 'name': 'ノーマル'}]
            }
        ]
        mock_get.return_value = mock_response
        
        generator = VoiceGenerator(self.config)
        speakers = generator.get_available_speakers()
        
        self.assertEqual(len(speakers), 2)
        self.assertEqual(speakers[0]['name'], 'ずんだもん')
        self.assertEqual(speakers[1]['name'], '四国めたん')
        
        mock_get.assert_called_once_with(
            "http://localhost:50021/speakers",
            timeout=10
        )


class TestAPIRateLimiting(unittest.TestCase):
    """Test API rate limiting and retry logic"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = Mock(spec=Config)
        self.config.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.config.temp_dir, ignore_errors=True)
    
    @patch('time.sleep')
    @patch('requests.Session.get')
    def test_unsplash_rate_limiting_delay(self, mock_get, mock_sleep):
        """Test that Unsplash API calls include rate limiting delays"""
        self.config.unsplash_access_key = "test_key"
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'results': []}
        mock_get.return_value = mock_response
        
        fetcher = ImageFetcher(self.config)
        
        with patch.object(fetcher, '_download_and_validate_images', return_value=[]):
            fetcher.fetch_images("test1, test2, test3")
        
        # Should have called sleep for rate limiting
        self.assertTrue(mock_sleep.called)
        
        # Verify sleep was called with small delay (0.1 seconds)
        sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
        self.assertTrue(any(delay <= 0.2 for delay in sleep_calls))


class TestAPIErrorRecovery(unittest.TestCase):
    """Test API error recovery and fallback mechanisms"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = Mock(spec=Config)
        self.config.temp_dir = tempfile.mkdtemp()
        self.config.min_images = 3
        self.config.max_images = 5
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.config.temp_dir, ignore_errors=True)
    
    @patch('requests.Session.get')
    def test_unsplash_fallback_search(self, mock_get):
        """Test Unsplash fallback search when original search fails"""
        self.config.unsplash_access_key = "test_key"
        
        # Mock responses: first search returns no results, fallback succeeds
        empty_response = Mock()
        empty_response.status_code = 200
        empty_response.json.return_value = {'results': []}
        
        fallback_response = Mock()
        fallback_response.status_code = 200
        fallback_response.json.return_value = {
            'results': [
                {
                    'id': 'fallback_img',
                    'urls': {'regular': 'url', 'full': 'url'},
                    'description': 'Fallback image',
                    'width': 1920,
                    'height': 1080,
                    'user': {'name': 'Fallback User'}
                }
            ] * 3  # Return 3 fallback images
        }
        
        mock_get.side_effect = [empty_response, fallback_response]
        
        fetcher = ImageFetcher(self.config)
        
        with patch.object(fetcher, '_download_and_validate_images') as mock_download:
            mock_download.return_value = [{'id': 'fallback_img'}] * 3
            
            result = fetcher.fetch_images("very_obscure_search_term")
            
            # Should have made two API calls (original + fallback)
            self.assertEqual(mock_get.call_count, 2)
            
            # Verify fallback search was for "nature landscape"
            fallback_call = mock_get.call_args_list[1]
            self.assertEqual(fallback_call[1]['params']['query'], 'nature landscape')
            
            # Should return fallback results
            self.assertEqual(len(result), 3)


if __name__ == '__main__':
    unittest.main()