import unittest
from unittest.mock import Mock, patch, MagicMock
import json
from script_generator import ScriptGenerator
from config import Config


class TestScriptGenerator(unittest.TestCase):
    """Test cases for ScriptGenerator class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = Mock(spec=Config)
        self.config.gemini_api_key = "test_api_key"
        
    @patch('script_generator.genai')
    def test_initialize_client_success(self, mock_genai):
        """Test successful client initialization"""
        mock_model = Mock()
        mock_genai.GenerativeModel.return_value = mock_model
        
        generator = ScriptGenerator(self.config)
        
        mock_genai.configure.assert_called_once_with(api_key="test_api_key")
        mock_genai.GenerativeModel.assert_called_once_with('gemini-1.5-flash')
        self.assertEqual(generator.client, mock_model)
    
    @patch('script_generator.genai')
    def test_initialize_client_failure(self, mock_genai):
        """Test client initialization failure"""
        mock_genai.configure.side_effect = Exception("API error")
        
        with self.assertRaises(RuntimeError) as context:
            ScriptGenerator(self.config)
        
        self.assertIn("Failed to initialize Gemini client", str(context.exception))
    
    def test_validate_theme_input_valid(self):
        """Test theme validation with valid inputs"""
        with patch('script_generator.genai'):
            generator = ScriptGenerator(self.config)
            
            # Valid themes
            self.assertTrue(generator.validate_theme_input("AI"))
            self.assertTrue(generator.validate_theme_input("人工知能"))
            self.assertTrue(generator.validate_theme_input("Technology and Future"))
    
    def test_validate_theme_input_invalid(self):
        """Test theme validation with invalid inputs"""
        with patch('script_generator.genai'):
            generator = ScriptGenerator(self.config)
            
            # Invalid themes
            self.assertFalse(generator.validate_theme_input(""))
            self.assertFalse(generator.validate_theme_input("   "))
            self.assertFalse(generator.validate_theme_input("a"))
            self.assertFalse(generator.validate_theme_input("a" * 101))  # Too long
            self.assertFalse(generator.validate_theme_input(None))
            self.assertFalse(generator.validate_theme_input(123))
    
    @patch('script_generator.genai')
    def test_generate_script_empty_theme(self, mock_genai):
        """Test script generation with empty theme"""
        generator = ScriptGenerator(self.config)
        
        with self.assertRaises(ValueError) as context:
            generator.generate_script("")
        
        self.assertIn("Theme cannot be empty", str(context.exception))
    
    @patch('script_generator.genai')
    def test_generate_script_success(self, mock_genai):
        """Test successful script generation"""
        mock_response = Mock()
        mock_response.text = '''
        {
            "title": "AIの未来",
            "script": "人工知能は私たちの生活を大きく変えています。今後もさらなる発展が期待されます。",
            "keywords": "AI, 人工知能, 技術, 未来"
        }
        '''
        
        mock_client = Mock()
        mock_client.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_client
        
        generator = ScriptGenerator(self.config)
        result = generator.generate_script("人工知能")
        
        self.assertEqual(result['title'], "AIの未来")
        self.assertIn("人工知能", result['script'])
        self.assertEqual(result['keywords'], "AI, 人工知能, 技術, 未来")
    
    @patch('script_generator.genai')
    def test_generate_script_empty_response(self, mock_genai):
        """Test script generation with empty API response"""
        mock_response = Mock()
        mock_response.text = ""
        
        mock_client = Mock()
        mock_client.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_client
        
        generator = ScriptGenerator(self.config)
        
        with self.assertRaises(RuntimeError) as context:
            generator.generate_script("test theme")
        
        self.assertIn("Empty response from Gemini API", str(context.exception))
    
    def test_parse_and_validate_response_valid_json(self):
        """Test parsing valid JSON response"""
        with patch('script_generator.genai'):
            generator = ScriptGenerator(self.config)
            
            response_text = '''
            {
                "title": "Test Title",
                "script": "This is a test script for validation.",
                "keywords": "test, validation, script"
            }
            '''
            
            result = generator._parse_and_validate_response(response_text)
            
            self.assertEqual(result['title'], "Test Title")
            self.assertEqual(result['script'], "This is a test script for validation.")
            self.assertEqual(result['keywords'], "test, validation, script")
    
    def test_parse_and_validate_response_invalid_json(self):
        """Test parsing invalid JSON response"""
        with patch('script_generator.genai'):
            generator = ScriptGenerator(self.config)
            
            with self.assertRaises(ValueError) as context:
                generator._parse_and_validate_response("invalid json")
            
            self.assertIn("No valid JSON found", str(context.exception))
    
    def test_parse_and_validate_response_missing_fields(self):
        """Test parsing JSON with missing required fields"""
        with patch('script_generator.genai'):
            generator = ScriptGenerator(self.config)
            
            response_text = '{"title": "Test Title"}'
            
            with self.assertRaises(ValueError) as context:
                generator._parse_and_validate_response(response_text)
            
            self.assertIn("Missing or empty field", str(context.exception))
    
    def test_parse_and_validate_response_script_too_long(self):
        """Test script length validation - too long"""
        with patch('script_generator.genai'):
            generator = ScriptGenerator(self.config)
            
            long_script = "a" * 200  # Exceeds 150 character limit
            response_text = f'''
            {{
                "title": "Test Title",
                "script": "{long_script}",
                "keywords": "test, keywords"
            }}
            '''
            
            with self.assertRaises(ValueError) as context:
                generator._parse_and_validate_response(response_text)
            
            self.assertIn("Script too long", str(context.exception))
    
    def test_parse_and_validate_response_script_too_short(self):
        """Test script length validation - too short"""
        with patch('script_generator.genai'):
            generator = ScriptGenerator(self.config)
            
            response_text = '''
            {
                "title": "Test Title",
                "script": "short",
                "keywords": "test, keywords"
            }
            '''
            
            with self.assertRaises(ValueError) as context:
                generator._parse_and_validate_response(response_text)
            
            self.assertIn("Script too short", str(context.exception))
    
    def test_handle_api_error_api_key_error(self):
        """Test API error handling for API key issues"""
        with patch('script_generator.genai'):
            generator = ScriptGenerator(self.config)
            
            with self.assertRaises(RuntimeError) as context:
                generator._handle_api_error(Exception("Invalid API key"))
            
            self.assertIn("Invalid API key", str(context.exception))
    
    def test_handle_api_error_quota_error(self):
        """Test API error handling for quota issues"""
        with patch('script_generator.genai'):
            generator = ScriptGenerator(self.config)
            
            with self.assertRaises(RuntimeError) as context:
                generator._handle_api_error(Exception("Quota exceeded"))
            
            self.assertIn("API quota exceeded", str(context.exception))
    
    def test_handle_api_error_network_error(self):
        """Test API error handling for network issues"""
        with patch('script_generator.genai'):
            generator = ScriptGenerator(self.config)
            
            with self.assertRaises(RuntimeError) as context:
                generator._handle_api_error(Exception("Network connection failed"))
            
            self.assertIn("Network error", str(context.exception))
    
    def test_handle_api_error_generic_error(self):
        """Test API error handling for generic errors"""
        with patch('script_generator.genai'):
            generator = ScriptGenerator(self.config)
            
            with self.assertRaises(RuntimeError) as context:
                generator._handle_api_error(Exception("Unknown error"))
            
            self.assertIn("Script generation failed", str(context.exception))
    
    def test_create_prompt_template(self):
        """Test prompt template creation"""
        with patch('script_generator.genai'):
            generator = ScriptGenerator(self.config)
            
            theme = "テストテーマ"
            prompt = generator._create_prompt_template(theme)
            
            self.assertIn(theme, prompt)
            self.assertIn("30秒動画用のスクリプト", prompt)
            self.assertIn("JSON形式", prompt)
            self.assertIn("title", prompt)
            self.assertIn("script", prompt)
            self.assertIn("keywords", prompt)


class TestCreateScriptGenerator(unittest.TestCase):
    """Test cases for create_script_generator factory function"""
    
    @patch('script_generator.Config')
    @patch('script_generator.genai')
    def test_create_script_generator(self, mock_genai, mock_config_class):
        """Test factory function creates ScriptGenerator instance"""
        from script_generator import create_script_generator
        
        mock_config = Mock()
        mock_config_class.return_value = mock_config
        
        generator = create_script_generator()
        
        self.assertIsInstance(generator, ScriptGenerator)
        mock_config_class.assert_called_once()


if __name__ == '__main__':
    unittest.main()