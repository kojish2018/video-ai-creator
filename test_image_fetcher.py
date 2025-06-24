import unittest
from unittest.mock import Mock, patch, MagicMock, mock_open
import os
import tempfile
import json
from PIL import Image
import requests
from image_fetcher import ImageFetcher
from config import Config


class TestImageFetcher(unittest.TestCase):
    """Test cases for ImageFetcher class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = Mock(spec=Config)
        self.config.unsplash_access_key = "test_access_key"
        self.config.temp_dir = "/tmp/test"
        self.config.min_images = 3
        self.config.max_images = 5
        
        # Create temp directory for testing
        os.makedirs(self.config.temp_dir, exist_ok=True)
    
    def tearDown(self):
        """Clean up test fixtures"""
        # Clean up test temp directory
        if os.path.exists(self.config.temp_dir):
            import shutil
            shutil.rmtree(self.config.temp_dir, ignore_errors=True)
    
    def test_init(self):
        """Test ImageFetcher initialization"""
        fetcher = ImageFetcher(self.config)
        
        self.assertEqual(fetcher.config, self.config)
        self.assertEqual(fetcher.base_url, "https://api.unsplash.com")
        self.assertIn("Client-ID test_access_key", fetcher.headers["Authorization"])
        self.assertIsInstance(fetcher.session, requests.Session)
    
    def test_process_keywords_valid(self):
        """Test keyword processing with valid input"""
        fetcher = ImageFetcher(self.config)
        
        # Test normal keywords
        result = fetcher._process_keywords("AI, technology, future")
        self.assertEqual(set(result), {"AI", "technology", "future"})
        
        # Test with extra spaces
        result = fetcher._process_keywords(" AI , technology , future ")
        self.assertEqual(set(result), {"AI", "technology", "future"})
        
        # Test with duplicates
        result = fetcher._process_keywords("AI, AI, technology")
        self.assertIn("AI", result)
        self.assertIn("technology", result)
        self.assertEqual(len(result), 2)
    
    def test_process_keywords_empty(self):
        """Test keyword processing with empty input"""
        fetcher = ImageFetcher(self.config)
        
        # Test empty string
        result = fetcher._process_keywords("")
        self.assertEqual(result, ["nature", "landscape"])
        
        # Test None
        result = fetcher._process_keywords(None)
        self.assertEqual(result, ["nature", "landscape"])
        
        # Test only spaces/commas
        result = fetcher._process_keywords(" , , ")
        self.assertEqual(result, ["nature", "landscape"])
    
    def test_process_keywords_limit(self):
        """Test keyword processing with too many keywords"""
        fetcher = ImageFetcher(self.config)
        
        keywords = "AI, tech, future, science, innovation, development"
        result = fetcher._process_keywords(keywords)
        
        # Should limit to 3 terms
        self.assertEqual(len(result), 3)
        self.assertTrue(all(term in ["AI", "tech", "future", "science", "innovation", "development"] 
                          for term in result))
    
    def test_extract_image_info(self):
        """Test image information extraction from API response"""
        fetcher = ImageFetcher(self.config)
        
        mock_data = {
            'results': [
                {
                    'id': 'test123',
                    'urls': {
                        'regular': 'https://example.com/regular.jpg',
                        'full': 'https://example.com/full.jpg'
                    },
                    'description': 'Test image',
                    'alt_description': 'Alt description',
                    'width': 1920,
                    'height': 1080,
                    'user': {'name': 'Test Photographer'}
                }
            ]
        }
        
        result = fetcher._extract_image_info(mock_data)
        
        self.assertEqual(len(result), 1)
        image = result[0]
        self.assertEqual(image['id'], 'test123')
        self.assertEqual(image['url'], 'https://example.com/regular.jpg')
        self.assertEqual(image['download_url'], 'https://example.com/full.jpg')
        self.assertEqual(image['description'], 'Test image')
        self.assertEqual(image['width'], 1920)
        self.assertEqual(image['height'], 1080)
        self.assertEqual(image['photographer'], 'Test Photographer')
    
    def test_extract_image_info_missing_fields(self):
        """Test image info extraction with missing fields"""
        fetcher = ImageFetcher(self.config)
        
        mock_data = {
            'results': [
                {
                    'id': 'test123',
                    'urls': {'regular': 'https://example.com/regular.jpg'}
                }
            ]
        }
        
        result = fetcher._extract_image_info(mock_data)
        
        self.assertEqual(len(result), 1)
        image = result[0]
        self.assertEqual(image['id'], 'test123')
        self.assertEqual(image['description'], '')
        self.assertEqual(image['photographer'], 'Unknown')
        self.assertEqual(image['width'], 0)
    
    @patch('image_fetcher.requests.get')
    def test_download_image_success(self, mock_get):
        """Test successful image download"""
        fetcher = ImageFetcher(self.config)
        
        # Mock successful response
        mock_response = Mock()
        mock_response.iter_content.return_value = [b'fake image data']
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        test_url = "https://example.com/image.jpg"
        test_filepath = os.path.join(self.config.temp_dir, "test.jpg")
        
        with patch('builtins.open', mock_open()) as mock_file:
            result = fetcher._download_image(test_url, test_filepath)
            
            self.assertTrue(result)
            mock_get.assert_called_once_with(test_url, stream=True, timeout=30)
            mock_file.assert_called_once_with(test_filepath, 'wb')
    
    @patch('image_fetcher.requests.get')
    def test_download_image_failure(self, mock_get):
        """Test image download failure"""
        fetcher = ImageFetcher(self.config)
        
        # Mock failed response
        mock_get.side_effect = requests.exceptions.RequestException("Network error")
        
        test_url = "https://example.com/image.jpg"
        test_filepath = os.path.join(self.config.temp_dir, "test.jpg")
        
        result = fetcher._download_image(test_url, test_filepath)
        
        self.assertFalse(result)
    
    @patch('image_fetcher.Image.open')
    @patch('os.path.getsize')
    def test_validate_image_valid(self, mock_getsize, mock_image_open):
        """Test image validation with valid image"""
        fetcher = ImageFetcher(self.config)
        
        # Mock valid image
        mock_img = Mock()
        mock_img.size = (1920, 1080)
        mock_img.format = 'JPEG'
        mock_image_open.return_value.__enter__.return_value = mock_img
        mock_getsize.return_value = 50000  # 50KB
        
        result = fetcher._validate_image("/path/to/test.jpg")
        
        self.assertTrue(result)
    
    @patch('image_fetcher.Image.open')
    @patch('os.path.getsize')
    def test_validate_image_too_small(self, mock_getsize, mock_image_open):
        """Test image validation with too small dimensions"""
        fetcher = ImageFetcher(self.config)
        
        # Mock small image
        mock_img = Mock()
        mock_img.size = (400, 300)  # Too small
        mock_img.format = 'JPEG'
        mock_image_open.return_value.__enter__.return_value = mock_img
        mock_getsize.return_value = 50000
        
        result = fetcher._validate_image("/path/to/test.jpg")
        
        self.assertFalse(result)
    
    @patch('image_fetcher.Image.open')
    @patch('os.path.getsize')
    def test_validate_image_bad_aspect_ratio(self, mock_getsize, mock_image_open):
        """Test image validation with bad aspect ratio"""
        fetcher = ImageFetcher(self.config)
        
        # Mock image with bad aspect ratio
        mock_img = Mock()
        mock_img.size = (1000, 4000)  # Too tall (aspect ratio = 0.25)
        mock_img.format = 'JPEG'
        mock_image_open.return_value.__enter__.return_value = mock_img
        mock_getsize.return_value = 50000
        
        result = fetcher._validate_image("/path/to/test.jpg")
        
        self.assertFalse(result)
    
    @patch('image_fetcher.Image.open')
    @patch('os.path.getsize')
    def test_validate_image_unsupported_format(self, mock_getsize, mock_image_open):
        """Test image validation with unsupported format"""
        fetcher = ImageFetcher(self.config)
        
        # Mock image with unsupported format
        mock_img = Mock()
        mock_img.size = (1920, 1080)
        mock_img.format = 'GIF'  # Unsupported
        mock_image_open.return_value.__enter__.return_value = mock_img
        mock_getsize.return_value = 50000
        
        result = fetcher._validate_image("/path/to/test.jpg")
        
        self.assertFalse(result)
    
    @patch('image_fetcher.Image.open')
    @patch('os.path.getsize')
    def test_validate_image_too_small_file(self, mock_getsize, mock_image_open):
        """Test image validation with too small file size"""
        fetcher = ImageFetcher(self.config)
        
        # Mock valid image but small file size
        mock_img = Mock()
        mock_img.size = (1920, 1080)
        mock_img.format = 'JPEG'
        mock_image_open.return_value.__enter__.return_value = mock_img
        mock_getsize.return_value = 5000  # Too small (5KB)
        
        result = fetcher._validate_image("/path/to/test.jpg")
        
        self.assertFalse(result)
    
    @patch('image_fetcher.Image.open')
    def test_validate_image_corrupt(self, mock_image_open):
        """Test image validation with corrupt image"""
        fetcher = ImageFetcher(self.config)
        
        # Mock corrupt image
        mock_image_open.side_effect = Exception("Corrupt image")
        
        result = fetcher._validate_image("/path/to/test.jpg")
        
        self.assertFalse(result)
    
    @patch.object(ImageFetcher, '_search_images')
    @patch.object(ImageFetcher, '_download_and_validate_images')
    def test_fetch_images_success(self, mock_download, mock_search):
        """Test successful image fetching"""
        fetcher = ImageFetcher(self.config)
        
        # Mock search results
        mock_images = [
            {'id': '1', 'url': 'url1', 'description': 'Image 1'},
            {'id': '2', 'url': 'url2', 'description': 'Image 2'}
        ]
        mock_search.return_value = mock_images
        mock_download.return_value = mock_images
        
        result = fetcher.fetch_images("AI, technology", 2)
        
        self.assertEqual(result, mock_images)
        mock_search.assert_called()
        mock_download.assert_called_once()
    
    @patch.object(ImageFetcher, '_search_images')
    def test_fetch_images_fallback(self, mock_search):
        """Test image fetching with fallback when not enough images found"""
        fetcher = ImageFetcher(self.config)
        
        # Mock insufficient search results, then fallback results
        mock_search.side_effect = [
            [],  # No results for first search
            [{'id': '1', 'url': 'url1'}] * 3  # Fallback results
        ]
        
        with patch.object(fetcher, '_download_and_validate_images') as mock_download:
            mock_download.return_value = [{'id': '1', 'url': 'url1'}] * 3
            
            result = fetcher.fetch_images("obscure term")
            
            self.assertEqual(len(result), 3)
            # Should call search twice (original + fallback)
            self.assertEqual(mock_search.call_count, 2)
    
    def test_handle_fetch_error_access_key(self):
        """Test error handling for API key issues"""
        fetcher = ImageFetcher(self.config)
        
        with self.assertRaises(RuntimeError) as context:
            fetcher._handle_fetch_error(Exception("Invalid access key"))
        
        self.assertIn("Invalid Unsplash API key", str(context.exception))
    
    def test_handle_fetch_error_rate_limit(self):
        """Test error handling for rate limit issues"""
        fetcher = ImageFetcher(self.config)
        
        with self.assertRaises(RuntimeError) as context:
            fetcher._handle_fetch_error(Exception("Rate limit exceeded"))
        
        self.assertIn("rate limit exceeded", str(context.exception))
    
    def test_handle_fetch_error_network(self):
        """Test error handling for network issues"""
        fetcher = ImageFetcher(self.config)
        
        with self.assertRaises(RuntimeError) as context:
            fetcher._handle_fetch_error(Exception("Network connection failed"))
        
        self.assertIn("Network error", str(context.exception))
    
    def test_handle_fetch_error_generic(self):
        """Test error handling for generic errors"""
        fetcher = ImageFetcher(self.config)
        
        with self.assertRaises(RuntimeError) as context:
            fetcher._handle_fetch_error(Exception("Unknown error"))
        
        self.assertIn("Image fetching failed", str(context.exception))
    
    @patch('os.listdir')
    @patch('os.path.exists')
    @patch('os.remove')
    def test_cleanup_temp_images(self, mock_remove, mock_exists, mock_listdir):
        """Test cleanup of temporary images"""
        fetcher = ImageFetcher(self.config)
        
        # Mock temp files
        mock_listdir.return_value = [
            'image_1_test.jpg',
            'image_2_test.jpg',
            'other_file.txt',  # Should be ignored
            'image_3_test.jpg'
        ]
        mock_exists.return_value = True
        
        fetcher.cleanup_temp_images()
        
        # Should remove only image files
        self.assertEqual(mock_remove.call_count, 3)
        mock_remove.assert_any_call(os.path.join(self.config.temp_dir, 'image_1_test.jpg'))
        mock_remove.assert_any_call(os.path.join(self.config.temp_dir, 'image_2_test.jpg'))
        mock_remove.assert_any_call(os.path.join(self.config.temp_dir, 'image_3_test.jpg'))
    
    @patch('requests.Session.get')
    def test_search_images_success(self, mock_get):
        """Test successful image search"""
        fetcher = ImageFetcher(self.config)
        
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'results': [
                {
                    'id': 'test1',
                    'urls': {'regular': 'url1', 'full': 'full1'},
                    'description': 'Test image 1'
                }
            ]
        }
        mock_get.return_value = mock_response
        
        result = fetcher._search_images("test query", 5)
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['id'], 'test1')
        mock_get.assert_called_once()
    
    @patch('requests.Session.get')
    def test_search_images_api_errors(self, mock_get):
        """Test image search API error handling"""
        fetcher = ImageFetcher(self.config)
        
        # Test 403 error
        mock_response = Mock()
        mock_response.status_code = 403
        mock_get.return_value = mock_response
        
        with self.assertRaises(RuntimeError) as context:
            fetcher._search_images("test", 5)
        self.assertIn("access denied", str(context.exception))
        
        # Test 429 error
        mock_response.status_code = 429
        with self.assertRaises(RuntimeError) as context:
            fetcher._search_images("test", 5)
        self.assertIn("rate limit exceeded", str(context.exception))
        
        # Test other error
        mock_response.status_code = 500
        with self.assertRaises(RuntimeError) as context:
            fetcher._search_images("test", 5)
        self.assertIn("API error: 500", str(context.exception))
    
    @patch('requests.Session.get')
    def test_search_images_network_error(self, mock_get):
        """Test image search network error handling"""
        fetcher = ImageFetcher(self.config)
        
        mock_get.side_effect = requests.exceptions.RequestException("Network error")
        
        with self.assertRaises(RuntimeError) as context:
            fetcher._search_images("test", 5)
        
        self.assertIn("Network error while searching", str(context.exception))


class TestCreateImageFetcher(unittest.TestCase):
    """Test cases for create_image_fetcher factory function"""
    
    @patch('image_fetcher.Config')
    def test_create_image_fetcher(self, mock_config_class):
        """Test factory function creates ImageFetcher instance"""
        from image_fetcher import create_image_fetcher
        
        mock_config = Mock()
        mock_config_class.return_value = mock_config
        
        fetcher = create_image_fetcher()
        
        self.assertIsInstance(fetcher, ImageFetcher)
        mock_config_class.assert_called_once()


if __name__ == '__main__':
    unittest.main()