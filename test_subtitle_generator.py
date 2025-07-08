import unittest
from unittest.mock import Mock, patch, mock_open, MagicMock, call
import os
import tempfile
import shutil
import subprocess
from subtitle_generator import SubtitleGenerator
from config import Config


class TestSubtitleGenerator(unittest.TestCase):
    """Test cases for SubtitleGenerator class"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create a mock config
        self.mock_config = Mock(spec=Config)
        self.mock_config.output_dir = tempfile.mkdtemp()
        self.mock_config.temp_dir = tempfile.mkdtemp()
        
        # Create test directories
        self.test_output_dir = tempfile.mkdtemp()
        self.test_temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """Clean up test fixtures"""
        # Clean up temporary directories
        shutil.rmtree(self.mock_config.output_dir, ignore_errors=True)
        shutil.rmtree(self.mock_config.temp_dir, ignore_errors=True)
        shutil.rmtree(self.test_output_dir, ignore_errors=True)
        shutil.rmtree(self.test_temp_dir, ignore_errors=True)
    
    @patch('os.path.exists')
    def test_init_with_japanese_font(self, mock_exists):
        """Test SubtitleGenerator initialization with Japanese font detection"""
        # Mock font file existence
        mock_exists.side_effect = lambda path: path == "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc"
        
        generator = SubtitleGenerator(self.mock_config)
        
        self.assertEqual(generator.config, self.mock_config)
        self.assertEqual(generator.font_path, "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc")
    
    @patch('os.path.exists')
    def test_init_with_fallback_font(self, mock_exists):
        """Test SubtitleGenerator initialization with fallback font"""
        # Mock no font files exist, should use default
        mock_exists.return_value = False
        
        generator = SubtitleGenerator(self.mock_config)
        
        self.assertEqual(generator.config, self.mock_config)
        self.assertEqual(generator.font_path, "/System/Library/Fonts/Arial.ttf")
    
    def test_split_text_into_sentences(self):
        """Test text splitting into sentences"""
        generator = SubtitleGenerator(self.mock_config)
        
        # Test normal text
        text = "これは最初の文章です。これは二番目の文章です！これは三番目の文章ですか？"
        sentences = generator._split_text_into_sentences(text)
        
        expected = [
            "これは最初の文章です。",
            "これは二番目の文章です！",
            "これは三番目の文章ですか？"
        ]
        self.assertEqual(sentences, expected)
        
        # Test multiline text
        multiline_text = "最初の行です。\n二番目の行です！\n\n三番目の行ですか？"
        sentences = generator._split_text_into_sentences(multiline_text)
        
        expected = [
            "最初の行です。",
            "二番目の行です！",
            "三番目の行ですか？"
        ]
        self.assertEqual(sentences, expected)
    
    def test_calculate_subtitle_timing(self):
        """Test subtitle timing calculation"""
        generator = SubtitleGenerator(self.mock_config)
        
        sentences = ["短い文。", "これは少し長い文章です。", "最後の文章。"]
        total_duration = 30.0
        
        timings = generator._calculate_subtitle_timing(sentences, total_duration)
        
        # Check that we have the right number of entries
        self.assertEqual(len(timings), 3)
        
        # Check timing structure
        for start_time, end_time, text in timings:
            self.assertIsInstance(start_time, float)
            self.assertIsInstance(end_time, float)
            self.assertIsInstance(text, str)
            self.assertGreaterEqual(end_time, start_time)
            self.assertLessEqual(end_time, total_duration)
        
        # Check that timings are sequential
        for i in range(len(timings) - 1):
            self.assertLessEqual(timings[i][1], timings[i+1][0])
    
    def test_seconds_to_srt_timestamp(self):
        """Test SRT timestamp conversion"""
        generator = SubtitleGenerator(self.mock_config)
        
        # Test various time values
        test_cases = [
            (0.0, "00:00:00,000"),
            (1.5, "00:00:01,500"),
            (65.250, "00:01:05,250"),
            (3661.123, "01:01:01,123")
        ]
        
        for seconds, expected in test_cases:
            result = generator._seconds_to_srt_timestamp(seconds)
            self.assertEqual(result, expected)
    
    def test_generate_srt_content(self):
        """Test SRT content generation"""
        generator = SubtitleGenerator(self.mock_config)
        
        subtitle_entries = [
            (0.0, 5.0, "最初の字幕です。"),
            (5.0, 10.0, "二番目の字幕です。"),
            (10.0, 15.0, "最後の字幕です。")
        ]
        
        srt_content = generator._generate_srt_content(subtitle_entries)
        
        expected_content = """1
00:00:00,000 --> 00:00:05,000
最初の字幕です。

2
00:00:05,000 --> 00:00:10,000
二番目の字幕です。

3
00:00:10,000 --> 00:00:15,000
最後の字幕です。

"""
        
        self.assertEqual(srt_content, expected_content)
    
    @patch('builtins.open', new_callable=mock_open)
    def test_create_srt_file(self, mock_file):
        """Test SRT file creation"""
        generator = SubtitleGenerator(self.mock_config)
        
        script_text = "これはテストです。もう一つの文章です。"
        audio_duration = 10.0
        output_path = "/test/output.srt"
        
        result = generator.create_srt_file(script_text, audio_duration, output_path)
        
        # Check that file was opened and written
        mock_file.assert_called_once_with(output_path, 'w', encoding='utf-8')
        mock_file().write.assert_called_once()
        
        # Check return value
        self.assertEqual(result, output_path)
    
    @patch('builtins.open', new_callable=mock_open)
    def test_create_srt_file_error_handling(self, mock_file):
        """Test SRT file creation error handling"""
        generator = SubtitleGenerator(self.mock_config)
        
        # Mock file write error
        mock_file.side_effect = IOError("Permission denied")
        
        with self.assertRaises(Exception) as context:
            generator.create_srt_file("テスト", 10.0, "/test/output.srt")
        
        self.assertIn("SRTファイル生成エラー", str(context.exception))
    
    @patch('subprocess.run')
    def test_add_subtitles_to_video_success(self, mock_run):
        """Test successful subtitle addition to video"""
        generator = SubtitleGenerator(self.mock_config)
        
        # Mock successful subprocess run
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        
        video_path = "/test/input.mp4"
        subtitle_path = "/test/input.srt"
        output_path = "/test/output.mp4"
        
        result = generator.add_subtitles_to_video(video_path, subtitle_path, output_path)
        
        # Check that subprocess was called with correct command
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        self.assertEqual(call_args[0], 'ffmpeg')
        self.assertIn(video_path, call_args)
        self.assertIn(output_path, call_args)
        
        # Check return value
        self.assertEqual(result, output_path)
    
    @patch('subprocess.run')
    def test_add_subtitles_to_video_ffmpeg_error(self, mock_run):
        """Test FFmpeg error handling"""
        generator = SubtitleGenerator(self.mock_config)
        
        # Mock FFmpeg error
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "FFmpeg error message"
        mock_run.return_value = mock_result
        
        with self.assertRaises(Exception) as context:
            generator.add_subtitles_to_video("/test/input.mp4", "/test/input.srt", "/test/output.mp4")
        
        self.assertIn("FFmpeg error", str(context.exception))
    
    @patch('subprocess.run')
    def test_add_subtitles_to_video_ffmpeg_not_found(self, mock_run):
        """Test FFmpeg not found error"""
        generator = SubtitleGenerator(self.mock_config)
        
        # Mock FileNotFoundError
        mock_run.side_effect = FileNotFoundError()
        
        with self.assertRaises(Exception) as context:
            generator.add_subtitles_to_video("/test/input.mp4", "/test/input.srt", "/test/output.mp4")
        
        self.assertIn("FFmpegが見つかりません", str(context.exception))
    
    @patch('subprocess.run')
    def test_check_ffmpeg_available_true(self, mock_run):
        """Test FFmpeg availability check - available"""
        generator = SubtitleGenerator(self.mock_config)
        
        # Mock successful FFmpeg version check
        mock_run.return_value = Mock()
        
        result = generator.check_ffmpeg_available()
        
        self.assertTrue(result)
        mock_run.assert_called_once_with(['ffmpeg', '-version'], capture_output=True, check=True)
    
    @patch('subprocess.run')
    def test_check_ffmpeg_available_false_not_found(self, mock_run):
        """Test FFmpeg availability check - not found"""
        generator = SubtitleGenerator(self.mock_config)
        
        # Mock FileNotFoundError
        mock_run.side_effect = FileNotFoundError()
        
        result = generator.check_ffmpeg_available()
        
        self.assertFalse(result)
    
    @patch('subprocess.run')
    def test_check_ffmpeg_available_false_error(self, mock_run):
        """Test FFmpeg availability check - error"""
        generator = SubtitleGenerator(self.mock_config)
        
        # Mock subprocess error
        mock_run.side_effect = subprocess.CalledProcessError(1, 'ffmpeg')
        
        result = generator.check_ffmpeg_available()
        
        self.assertFalse(result)
    
    @patch('os.makedirs')
    @patch.object(SubtitleGenerator, 'create_srt_file')
    @patch.object(SubtitleGenerator, 'add_subtitles_to_video')
    def test_generate_subtitled_video_success(self, mock_add_subtitles, mock_create_srt, mock_makedirs):
        """Test successful subtitled video generation"""
        generator = SubtitleGenerator(self.mock_config)
        
        # Mock successful operations
        srt_path = "/test/output/video.srt"
        subtitled_path = "/test/output/video_subtitled.mp4"
        
        mock_create_srt.return_value = srt_path
        mock_add_subtitles.return_value = subtitled_path
        
        video_path = "/test/input/video.mp4"
        script_text = "テストスクリプト"
        audio_duration = 30.0
        output_dir = "/test/output"
        
        result = generator.generate_subtitled_video(video_path, script_text, audio_duration, output_dir)
        
        # Check that directories were created
        mock_makedirs.assert_called_once_with(output_dir, exist_ok=True)
        
        # Check that SRT file was created
        mock_create_srt.assert_called_once_with(script_text, audio_duration, srt_path)
        
        # Check that subtitles were added to video
        mock_add_subtitles.assert_called_once_with(video_path, srt_path, subtitled_path)
        
        # Check return value
        self.assertEqual(result, subtitled_path)
    
    @patch('os.makedirs')
    @patch.object(SubtitleGenerator, 'create_srt_file')
    def test_generate_subtitled_video_error_handling(self, mock_create_srt, mock_makedirs):
        """Test error handling in subtitled video generation"""
        generator = SubtitleGenerator(self.mock_config)
        
        # Mock SRT creation error
        mock_create_srt.side_effect = Exception("SRT creation failed")
        
        with self.assertRaises(Exception) as context:
            generator.generate_subtitled_video("/test/video.mp4", "テスト", 30.0, "/test/output")
        
        self.assertIn("字幕付き動画生成エラー", str(context.exception))


# Integration test for subtitle generator
class TestSubtitleGeneratorIntegration(unittest.TestCase):
    """Integration tests for SubtitleGenerator"""
    
    def setUp(self):
        """Set up integration test fixtures"""
        self.mock_config = Mock(spec=Config)
        self.test_dir = tempfile.mkdtemp()
        self.mock_config.output_dir = self.test_dir
        self.mock_config.temp_dir = self.test_dir
    
    def tearDown(self):
        """Clean up integration test fixtures"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_text_processing_pipeline(self):
        """Test the complete text processing pipeline"""
        generator = SubtitleGenerator(self.mock_config)
        
        # Test with realistic Japanese text
        script_text = """
        人工知能は現代社会において重要な技術です。
        機械学習やディープラーニングが発達しています。
        AIは私たちの生活を大きく変える可能性があります。
        """
        
        # Test sentence splitting
        sentences = generator._split_text_into_sentences(script_text)
        self.assertGreater(len(sentences), 0)
        self.assertTrue(all(sentence.strip() for sentence in sentences))
        
        # Test timing calculation
        timings = generator._calculate_subtitle_timing(sentences, 30.0)
        self.assertEqual(len(timings), len(sentences))
        
        # Test SRT content generation
        srt_content = generator._generate_srt_content(timings)
        self.assertIn("人工知能", srt_content)
        self.assertIn("-->", srt_content)
        self.assertIn("1\n", srt_content)


if __name__ == '__main__':
    unittest.main()