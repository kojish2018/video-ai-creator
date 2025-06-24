import unittest
from unittest.mock import Mock, patch, MagicMock
import os
import tempfile
from video_creator import VideoCreator
from config import Config


class TestVideoCreator(unittest.TestCase):
    """Test cases for VideoCreator class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = Mock(spec=Config)
        self.config.video_duration = 30
        self.config.video_width = 1920
        self.config.video_height = 1080
        self.config.video_fps = 30
        self.config.output_dir = "/tmp/test_output"
        
        # Create temp directories for testing
        os.makedirs(self.config.output_dir, exist_ok=True)
    
    def tearDown(self):
        """Clean up test fixtures"""
        # Clean up test directories
        for test_dir in [self.config.output_dir]:
            if os.path.exists(test_dir):
                import shutil
                shutil.rmtree(test_dir, ignore_errors=True)
    
    def test_init(self):
        """Test VideoCreator initialization"""
        creator = VideoCreator(self.config)
        
        self.assertEqual(creator.config, self.config)
        self.assertEqual(creator.target_duration, 30)
        self.assertEqual(creator.video_size, (1920, 1080))
        self.assertEqual(creator.fps, 30)
    
    def test_create_video_no_images(self):
        """Test video creation with no images"""
        creator = VideoCreator(self.config)
        
        with self.assertRaises(ValueError) as context:
            creator.create_video([], "audio.wav")
        
        self.assertIn("No images provided", str(context.exception))
    
    def test_create_video_audio_not_found(self):
        """Test video creation with non-existent audio file"""
        creator = VideoCreator(self.config)
        
        images = [{'local_path': 'test.jpg'}]
        
        with self.assertRaises(ValueError) as context:
            creator.create_video(images, "nonexistent_audio.wav")
        
        self.assertIn("Audio file not found", str(context.exception))
    
    @patch('video_creator.AudioFileClip')
    @patch.object(VideoCreator, '_create_image_slideshow')
    @patch.object(VideoCreator, '_render_video')
    @patch('time.time')
    def test_create_video_success(self, mock_time, mock_render, mock_slideshow, mock_audio_clip):
        """Test successful video creation"""
        creator = VideoCreator(self.config)
        
        # Mock dependencies
        mock_time.return_value = 1234567890
        
        mock_audio = Mock()
        mock_audio.duration = 25.0
        mock_audio_clip.return_value = mock_audio
        
        mock_video = Mock()
        mock_slideshow.return_value = mock_video
        
        mock_final_clip = Mock()
        mock_video.set_audio.return_value = mock_final_clip
        
        # Create test audio file
        test_audio = os.path.join(self.config.output_dir, "test_audio.wav")
        with open(test_audio, 'wb') as f:
            f.write(b'fake audio data')
        
        images = [{'local_path': 'test.jpg'}]
        
        result = creator.create_video(images, test_audio)
        
        expected_path = os.path.join(self.config.output_dir, "video_1234567890.mp4")
        self.assertEqual(result, expected_path)
        
        mock_slideshow.assert_called_once_with(images, 25.0)  # Should use actual audio duration
        mock_video.set_audio.assert_called_once()
        mock_render.assert_called_once_with(mock_final_clip, expected_path)
        
        # Check cleanup calls
        mock_audio.close.assert_called_once()
        mock_video.close.assert_called_once()
        mock_final_clip.close.assert_called_once()
    
    @patch('video_creator.AudioFileClip')
    @patch.object(VideoCreator, '_create_image_slideshow')
    @patch.object(VideoCreator, '_render_video')
    def test_create_video_custom_filename(self, mock_render, mock_slideshow, mock_audio_clip):
        """Test video creation with custom filename"""
        creator = VideoCreator(self.config)
        
        # Mock dependencies
        mock_audio = Mock()
        mock_audio.duration = 25.0
        mock_audio_clip.return_value = mock_audio
        
        mock_video = Mock()
        mock_slideshow.return_value = mock_video
        mock_final_clip = Mock()
        mock_video.set_audio.return_value = mock_final_clip
        
        # Create test audio file
        test_audio = os.path.join(self.config.output_dir, "test_audio.wav")
        with open(test_audio, 'wb') as f:
            f.write(b'fake audio data')
        
        images = [{'local_path': 'test.jpg'}]
        
        result = creator.create_video(images, test_audio, "custom_video.mp4")
        
        expected_path = os.path.join(self.config.output_dir, "custom_video.mp4")
        self.assertEqual(result, expected_path)
        mock_render.assert_called_once_with(mock_final_clip, expected_path)
    
    @patch('video_creator.AudioFileClip')
    @patch.object(VideoCreator, '_create_image_slideshow')
    def test_create_video_duration_limit(self, mock_slideshow, mock_audio_clip):
        """Test video creation with audio longer than target duration"""
        creator = VideoCreator(self.config)
        
        # Mock long audio
        mock_audio = Mock()
        mock_audio.duration = 45.0  # Longer than 30-second target
        mock_audio_clip.return_value = mock_audio
        
        mock_video = Mock()
        mock_slideshow.return_value = mock_video
        mock_final_clip = Mock()
        mock_video.set_audio.return_value = mock_final_clip
        
        # Create test audio file
        test_audio = os.path.join(self.config.output_dir, "test_audio.wav")
        with open(test_audio, 'wb') as f:
            f.write(b'fake audio data')
        
        images = [{'local_path': 'test.jpg'}]
        
        with patch.object(creator, '_render_video'):
            creator.create_video(images, test_audio)
        
        # Should use target duration (30s) instead of actual duration (45s)
        mock_slideshow.assert_called_once_with(images, 30.0)
        mock_audio.subclip.assert_called_once_with(0, 30.0)
    
    @patch('video_creator.ImageClip')
    @patch('video_creator.concatenate_videoclips')
    @patch('os.path.exists')
    def test_create_image_slideshow_success(self, mock_exists, mock_concat, mock_image_clip):
        """Test successful image slideshow creation"""
        creator = VideoCreator(self.config)
        
        mock_exists.return_value = True
        
        # Mock image clips
        mock_clip1 = Mock()
        mock_clip2 = Mock()
        mock_image_clip.side_effect = [mock_clip1, mock_clip2]
        
        # Mock resize method
        mock_resized1 = Mock()
        mock_resized2 = Mock()
        creator._resize_and_fit_image = Mock(side_effect=[mock_resized1, mock_resized2])
        
        # Mock duration setting and transitions
        mock_resized1.set_duration.return_value = mock_resized1
        mock_resized2.set_duration.return_value = mock_resized2
        mock_resized1.fadeout.return_value = mock_resized1
        mock_resized2.fadein.return_value = mock_resized2
        
        # Mock concatenation
        mock_final = Mock()
        mock_final.duration = 30.0
        mock_concat.return_value = mock_final
        
        images = [
            {'local_path': 'image1.jpg'},
            {'local_path': 'image2.jpg'}
        ]
        
        result = creator._create_image_slideshow(images, 30.0)
        
        self.assertEqual(result, mock_final)
        
        # Check that images were processed
        self.assertEqual(mock_image_clip.call_count, 2)
        mock_image_clip.assert_any_call('image1.jpg')
        mock_image_clip.assert_any_call('image2.jpg')
        
        # Check duration setting (15 seconds per image for 30-second total)
        mock_resized1.set_duration.assert_called_with(15.0)
        mock_resized2.set_duration.assert_called_with(15.0)
        
        # Check transitions (first has fadeout, second has fadein)
        mock_resized1.fadeout.assert_called_once()
        mock_resized2.fadein.assert_called_once()
        
        mock_concat.assert_called_once()
    
    @patch('video_creator.ImageClip')
    @patch('os.path.exists')
    def test_create_image_slideshow_missing_image(self, mock_exists, mock_image_clip):
        """Test image slideshow creation with missing image"""
        creator = VideoCreator(self.config)
        
        # First image exists, second doesn't
        mock_exists.side_effect = [True, False]
        
        mock_clip = Mock()
        mock_image_clip.return_value = mock_clip
        
        # Mock resize and other methods
        creator._resize_and_fit_image = Mock(return_value=mock_clip)
        mock_clip.set_duration.return_value = mock_clip
        mock_clip.fadeout.return_value = mock_clip
        
        with patch('video_creator.concatenate_videoclips') as mock_concat:
            mock_final = Mock()
            mock_final.duration = 30.0
            mock_concat.return_value = mock_final
            
            with patch('builtins.print') as mock_print:
                images = [
                    {'local_path': 'image1.jpg'},
                    {'local_path': 'missing.jpg'}
                ]
                
                result = creator._create_image_slideshow(images, 30.0)
                
                # Should print warning for missing image
                mock_print.assert_called()
                warning_calls = [call for call in mock_print.call_args_list 
                               if 'Warning' in str(call)]
                self.assertTrue(len(warning_calls) > 0)
                
                # Should still create slideshow with available images
                self.assertEqual(mock_image_clip.call_count, 1)  # Only first image processed
    
    @patch('os.path.exists')
    def test_create_image_slideshow_no_valid_images(self, mock_exists):
        """Test image slideshow creation with no valid images"""
        creator = VideoCreator(self.config)
        
        mock_exists.return_value = False  # All images missing
        
        images = [{'local_path': 'missing1.jpg'}, {'local_path': 'missing2.jpg'}]
        
        with self.assertRaises(RuntimeError) as context:
            creator._create_image_slideshow(images, 30.0)
        
        self.assertIn("No valid images found", str(context.exception))
    
    @patch('video_creator.ImageClip')
    @patch('video_creator.concatenate_videoclips')
    @patch('os.path.exists')
    def test_create_image_slideshow_duration_adjustment(self, mock_exists, mock_concat, mock_image_clip):
        """Test image slideshow duration adjustment"""
        creator = VideoCreator(self.config)
        
        mock_exists.return_value = True
        mock_clip = Mock()
        mock_image_clip.return_value = mock_clip
        creator._resize_and_fit_image = Mock(return_value=mock_clip)
        mock_clip.set_duration.return_value = mock_clip
        
        # Test duration too long
        mock_final = Mock()
        mock_final.duration = 35.0  # Longer than target 30s
        mock_concat.return_value = mock_final
        
        mock_subclip = Mock()
        mock_final.subclip.return_value = mock_subclip
        
        images = [{'local_path': 'image1.jpg'}]
        
        result = creator._create_image_slideshow(images, 30.0)
        
        # Should trim to exact duration
        mock_final.subclip.assert_called_once_with(0, 30.0)
        self.assertEqual(result, mock_subclip)
    
    @patch('video_creator.ImageClip')
    @patch('video_creator.concatenate_videoclips')
    @patch('os.path.exists')
    def test_create_image_slideshow_duration_extension(self, mock_exists, mock_concat, mock_image_clip):
        """Test image slideshow duration extension"""
        creator = VideoCreator(self.config)
        
        mock_exists.return_value = True
        mock_clip = Mock()
        mock_image_clip.return_value = mock_clip
        creator._resize_and_fit_image = Mock(return_value=mock_clip)
        mock_clip.set_duration.return_value = mock_clip
        
        # Test duration too short
        mock_final = Mock()
        mock_final.duration = 25.0  # Shorter than target 30s
        mock_concat.return_value = mock_final
        
        # Mock extension creation
        mock_image_clip_from_last = Mock()
        mock_clip.to_ImageClip.return_value = mock_image_clip_from_last
        mock_extension = Mock()
        mock_image_clip_from_last.set_duration.return_value = mock_extension
        
        mock_extended = Mock()
        mock_concat.side_effect = [mock_final, mock_extended]  # First call returns short clip, second returns extended
        
        images = [{'local_path': 'image1.jpg'}]
        
        result = creator._create_image_slideshow(images, 30.0)
        
        # Should extend with static last frame
        mock_image_clip_from_last.set_duration.assert_called_once_with(5.0)  # 30 - 25 = 5 seconds
        self.assertEqual(mock_concat.call_count, 2)
        self.assertEqual(result, mock_extended)
    
    @patch('video_creator.ColorClip')
    @patch('video_creator.CompositeVideoClip')
    def test_resize_and_fit_image_with_background(self, mock_composite, mock_color_clip):
        """Test image resizing with background when image doesn't fill frame"""
        creator = VideoCreator(self.config)
        
        # Mock image that's smaller after scaling
        mock_image = Mock()
        mock_image.size = (800, 600)  # 4:3 aspect ratio, will have black bars on 16:9 video
        
        mock_resized = Mock()
        mock_image.resize.return_value = mock_resized
        
        mock_background = Mock()
        mock_color_clip.return_value = mock_background
        
        mock_positioned = Mock()
        mock_resized.set_position.return_value = mock_positioned
        
        mock_final = Mock()
        mock_composite.return_value = mock_final
        
        result = creator._resize_and_fit_image(mock_image)
        
        # Check scaling calculation (should scale to fit height: 1080/600 = 1.8)
        expected_new_size = (1440, 1080)  # 800*1.8, 600*1.8
        mock_image.resize.assert_called_once_with(expected_new_size)
        
        # Should create background
        mock_color_clip.assert_called_once_with(size=(1920, 1080), color=(0, 0, 0))
        
        # Should center image (offset = (1920-1440)/2 = 240 horizontally, 0 vertically)
        mock_resized.set_position.assert_called_once_with((240, 0))
        
        # Should composite
        mock_composite.assert_called_once_with([mock_background, mock_positioned])
        
        self.assertEqual(result, mock_final)
    
    def test_resize_and_fit_image_exact_fit(self):
        """Test image resizing when image fits exactly"""
        creator = VideoCreator(self.config)
        
        # Mock image that fits exactly after scaling
        mock_image = Mock()
        mock_image.size = (1920, 1080)  # Exact video size
        
        mock_resized = Mock()
        mock_image.resize.return_value = mock_resized
        
        result = creator._resize_and_fit_image(mock_image)
        
        # Should just resize without background
        mock_image.resize.assert_called_once_with((1920, 1080))
        self.assertEqual(result, mock_resized)
    
    @patch('video_creator.os.path.exists')
    @patch('video_creator.os.path.getsize')
    def test_render_video_success(self, mock_getsize, mock_exists):
        """Test successful video rendering"""
        creator = VideoCreator(self.config)
        
        mock_clip = Mock()
        mock_exists.return_value = True
        mock_getsize.return_value = 5000000  # 5MB file
        
        output_path = "/tmp/test_output/test.mp4"
        
        creator._render_video(mock_clip, output_path)
        
        # Check that write_videofile was called with correct parameters
        mock_clip.write_videofile.assert_called_once()
        call_args = mock_clip.write_videofile.call_args
        
        self.assertEqual(call_args[0][0], output_path)  # First positional arg is output path
        
        # Check codec parameters
        kwargs = call_args[1]
        self.assertEqual(kwargs['codec'], 'libx264')
        self.assertEqual(kwargs['audio_codec'], 'aac')
        self.assertEqual(kwargs['fps'], 30)
        self.assertEqual(kwargs['bitrate'], '2000k')
        self.assertEqual(kwargs['audio_bitrate'], '128k')
    
    @patch('video_creator.os.path.exists')
    def test_render_video_file_not_created(self, mock_exists):
        """Test video rendering when file is not created"""
        creator = VideoCreator(self.config)
        
        mock_clip = Mock()
        mock_exists.return_value = False  # File not created
        
        with self.assertRaises(RuntimeError) as context:
            creator._render_video(mock_clip, "/tmp/test.mp4")
        
        self.assertIn("Video file was not created", str(context.exception))
    
    @patch('video_creator.os.path.exists')
    @patch('video_creator.os.path.getsize')
    def test_render_video_corrupted(self, mock_getsize, mock_exists):
        """Test video rendering when file is corrupted"""
        creator = VideoCreator(self.config)
        
        mock_clip = Mock()
        mock_exists.return_value = True
        mock_getsize.return_value = 500  # Too small, indicates corruption
        
        with self.assertRaises(RuntimeError) as context:
            creator._render_video(mock_clip, "/tmp/test.mp4")
        
        self.assertIn("Video file appears to be corrupted", str(context.exception))
    
    @patch('video_creator.os.path.exists')
    @patch('video_creator.os.remove')
    def test_render_video_cleanup_on_error(self, mock_remove, mock_exists):
        """Test video rendering cleanup on error"""
        creator = VideoCreator(self.config)
        
        mock_clip = Mock()
        mock_clip.write_videofile.side_effect = Exception("Render error")
        mock_exists.return_value = True  # Partial file exists
        
        output_path = "/tmp/test.mp4"
        
        with self.assertRaises(RuntimeError):
            creator._render_video(mock_clip, output_path)
        
        # Should attempt to remove partial file
        mock_remove.assert_called_once_with(output_path)
    
    def test_handle_video_error_codec(self):
        """Test video error handling for codec issues"""
        creator = VideoCreator(self.config)
        
        with self.assertRaises(RuntimeError) as context:
            creator._handle_video_error(Exception("Codec not found"))
        
        self.assertIn("Video codec error", str(context.exception))
    
    def test_handle_video_error_memory(self):
        """Test video error handling for memory issues"""
        creator = VideoCreator(self.config)
        
        with self.assertRaises(RuntimeError) as context:
            creator._handle_video_error(Exception("Out of memory"))
        
        self.assertIn("Insufficient memory", str(context.exception))
    
    def test_handle_video_error_permission(self):
        """Test video error handling for permission issues"""
        creator = VideoCreator(self.config)
        
        with self.assertRaises(RuntimeError) as context:
            creator._handle_video_error(Exception("Permission denied"))
        
        self.assertIn("Permission denied", str(context.exception))
    
    def test_handle_video_error_disk_space(self):
        """Test video error handling for disk space issues"""
        creator = VideoCreator(self.config)
        
        with self.assertRaises(RuntimeError) as context:
            creator._handle_video_error(Exception("No space left on disk"))
        
        self.assertIn("Insufficient disk space", str(context.exception))
    
    def test_handle_video_error_generic(self):
        """Test video error handling for generic errors"""
        creator = VideoCreator(self.config)
        
        with self.assertRaises(RuntimeError) as context:
            creator._handle_video_error(Exception("Unknown error"))
        
        self.assertIn("Video creation failed", str(context.exception))
    
    @patch('video_creator.VideoFileClip')
    @patch('video_creator.os.path.exists')
    @patch('video_creator.os.path.getsize')
    def test_get_video_info_success(self, mock_getsize, mock_exists, mock_video_clip):
        """Test successful video info retrieval"""
        creator = VideoCreator(self.config)
        
        mock_exists.return_value = True
        mock_getsize.return_value = 5000000
        
        mock_clip = Mock()
        mock_clip.duration = 30.0
        mock_clip.fps = 30
        mock_clip.size = (1920, 1080)
        mock_clip.audio = Mock()  # Has audio
        mock_video_clip.return_value = mock_clip
        
        result = creator.get_video_info("/path/to/video.mp4")
        
        expected = {
            'duration': 30.0,
            'fps': 30,
            'size': (1920, 1080),
            'file_size': 5000000,
            'has_audio': True
        }
        
        self.assertEqual(result, expected)
        mock_clip.close.assert_called_once()
    
    @patch('video_creator.os.path.exists')
    def test_get_video_info_file_not_found(self, mock_exists):
        """Test video info retrieval with non-existent file"""
        creator = VideoCreator(self.config)
        
        mock_exists.return_value = False
        
        result = creator.get_video_info("/path/to/nonexistent.mp4")
        
        self.assertIsNone(result)
    
    @patch('video_creator.VideoFileClip')
    @patch('video_creator.os.path.exists')
    def test_get_video_info_error(self, mock_exists, mock_video_clip):
        """Test video info retrieval with error"""
        creator = VideoCreator(self.config)
        
        mock_exists.return_value = True
        mock_video_clip.side_effect = Exception("Cannot read video")
        
        with patch('builtins.print') as mock_print:
            result = creator.get_video_info("/path/to/video.mp4")
            
            self.assertIsNone(result)
            mock_print.assert_called()  # Should print warning
    
    @patch('video_creator.os.path.exists')
    @patch('video_creator.os.remove')
    @patch('video_creator.os.listdir')
    def test_cleanup_temp_files(self, mock_listdir, mock_remove, mock_exists):
        """Test cleanup of temporary files"""
        creator = VideoCreator(self.config)
        
        # Mock files in current directory
        mock_listdir.return_value = [
            'temp-audio.m4a',
            'temp-audio.wav',
            'TEMP_MPY_wvfqtABC.avi',
            'normal_file.txt'  # Should be ignored
        ]
        
        mock_exists.side_effect = [True, True, True, False]  # First 3 exist, last doesn't
        
        creator.cleanup_temp_files()
        
        # Should remove temp files
        expected_calls = [
            unittest.mock.call('temp-audio.m4a'),
            unittest.mock.call('temp-audio.wav'),
            unittest.mock.call('TEMP_MPY_wvfqtABC.avi')
        ]
        
        mock_remove.assert_has_calls(expected_calls, any_order=True)
        self.assertEqual(mock_remove.call_count, 3)


class TestCreateVideoCreator(unittest.TestCase):
    """Test cases for create_video_creator factory function"""
    
    @patch('video_creator.Config')
    def test_create_video_creator(self, mock_config_class):
        """Test factory function creates VideoCreator instance"""
        from video_creator import create_video_creator
        
        mock_config = Mock()
        mock_config_class.return_value = mock_config
        
        creator = create_video_creator()
        
        self.assertIsInstance(creator, VideoCreator)
        mock_config_class.assert_called_once()


if __name__ == '__main__':
    unittest.main()