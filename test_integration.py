import unittest
from unittest.mock import Mock, patch, MagicMock
import os
import tempfile
import time
from main import VideoWorkflow, CLIInterface
from config import Config


class TestVideoWorkflow(unittest.TestCase):
    """Test cases for VideoWorkflow class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = Mock(spec=Config)
        self.config.max_images = 5
        
        # Mock components
        self.mock_script_gen = Mock()
        self.mock_image_fetcher = Mock()
        self.mock_voice_gen = Mock()
        self.mock_video_creator = Mock()
    
    @patch('main.VideoCreator')
    @patch('main.VoiceGenerator')
    @patch('main.ImageFetcher')
    @patch('main.ScriptGenerator')
    def test_init_success(self, mock_script_class, mock_image_class, mock_voice_class, mock_video_class):
        """Test successful VideoWorkflow initialization"""
        # Mock constructor returns
        mock_script_class.return_value = self.mock_script_gen
        mock_image_class.return_value = self.mock_image_fetcher
        mock_voice_class.return_value = self.mock_voice_gen
        mock_video_class.return_value = self.mock_video_creator
        
        workflow = VideoWorkflow(self.config)
        
        self.assertEqual(workflow.config, self.config)
        self.assertEqual(workflow.script_generator, self.mock_script_gen)
        self.assertEqual(workflow.image_fetcher, self.mock_image_fetcher)
        self.assertEqual(workflow.voice_generator, self.mock_voice_gen)
        self.assertEqual(workflow.video_creator, self.mock_video_creator)
    
    @patch('main.ScriptGenerator')
    def test_init_component_failure(self, mock_script_class):
        """Test VideoWorkflow initialization with component failure"""
        mock_script_class.side_effect = Exception("Component initialization failed")
        
        with self.assertRaises(RuntimeError) as context:
            VideoWorkflow(self.config)
        
        self.assertIn("コンポーネントの初期化に失敗しました", str(context.exception))
    
    def test_init_default_config(self):
        """Test VideoWorkflow initialization with default config"""
        with patch('main.Config') as mock_config_class, \
             patch('main.ScriptGenerator'), \
             patch('main.ImageFetcher'), \
             patch('main.VoiceGenerator'), \
             patch('main.VideoCreator'):
            
            mock_config = Mock()
            mock_config_class.return_value = mock_config
            
            workflow = VideoWorkflow()
            
            self.assertEqual(workflow.config, mock_config)
            mock_config_class.assert_called_once()
    
    def test_set_progress_callback(self):
        """Test setting progress callback"""
        with patch('main.ScriptGenerator'), \
             patch('main.ImageFetcher'), \
             patch('main.VoiceGenerator'), \
             patch('main.VideoCreator'):
            
            workflow = VideoWorkflow(self.config)
            callback = Mock()
            
            workflow.set_progress_callback(callback)
            
            self.assertEqual(workflow.progress_callback, callback)
    
    def test_update_progress_with_callback(self):
        """Test progress update with callback"""
        with patch('main.ScriptGenerator'), \
             patch('main.ImageFetcher'), \
             patch('main.VoiceGenerator'), \
             patch('main.VideoCreator'):
            
            workflow = VideoWorkflow(self.config)
            callback = Mock()
            workflow.set_progress_callback(callback)
            
            workflow._update_progress("test_step", 50, "test message")
            
            callback.assert_called_once_with("test_step", 50, "test message")
    
    def test_update_progress_without_callback(self):
        """Test progress update without callback"""
        with patch('main.ScriptGenerator'), \
             patch('main.ImageFetcher'), \
             patch('main.VoiceGenerator'), \
             patch('main.VideoCreator'):
            
            workflow = VideoWorkflow(self.config)
            
            with patch('builtins.print') as mock_print:
                workflow._update_progress("test_step", 50, "test message")
                
                mock_print.assert_called_once_with("[ 50%] test_step: test message")
    
    def test_generate_video_empty_theme(self):
        """Test video generation with empty theme"""
        with patch('main.ScriptGenerator'), \
             patch('main.ImageFetcher'), \
             patch('main.VoiceGenerator'), \
             patch('main.VideoCreator'):
            
            workflow = VideoWorkflow(self.config)
            
            with self.assertRaises(ValueError) as context:
                workflow.generate_video("")
            
            self.assertIn("テーマが指定されていません", str(context.exception))
    
    @patch('main.VideoCreator')
    @patch('main.VoiceGenerator')
    @patch('main.ImageFetcher')
    @patch('main.ScriptGenerator')
    @patch('time.time')
    @patch('main.datetime')
    @patch('os.path.basename')
    def test_generate_video_success(self, mock_basename, mock_datetime, mock_time, 
                                   mock_script_class, mock_image_class, mock_voice_class, mock_video_class):
        """Test successful video generation"""
        # Setup mocks
        mock_time.side_effect = [1000, 1030]  # Start and end times
        mock_datetime.now.return_value.strftime.return_value = "20231201_120000"
        mock_basename.return_value = "test_video.mp4"
        
        # Mock component returns
        mock_script_gen = Mock()
        mock_image_fetcher = Mock()
        mock_voice_gen = Mock()
        mock_video_creator = Mock()
        
        mock_script_class.return_value = mock_script_gen
        mock_image_class.return_value = mock_image_fetcher
        mock_voice_class.return_value = mock_voice_gen
        mock_video_class.return_value = mock_video_creator
        
        # Mock component methods
        script_data = {
            'title': 'Test Title',
            'script': 'Test script',
            'keywords': 'test, keywords'
        }
        mock_script_gen.generate_script.return_value = script_data
        
        images = [{'local_path': 'image1.jpg'}, {'local_path': 'image2.jpg'}]
        mock_image_fetcher.fetch_images.return_value = images
        
        audio_path = '/tmp/audio.wav'
        mock_voice_gen.generate_voice.return_value = audio_path
        
        video_path = '/tmp/video.mp4'
        mock_video_creator.create_video.return_value = video_path
        
        video_info = {'duration': 30.0, 'size': (1920, 1080), 'file_size': 5000000}
        mock_video_creator.get_video_info.return_value = video_info
        
        # Mock config validation
        self.config.validate.return_value = True
        
        workflow = VideoWorkflow(self.config)
        
        # Execute
        result = workflow.generate_video("test theme")
        
        # Verify
        self.assertTrue(result['success'])
        self.assertEqual(result['theme'], "test theme")
        self.assertEqual(result['output_path'], video_path)
        self.assertEqual(result['duration'], 30)  # 1030 - 1000
        self.assertEqual(result['video_info'], video_info)
        
        # Verify component calls
        mock_script_gen.generate_script.assert_called_once_with("test theme")
        mock_image_fetcher.fetch_images.assert_called_once_with('test, keywords', self.config.max_images)
        mock_voice_gen.generate_voice.assert_called_once_with('Test script')
        mock_video_creator.create_video.assert_called_once_with(images, audio_path, "test theme_20231201_120000.mp4")
    
    @patch('main.VideoCreator')
    @patch('main.VoiceGenerator')
    @patch('main.ImageFetcher')
    @patch('main.ScriptGenerator')
    @patch('time.time')
    def test_generate_video_with_custom_filename(self, mock_time, mock_script_class, 
                                                mock_image_class, mock_voice_class, mock_video_class):
        """Test video generation with custom filename"""
        # Setup mocks similar to previous test
        mock_time.side_effect = [1000, 1030]
        
        mock_script_gen = Mock()
        mock_image_fetcher = Mock()
        mock_voice_gen = Mock()
        mock_video_creator = Mock()
        
        mock_script_class.return_value = mock_script_gen
        mock_image_class.return_value = mock_image_fetcher
        mock_voice_class.return_value = mock_voice_gen
        mock_video_class.return_value = mock_video_creator
        
        # Mock returns
        script_data = {'title': 'Test', 'script': 'Test', 'keywords': 'test'}
        mock_script_gen.generate_script.return_value = script_data
        mock_image_fetcher.fetch_images.return_value = [{'local_path': 'image.jpg'}]
        mock_voice_gen.generate_voice.return_value = '/tmp/audio.wav'
        mock_video_creator.create_video.return_value = '/tmp/custom.mp4'
        mock_video_creator.get_video_info.return_value = {}
        
        self.config.validate.return_value = True
        
        workflow = VideoWorkflow(self.config)
        
        # Execute with custom filename
        result = workflow.generate_video("test theme", "custom_video.mp4")
        
        # Verify custom filename was used
        mock_video_creator.create_video.assert_called_once()
        args = mock_video_creator.create_video.call_args[0]
        self.assertEqual(args[2], "custom_video.mp4")  # Third argument is output filename
    
    @patch('main.VideoCreator')
    @patch('main.VoiceGenerator')
    @patch('main.ImageFetcher')
    @patch('main.ScriptGenerator')
    @patch('time.time')
    def test_generate_video_script_error(self, mock_time, mock_script_class, 
                                        mock_image_class, mock_voice_class, mock_video_class):
        """Test video generation with script generation error"""
        mock_time.side_effect = [1000, 1010]
        
        mock_script_gen = Mock()
        mock_script_gen.generate_script.side_effect = Exception("Script generation failed")
        mock_script_class.return_value = mock_script_gen
        
        mock_image_class.return_value = Mock()
        mock_voice_class.return_value = Mock()
        mock_video_class.return_value = Mock()
        
        self.config.validate.return_value = True
        
        workflow = VideoWorkflow(self.config)
        
        with self.assertRaises(RuntimeError) as context:
            workflow.generate_video("test theme")
        
        self.assertIn("動画生成中にエラーが発生しました", str(context.exception))
    
    @patch('main.VideoCreator')
    @patch('main.VoiceGenerator')
    @patch('main.ImageFetcher')
    @patch('main.ScriptGenerator')
    def test_cleanup_temp_files(self, mock_script_class, mock_image_class, mock_voice_class, mock_video_class):
        """Test temporary files cleanup"""
        mock_script_gen = Mock()
        mock_image_fetcher = Mock()
        mock_voice_gen = Mock()
        mock_video_creator = Mock()
        
        mock_script_class.return_value = mock_script_gen
        mock_image_class.return_value = mock_image_fetcher
        mock_voice_class.return_value = mock_voice_gen
        mock_video_class.return_value = mock_video_creator
        
        workflow = VideoWorkflow(self.config)
        
        workflow._cleanup_temp_files()
        
        mock_image_fetcher.cleanup_temp_images.assert_called_once()
        mock_voice_gen.cleanup_temp_audio.assert_called_once()
        mock_video_creator.cleanup_temp_files.assert_called_once()
    
    @patch('main.VideoCreator')
    @patch('main.VoiceGenerator')
    @patch('main.ImageFetcher')
    @patch('main.ScriptGenerator')
    def test_cleanup_temp_files_error(self, mock_script_class, mock_image_class, mock_voice_class, mock_video_class):
        """Test temporary files cleanup with error"""
        mock_script_gen = Mock()
        mock_image_fetcher = Mock()
        mock_voice_gen = Mock()
        mock_video_creator = Mock()
        
        mock_script_class.return_value = mock_script_gen
        mock_image_class.return_value = mock_image_fetcher
        mock_voice_class.return_value = mock_voice_gen
        mock_video_class.return_value = mock_video_creator
        
        # Mock cleanup error
        mock_image_fetcher.cleanup_temp_images.side_effect = Exception("Cleanup failed")
        
        workflow = VideoWorkflow(self.config)
        
        with patch('builtins.print') as mock_print:
            workflow._cleanup_temp_files()
            
            # Should print warning but not raise exception
            mock_print.assert_called()
            warning_calls = [call for call in mock_print.call_args_list 
                           if 'warning' in str(call).lower() or '警告' in str(call)]
            self.assertTrue(len(warning_calls) > 0)


class TestCLIInterface(unittest.TestCase):
    """Test cases for CLIInterface class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.cli = CLIInterface()
    
    @patch('main.argparse.ArgumentParser.parse_args')
    def test_parse_arguments(self, mock_parse_args):
        """Test command line argument parsing"""
        mock_args = Mock()
        mock_args.theme = "test theme"
        mock_args.output = "test.mp4"
        mock_args.test_config = False
        mock_parse_args.return_value = mock_args
        
        result = self.cli._parse_arguments()
        
        self.assertEqual(result, mock_args)
    
    def test_progress_callback(self):
        """Test progress callback function"""
        with patch('builtins.print') as mock_print:
            self.cli._progress_callback("Test Step", 50, "Test message")
            
            # Should print progress bar
            mock_print.assert_called()
            call_args = mock_print.call_args[0][0]
            self.assertIn("Test Step", call_args)
            self.assertIn("50%", call_args)
            self.assertIn("Test message", call_args)
    
    def test_progress_callback_completion(self):
        """Test progress callback at 100%"""
        with patch('builtins.print') as mock_print:
            self.cli._progress_callback("Complete", 100, "Done")
            
            # Should print progress bar and newline
            self.assertEqual(mock_print.call_count, 2)  # Progress + newline
    
    def test_print_banner(self):
        """Test banner printing"""
        with patch('builtins.print') as mock_print:
            self.cli._print_banner()
            
            # Should print multiple lines
            self.assertTrue(mock_print.call_count > 3)
            
            # Check for banner content
            all_calls = ' '.join(str(call) for call in mock_print.call_args_list)
            self.assertIn("AI自動動画生成システム", all_calls)
    
    def test_print_result_success(self):
        """Test printing successful result"""
        result = {
            'success': True,
            'output_path': '/tmp/test_video.mp4',
            'video_info': {
                'duration': 30.0,
                'size': (1920, 1080),
                'file_size': 5000000
            },
            'duration': 45.5
        }
        
        with patch('builtins.print') as mock_print:
            self.cli._print_result(result)
            
            all_calls = ' '.join(str(call) for call in mock_print.call_args_list)
            self.assertIn("動画生成完了", all_calls)
            self.assertIn("/tmp/test_video.mp4", all_calls)
            self.assertIn("30.0秒", all_calls)
            self.assertIn("1920x1080", all_calls)
            self.assertIn("45.5秒", all_calls)
    
    def test_print_result_failure(self):
        """Test printing failed result"""
        result = {
            'success': False,
            'errors': ['Error 1', 'Error 2']
        }
        
        with patch('builtins.print') as mock_print:
            self.cli._print_result(result)
            
            all_calls = ' '.join(str(call) for call in mock_print.call_args_list)
            self.assertIn("動画生成に失敗", all_calls)
            self.assertIn("Error 1", all_calls)
            self.assertIn("Error 2", all_calls)
    
    @patch('main.Config')
    @patch('main.VoiceGenerator')
    def test_test_configuration_success(self, mock_voice_class, mock_config_class):
        """Test configuration testing success"""
        mock_config = Mock()
        mock_config.validate.return_value = True
        mock_config_class.return_value = mock_config
        
        mock_voice_gen = Mock()
        mock_voice_gen.test_connection.return_value = True
        mock_voice_class.return_value = mock_voice_gen
        
        with patch('builtins.print') as mock_print:
            self.cli._test_configuration()
            
            all_calls = ' '.join(str(call) for call in mock_print.call_args_list)
            self.assertIn("基本設定: OK", all_calls)
            self.assertIn("VOICEVOX接続: OK", all_calls)
    
    @patch('main.Config')
    def test_test_configuration_failure(self, mock_config_class):
        """Test configuration testing failure"""
        mock_config = Mock()
        mock_config.validate.side_effect = Exception("Config error")
        mock_config_class.return_value = mock_config
        
        with patch('builtins.print') as mock_print, \
             patch('sys.exit') as mock_exit:
            
            self.cli._test_configuration()
            
            all_calls = ' '.join(str(call) for call in mock_print.call_args_list)
            self.assertIn("設定エラー", all_calls)
            mock_exit.assert_called_once_with(1)
    
    @patch('main.VideoWorkflow')
    @patch('main.Config')
    @patch('main.argparse.ArgumentParser.parse_args')
    def test_run_with_args_theme(self, mock_parse_args, mock_config_class, mock_workflow_class):
        """Test running with theme argument"""
        # Mock arguments
        mock_args = Mock()
        mock_args.theme = "test theme"
        mock_args.output = "test.mp4"
        mock_args.test_config = False
        mock_parse_args.return_value = mock_args
        
        # Mock config and workflow
        mock_config = Mock()
        mock_config_class.return_value = mock_config
        
        mock_workflow = Mock()
        mock_workflow.generate_video.return_value = {'success': True}
        mock_workflow_class.return_value = mock_workflow
        
        with patch.object(self.cli, '_print_banner'), \
             patch.object(self.cli, '_print_result'), \
             patch('builtins.print'):
            
            self.cli.run()
            
            mock_workflow.generate_video.assert_called_once_with("test theme", "test.mp4")
    
    @patch('main.VideoWorkflow')
    @patch('main.Config')
    @patch('main.argparse.ArgumentParser.parse_args')
    def test_run_with_test_config(self, mock_parse_args, mock_config_class, mock_workflow_class):
        """Test running with test config flag"""
        # Mock arguments
        mock_args = Mock()
        mock_args.theme = None
        mock_args.test_config = True
        mock_parse_args.return_value = mock_args
        
        mock_config_class.return_value = Mock()
        mock_workflow_class.return_value = Mock()
        
        with patch.object(self.cli, '_print_banner'), \
             patch.object(self.cli, '_test_configuration') as mock_test_config:
            
            self.cli.run()
            
            mock_test_config.assert_called_once()
    
    @patch('main.VideoWorkflow')
    @patch('main.Config')
    @patch('main.argparse.ArgumentParser.parse_args')
    @patch('builtins.input')
    def test_run_interactive_mode_quit(self, mock_input, mock_parse_args, mock_config_class, mock_workflow_class):
        """Test interactive mode with quit command"""
        # Mock arguments for interactive mode
        mock_args = Mock()
        mock_args.theme = None
        mock_args.test_config = False
        mock_parse_args.return_value = mock_args
        
        # Mock config validation success
        mock_config = Mock()
        mock_config.validate.return_value = True
        mock_config_class.return_value = mock_config
        
        mock_workflow = Mock()
        mock_workflow_class.return_value = mock_workflow
        
        # Mock user input: quit immediately
        mock_input.return_value = "quit"
        
        with patch.object(self.cli, '_print_banner'), \
             patch('builtins.print') as mock_print:
            
            self.cli.run()
            
            # Should have prompted for theme
            mock_input.assert_called()
            
            # Should print quit message
            all_calls = ' '.join(str(call) for call in mock_print.call_args_list)
            self.assertIn("終了します", all_calls)
    
    @patch('main.VideoWorkflow')
    @patch('main.Config')
    @patch('main.argparse.ArgumentParser.parse_args')
    def test_run_keyboard_interrupt(self, mock_parse_args, mock_config_class, mock_workflow_class):
        """Test handling keyboard interrupt"""
        mock_args = Mock()
        mock_args.theme = None
        mock_args.test_config = False
        mock_parse_args.return_value = mock_args
        
        mock_config_class.side_effect = KeyboardInterrupt()
        
        with patch('builtins.print') as mock_print, \
             patch('sys.exit') as mock_exit, \
             patch.object(self.cli, '_print_banner'):
            
            self.cli.run()
            
            mock_exit.assert_called_once_with(1)
            all_calls = ' '.join(str(call) for call in mock_print.call_args_list)
            self.assertIn("処理が中断されました", all_calls)
    
    @patch('main.VideoWorkflow')
    @patch('main.Config')
    @patch('main.argparse.ArgumentParser.parse_args')
    def test_run_general_error(self, mock_parse_args, mock_config_class, mock_workflow_class):
        """Test handling general error"""
        mock_args = Mock()
        mock_args.theme = None
        mock_args.test_config = False
        mock_parse_args.return_value = mock_args
        
        mock_config_class.side_effect = Exception("General error")
        
        with patch('builtins.print') as mock_print, \
             patch('sys.exit') as mock_exit, \
             patch.object(self.cli, '_print_banner'):
            
            self.cli.run()
            
            mock_exit.assert_called_once_with(1)
            all_calls = ' '.join(str(call) for call in mock_print.call_args_list)
            self.assertIn("エラー: General error", all_calls)


class TestMainFunction(unittest.TestCase):
    """Test cases for main function"""
    
    @patch('main.CLIInterface')
    def test_main(self, mock_cli_class):
        """Test main function"""
        from main import main
        
        mock_cli = Mock()
        mock_cli_class.return_value = mock_cli
        
        main()
        
        mock_cli_class.assert_called_once()
        mock_cli.run.assert_called_once()


if __name__ == '__main__':
    unittest.main()