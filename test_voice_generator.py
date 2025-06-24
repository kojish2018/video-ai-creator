import unittest
from unittest.mock import Mock, patch, mock_open, MagicMock
import os
import json
import wave
import requests
from voice_generator import VoiceGenerator
from config import Config


class TestVoiceGenerator(unittest.TestCase):
    """Test cases for VoiceGenerator class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = Mock(spec=Config)
        self.config.voicevox_server_url = "http://localhost:50021"
        self.config.speaker_id = 1
        self.config.temp_dir = "/tmp/test"
        
        # Create temp directory for testing
        os.makedirs(self.config.temp_dir, exist_ok=True)
    
    def tearDown(self):
        """Clean up test fixtures"""
        # Clean up test temp directory
        if os.path.exists(self.config.temp_dir):
            import shutil
            shutil.rmtree(self.config.temp_dir, ignore_errors=True)
    
    def test_init(self):
        """Test VoiceGenerator initialization"""
        generator = VoiceGenerator(self.config)
        
        self.assertEqual(generator.config, self.config)
        self.assertEqual(generator.base_url, "http://localhost:50021")
        self.assertIsInstance(generator.session, requests.Session)
        self.assertEqual(generator.session.timeout, 30)
    
    def test_init_strip_trailing_slash(self):
        """Test initialization with trailing slash in URL"""
        self.config.voicevox_server_url = "http://localhost:50021/"
        generator = VoiceGenerator(self.config)
        
        self.assertEqual(generator.base_url, "http://localhost:50021")
    
    def test_preprocess_text_basic(self):
        """Test basic text preprocessing"""
        generator = VoiceGenerator(self.config)
        
        # Test whitespace normalization
        text = "  こんにちは   世界  "
        result = generator._preprocess_text(text)
        self.assertEqual(result, "こんにちは 世界")
        
        # Test punctuation with pauses
        text = "こんにちは。元気ですか？そうですね！"
        result = generator._preprocess_text(text)
        expected = "こんにちは。、元気ですか？、そうですね！、"
        self.assertEqual(result, expected)
    
    def test_preprocess_text_special_characters(self):
        """Test special character replacement"""
        generator = VoiceGenerator(self.config)
        
        text = "AI・ML～50%の確率で成功…"
        result = generator._preprocess_text(text)
        expected = "AIとMLから50パーセントの確率で成功。"
        self.assertEqual(result, expected)
    
    def test_generate_voice_empty_script(self):
        """Test voice generation with empty script"""
        generator = VoiceGenerator(self.config)
        
        with self.assertRaises(ValueError) as context:
            generator.generate_voice("")
        
        self.assertIn("Script text cannot be empty", str(context.exception))
        
        with self.assertRaises(ValueError) as context:
            generator.generate_voice("   ")
        
        self.assertIn("Script text cannot be empty", str(context.exception))
    
    @patch('requests.Session.post')
    def test_create_audio_query_success(self, mock_post):
        """Test successful audio query creation"""
        generator = VoiceGenerator(self.config)
        
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'accent_phrases': [{'moras': [{'text': 'テ'}, {'text': 'ス'}, {'text': 'ト'}]}],
            'speedScale': 1.0
        }
        mock_post.return_value = mock_response
        
        result = generator._create_audio_query("テスト")
        
        self.assertIn('accent_phrases', result)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertIn('audio_query', args[0])
        self.assertEqual(kwargs['params']['text'], "テスト")
        self.assertEqual(kwargs['params']['speaker'], 1)
    
    @patch('requests.Session.post')
    def test_create_audio_query_errors(self, mock_post):
        """Test audio query creation error handling"""
        generator = VoiceGenerator(self.config)
        
        # Test 400 error
        mock_response = Mock()
        mock_response.status_code = 400
        mock_post.return_value = mock_response
        
        with self.assertRaises(RuntimeError) as context:
            generator._create_audio_query("test")
        self.assertIn("Invalid text or speaker ID", str(context.exception))
        
        # Test 503 error
        mock_response.status_code = 503
        with self.assertRaises(RuntimeError) as context:
            generator._create_audio_query("test")
        self.assertIn("VOICEVOX server is not running", str(context.exception))
        
        # Test other error
        mock_response.status_code = 500
        with self.assertRaises(RuntimeError) as context:
            generator._create_audio_query("test")
        self.assertIn("VOICEVOX API error: 500", str(context.exception))
    
    @patch('requests.Session.post')
    def test_create_audio_query_network_errors(self, mock_post):
        """Test audio query network error handling"""
        generator = VoiceGenerator(self.config)
        
        # Test connection error
        mock_post.side_effect = requests.exceptions.ConnectionError("Connection failed")
        
        with self.assertRaises(RuntimeError) as context:
            generator._create_audio_query("test")
        self.assertIn("Cannot connect to VOICEVOX server", str(context.exception))
        
        # Test timeout error
        mock_post.side_effect = requests.exceptions.Timeout("Timeout")
        
        with self.assertRaises(RuntimeError) as context:
            generator._create_audio_query("test")
        self.assertIn("VOICEVOX server timeout", str(context.exception))
        
        # Test generic request error
        mock_post.side_effect = requests.exceptions.RequestException("Network error")
        
        with self.assertRaises(RuntimeError) as context:
            generator._create_audio_query("test")
        self.assertIn("Network error", str(context.exception))
    
    def test_estimate_duration(self):
        """Test audio duration estimation"""
        generator = VoiceGenerator(self.config)
        
        # Test with accent phrases
        audio_query = {
            'accent_phrases': [
                {'moras': [{'text': 'テ'}, {'text': 'ス'}, {'text': 'ト'}]}
            ],
            'speedScale': 1.0
        }
        
        duration = generator._estimate_duration(audio_query)
        expected = 3 * 0.15  # 3 moras * 0.15 seconds per mora
        self.assertEqual(duration, expected)
        
        # Test with speed scale
        audio_query['speedScale'] = 2.0
        duration = generator._estimate_duration(audio_query)
        expected = (3 * 0.15) / 2.0
        self.assertEqual(duration, expected)
    
    def test_estimate_duration_fallback(self):
        """Test duration estimation fallback"""
        generator = VoiceGenerator(self.config)
        
        # Test with query that has no accent_phrases or valid data (should use fallback)
        audio_query = {"invalid": "data"}
        
        duration = generator._estimate_duration(audio_query)
        # Since accent_phrases is empty, total_moras will be 0, so base_duration is 0
        # This should return 0.0, not use the fallback
        self.assertEqual(duration, 0.0)
    
    @patch('requests.Session.post')
    def test_synthesize_voice_success(self, mock_post):
        """Test successful voice synthesis"""
        generator = VoiceGenerator(self.config)
        
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'fake audio data'
        mock_post.return_value = mock_response
        
        audio_query = {'accent_phrases': [], 'speedScale': 1.0}
        result = generator._synthesize_voice(audio_query)
        
        self.assertEqual(result, b'fake audio data')
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertIn('synthesis', args[0])
        self.assertEqual(kwargs['json'], audio_query)
    
    @patch('requests.Session.post')
    def test_synthesize_voice_speed_adjustment(self, mock_post):
        """Test voice synthesis with speed adjustment for long content"""
        generator = VoiceGenerator(self.config)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'fake audio data'
        mock_post.return_value = mock_response
        
        # Create query that would result in > 30 second duration
        long_audio_query = {
            'accent_phrases': [
                {'moras': [{'text': 'あ'} for _ in range(250)]}  # 250 moras = 37.5 seconds
            ],
            'speedScale': 1.0
        }
        
        with patch.object(generator, '_estimate_duration', return_value=35):
            generator._synthesize_voice(long_audio_query)
        
        # Speed should be adjusted
        call_args = mock_post.call_args
        adjusted_query = call_args[1]['json']
        self.assertGreater(adjusted_query['speedScale'], 1.0)
    
    @patch('requests.Session.post')
    def test_synthesize_voice_error(self, mock_post):
        """Test voice synthesis error handling"""
        generator = VoiceGenerator(self.config)
        
        # Test API error
        mock_response = Mock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response
        
        with self.assertRaises(RuntimeError) as context:
            generator._synthesize_voice({})
        self.assertIn("Voice synthesis failed: 500", str(context.exception))
        
        # Test network error
        mock_post.side_effect = requests.exceptions.RequestException("Network error")
        
        with self.assertRaises(RuntimeError) as context:
            generator._synthesize_voice({})
        self.assertIn("Voice synthesis network error", str(context.exception))
    
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists')
    @patch('wave.open')
    def test_save_audio_file_success(self, mock_wave_open, mock_exists, mock_file_open):
        """Test successful audio file saving"""
        generator = VoiceGenerator(self.config)
        
        # Mock file operations
        mock_exists.return_value = True
        mock_wav_file = Mock()
        mock_wav_file.getnframes.return_value = 1000  # Non-empty file
        mock_wave_open.return_value.__enter__.return_value = mock_wav_file
        
        audio_data = b'fake audio data'
        output_path = "/tmp/test/test.wav"
        
        generator._save_audio_file(audio_data, output_path)
        
        mock_file_open.assert_called_once_with(output_path, 'wb')
        mock_file_open().write.assert_called_once_with(audio_data)
        mock_wave_open.assert_called_once_with(output_path, 'rb')
    
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists')
    def test_save_audio_file_not_created(self, mock_exists, mock_file_open):
        """Test audio file saving when file is not created"""
        generator = VoiceGenerator(self.config)
        
        mock_exists.return_value = False  # File not created
        
        with self.assertRaises(RuntimeError) as context:
            generator._save_audio_file(b'data', "/tmp/test.wav")
        
        self.assertIn("Failed to create audio file", str(context.exception))
    
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists')
    @patch('wave.open')
    def test_save_audio_file_empty(self, mock_wave_open, mock_exists, mock_file_open):
        """Test audio file saving with empty audio"""
        generator = VoiceGenerator(self.config)
        
        mock_exists.return_value = True
        mock_wav_file = Mock()
        mock_wav_file.getnframes.return_value = 0  # Empty file
        mock_wave_open.return_value.__enter__.return_value = mock_wav_file
        
        with self.assertRaises(RuntimeError) as context:
            generator._save_audio_file(b'data', "/tmp/test.wav")
        
        self.assertIn("Generated audio file is empty", str(context.exception))
    
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists')
    @patch('wave.open')
    def test_save_audio_file_corrupted(self, mock_wave_open, mock_exists, mock_file_open):
        """Test audio file saving with corrupted file"""
        generator = VoiceGenerator(self.config)
        
        mock_exists.return_value = True
        mock_wave_open.side_effect = wave.Error("Corrupted file")
        
        with self.assertRaises(RuntimeError) as context:
            generator._save_audio_file(b'data', "/tmp/test.wav")
        
        self.assertIn("Generated audio file is corrupted", str(context.exception))
    
    @patch('builtins.open', side_effect=IOError("Permission denied"))
    def test_save_audio_file_io_error(self, mock_file_open):
        """Test audio file saving with IO error"""
        generator = VoiceGenerator(self.config)
        
        with self.assertRaises(RuntimeError) as context:
            generator._save_audio_file(b'data', "/tmp/test.wav")
        
        self.assertIn("Failed to save audio file", str(context.exception))
    
    @patch('wave.open')
    def test_get_audio_duration_success(self, mock_wave_open):
        """Test successful audio duration calculation"""
        generator = VoiceGenerator(self.config)
        
        mock_wav_file = Mock()
        mock_wav_file.getnframes.return_value = 44100  # 1 second at 44.1kHz
        mock_wav_file.getframerate.return_value = 44100
        mock_wave_open.return_value.__enter__.return_value = mock_wav_file
        
        duration = generator._get_audio_duration("/path/to/audio.wav")
        
        self.assertEqual(duration, 1.0)
    
    @patch('wave.open')
    def test_get_audio_duration_error(self, mock_wave_open):
        """Test audio duration calculation with error"""
        generator = VoiceGenerator(self.config)
        
        mock_wave_open.side_effect = Exception("File error")
        
        duration = generator._get_audio_duration("/path/to/audio.wav")
        
        self.assertEqual(duration, 0.0)
    
    def test_handle_voice_error_connection(self):
        """Test voice error handling for connection issues"""
        generator = VoiceGenerator(self.config)
        
        with self.assertRaises(RuntimeError) as context:
            generator._handle_voice_error(Exception("Connection failed"))
        
        self.assertIn("VOICEVOX server is not accessible", str(context.exception))
        
        with self.assertRaises(RuntimeError) as context:
            generator._handle_voice_error(Exception("Server not running"))
        
        self.assertIn("VOICEVOX server is not accessible", str(context.exception))
    
    def test_handle_voice_error_timeout(self):
        """Test voice error handling for timeout"""
        generator = VoiceGenerator(self.config)
        
        with self.assertRaises(RuntimeError) as context:
            generator._handle_voice_error(Exception("Request timeout"))
        
        self.assertIn("VOICEVOX server timeout", str(context.exception))
    
    def test_handle_voice_error_speaker(self):
        """Test voice error handling for speaker issues"""
        generator = VoiceGenerator(self.config)
        
        with self.assertRaises(RuntimeError) as context:
            generator._handle_voice_error(Exception("Invalid speaker ID"))
        
        self.assertIn("Invalid speaker ID", str(context.exception))
    
    def test_handle_voice_error_generic(self):
        """Test voice error handling for generic errors"""
        generator = VoiceGenerator(self.config)
        
        with self.assertRaises(RuntimeError) as context:
            generator._handle_voice_error(Exception("Unknown error"))
        
        self.assertIn("Voice generation failed", str(context.exception))
    
    @patch('os.listdir')
    @patch('os.path.exists')
    @patch('os.remove')
    def test_cleanup_temp_audio(self, mock_remove, mock_exists, mock_listdir):
        """Test cleanup of temporary audio files"""
        generator = VoiceGenerator(self.config)
        
        # Mock temp files
        mock_listdir.return_value = [
            'voice_123.wav',
            'voice_456.wav',
            'other_file.txt',  # Should be ignored
            'voice_789.wav'
        ]
        mock_exists.return_value = True
        
        generator.cleanup_temp_audio()
        
        # Should remove only voice files
        self.assertEqual(mock_remove.call_count, 3)
        mock_remove.assert_any_call(os.path.join(self.config.temp_dir, 'voice_123.wav'))
        mock_remove.assert_any_call(os.path.join(self.config.temp_dir, 'voice_456.wav'))
        mock_remove.assert_any_call(os.path.join(self.config.temp_dir, 'voice_789.wav'))
    
    @patch('requests.Session.get')
    def test_test_connection_success(self, mock_get):
        """Test successful connection test"""
        generator = VoiceGenerator(self.config)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        result = generator.test_connection()
        
        self.assertTrue(result)
        mock_get.assert_called_once_with("http://localhost:50021/version", timeout=5)
    
    @patch('requests.Session.get')
    def test_test_connection_failure(self, mock_get):
        """Test connection test failure"""
        generator = VoiceGenerator(self.config)
        
        # Test API error
        mock_response = Mock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response
        
        result = generator.test_connection()
        self.assertFalse(result)
        
        # Test network error
        mock_get.side_effect = Exception("Network error")
        
        result = generator.test_connection()
        self.assertFalse(result)
    
    @patch('requests.Session.get')
    def test_get_available_speakers_success(self, mock_get):
        """Test successful speakers retrieval"""
        generator = VoiceGenerator(self.config)
        
        mock_speakers = [
            {'name': 'ずんだもん', 'speaker_uuid': 'test1'},
            {'name': '四国めたん', 'speaker_uuid': 'test2'}
        ]
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_speakers
        mock_get.return_value = mock_response
        
        result = generator.get_available_speakers()
        
        self.assertEqual(result, mock_speakers)
        mock_get.assert_called_once_with("http://localhost:50021/speakers", timeout=10)
    
    @patch('requests.Session.get')
    def test_get_available_speakers_failure(self, mock_get):
        """Test speakers retrieval failure"""
        generator = VoiceGenerator(self.config)
        
        # Test API error
        mock_response = Mock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response
        
        result = generator.get_available_speakers()
        self.assertEqual(result, [])
        
        # Test network error
        mock_get.side_effect = Exception("Network error")
        
        result = generator.get_available_speakers()
        self.assertEqual(result, [])
    
    @patch.object(VoiceGenerator, '_preprocess_text')
    @patch.object(VoiceGenerator, '_create_audio_query')
    @patch.object(VoiceGenerator, '_synthesize_voice')
    @patch.object(VoiceGenerator, '_save_audio_file')
    @patch.object(VoiceGenerator, '_get_audio_duration')
    @patch('time.time')
    def test_generate_voice_success(self, mock_time, mock_duration, mock_save, 
                                   mock_synthesize, mock_query, mock_preprocess):
        """Test successful voice generation"""
        generator = VoiceGenerator(self.config)
        
        # Mock all dependencies
        mock_time.return_value = 1234567890
        mock_preprocess.return_value = "processed text"
        mock_query.return_value = {'test': 'query'}
        mock_synthesize.return_value = b'audio data'
        mock_duration.return_value = 25.0  # Within 30-second limit
        
        result = generator.generate_voice("test script")
        
        expected_path = os.path.join(self.config.temp_dir, "voice_1234567890.wav")
        self.assertEqual(result, expected_path)
        
        mock_preprocess.assert_called_once_with("test script")
        mock_query.assert_called_once_with("processed text")
        mock_synthesize.assert_called_once_with({'test': 'query'})
        mock_save.assert_called_once_with(b'audio data', expected_path)
    
    @patch.object(VoiceGenerator, '_preprocess_text')
    @patch.object(VoiceGenerator, '_create_audio_query')
    @patch.object(VoiceGenerator, '_synthesize_voice')
    @patch.object(VoiceGenerator, '_save_audio_file')
    @patch.object(VoiceGenerator, '_get_audio_duration')
    def test_generate_voice_custom_filename(self, mock_duration, mock_save, 
                                           mock_synthesize, mock_query, mock_preprocess):
        """Test voice generation with custom filename"""
        generator = VoiceGenerator(self.config)
        
        # Mock all dependencies
        mock_preprocess.return_value = "processed text"
        mock_query.return_value = {'test': 'query'}
        mock_synthesize.return_value = b'audio data'
        mock_duration.return_value = 25.0
        
        result = generator.generate_voice("test script", "custom.wav")
        
        expected_path = os.path.join(self.config.temp_dir, "custom.wav")
        self.assertEqual(result, expected_path)
        mock_save.assert_called_once_with(b'audio data', expected_path)
    
    @patch.object(VoiceGenerator, '_get_audio_duration')
    @patch.object(VoiceGenerator, '_save_audio_file')
    @patch.object(VoiceGenerator, '_synthesize_voice')
    @patch.object(VoiceGenerator, '_create_audio_query')
    @patch.object(VoiceGenerator, '_preprocess_text')
    @patch('builtins.print')
    def test_generate_voice_duration_warning(self, mock_print, mock_preprocess, 
                                           mock_query, mock_synthesize, mock_save, mock_duration):
        """Test voice generation with duration warning"""
        generator = VoiceGenerator(self.config)
        
        # Mock dependencies with long duration
        mock_preprocess.return_value = "processed text"
        mock_query.return_value = {'test': 'query'}
        mock_synthesize.return_value = b'audio data'
        mock_duration.return_value = 40.0  # Exceeds 35-second warning threshold
        
        generator.generate_voice("test script")
        
        # Should print warning
        mock_print.assert_called()
        warning_call = [call for call in mock_print.call_args_list 
                       if 'Warning' in str(call)]
        self.assertTrue(len(warning_call) > 0)


class TestCreateVoiceGenerator(unittest.TestCase):
    """Test cases for create_voice_generator factory function"""
    
    @patch('voice_generator.Config')
    def test_create_voice_generator(self, mock_config_class):
        """Test factory function creates VoiceGenerator instance"""
        from voice_generator import create_voice_generator
        
        mock_config = Mock()
        mock_config_class.return_value = mock_config
        
        generator = create_voice_generator()
        
        self.assertIsInstance(generator, VoiceGenerator)
        mock_config_class.assert_called_once()


if __name__ == '__main__':
    unittest.main()