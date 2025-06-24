import os
import requests
import time
from typing import List, Dict, Optional
from urllib.parse import urlparse
from PIL import Image
from config import Config

class ImageFetcher:
    """Fetch images from Unsplash API based on themes"""
    
    def __init__(self, config: Config):
        self.config = config
        self.base_url = "https://api.unsplash.com"
        self.headers = {
            "Authorization": f"Client-ID {config.unsplash_access_key}",
            "User-Agent": "AutoYoutube/1.0"
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
    def fetch_images(self, keywords: str, count: int = None) -> List[Dict[str, str]]:
        """
        Fetch images based on keywords
        
        Args:
            keywords: Comma-separated keywords for image search
            count: Number of images to fetch (defaults to config settings)
            
        Returns:
            List of dictionaries containing image info
        """
        if count is None:
            count = min(self.config.max_images, max(self.config.min_images, 4))
        
        try:
            search_terms = self._process_keywords(keywords)
            images = []
            
            for term in search_terms:
                if len(images) >= count:
                    break
                    
                term_images = self._search_images(term, count - len(images))
                images.extend(term_images)
                
                # Rate limiting - Unsplash allows 50 requests per hour for demo
                time.sleep(0.1)
            
            # Ensure we have enough images
            if len(images) < self.config.min_images:
                # Fallback search with broader terms
                fallback_images = self._search_images("nature landscape", count)
                images.extend(fallback_images[:count - len(images)])
            
            return self._download_and_validate_images(images[:count])
            
        except Exception as e:
            self._handle_fetch_error(e)
    
    def _process_keywords(self, keywords: str) -> List[str]:
        """Process and clean keywords for search"""
        if not keywords:
            return ["nature", "landscape"]
        
        # Split by comma and clean
        terms = [term.strip() for term in keywords.split(',')]
        # Remove empty terms and duplicates
        terms = list(set([term for term in terms if term]))
        
        # Ensure we have at least one search term
        if not terms:
            terms = ["nature", "landscape"]
        
        return terms[:3]  # Limit to 3 terms to avoid too many API calls
    
    def _search_images(self, query: str, per_page: int) -> List[Dict[str, str]]:
        """Search images on Unsplash"""
        try:
            params = {
                'query': query,
                'per_page': min(per_page, 10),  # Unsplash demo limit
                'orientation': 'landscape',
                'content_filter': 'high',
                'order_by': 'relevant'
            }
            
            response = self.session.get(
                f"{self.base_url}/search/photos",
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                return self._extract_image_info(data)
            elif response.status_code == 403:
                raise RuntimeError("Unsplash API access denied. Check your access key.")
            elif response.status_code == 429:
                raise RuntimeError("Unsplash API rate limit exceeded. Please try again later.")
            else:
                raise RuntimeError(f"Unsplash API error: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Network error while searching images: {e}")
    
    def _extract_image_info(self, data: Dict) -> List[Dict[str, str]]:
        """Extract relevant image information from API response"""
        images = []
        
        for photo in data.get('results', []):
            if 'urls' in photo and 'regular' in photo['urls']:
                image_info = {
                    'id': photo.get('id', ''),
                    'url': photo['urls']['regular'],
                    'download_url': photo['urls'].get('full', photo['urls']['regular']),
                    'description': photo.get('description', ''),
                    'alt_description': photo.get('alt_description', ''),
                    'width': photo.get('width', 0),
                    'height': photo.get('height', 0),
                    'photographer': photo.get('user', {}).get('name', 'Unknown')
                }
                images.append(image_info)
        
        return images
    
    def _download_and_validate_images(self, image_list: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Download images and validate their quality"""
        downloaded_images = []
        
        for i, image_info in enumerate(image_list):
            try:
                filename = f"image_{i+1}_{image_info['id']}.jpg"
                filepath = os.path.join(self.config.temp_dir, filename)
                
                # Download image
                if self._download_image(image_info['download_url'], filepath):
                    # Validate image
                    if self._validate_image(filepath):
                        image_info['local_path'] = filepath
                        image_info['filename'] = filename
                        downloaded_images.append(image_info)
                    else:
                        # Remove invalid image file
                        if os.path.exists(filepath):
                            os.remove(filepath)
                
            except Exception as e:
                print(f"Warning: Failed to download image {i+1}: {e}")
                continue
        
        if len(downloaded_images) == 0:
            raise RuntimeError("No valid images could be downloaded")
        
        return downloaded_images
    
    def _download_image(self, url: str, filepath: str) -> bool:
        """Download a single image"""
        try:
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            return True
            
        except Exception as e:
            print(f"Failed to download image from {url}: {e}")
            return False
    
    def _validate_image(self, filepath: str) -> bool:
        """Validate downloaded image quality and format"""
        try:
            with Image.open(filepath) as img:
                width, height = img.size
                
                # Check minimum dimensions
                if width < 800 or height < 600:
                    return False
                
                # Check aspect ratio (should be reasonable for video)
                aspect_ratio = width / height
                if aspect_ratio < 0.5 or aspect_ratio > 3.0:
                    return False
                
                # Check file format
                if img.format not in ['JPEG', 'PNG', 'WebP']:
                    return False
                
                # Check file size (not too small)
                file_size = os.path.getsize(filepath)
                if file_size < 10000:  # 10KB minimum
                    return False
                
                return True
                
        except Exception:
            return False
    
    def _handle_fetch_error(self, error: Exception):
        """Handle image fetching errors"""
        error_msg = str(error).lower()
        
        if 'access key' in error_msg or 'authorization' in error_msg:
            raise RuntimeError("Invalid Unsplash API key. Please check your configuration.")
        elif 'rate limit' in error_msg:
            raise RuntimeError("Unsplash API rate limit exceeded. Please try again later.")
        elif 'network' in error_msg or 'connection' in error_msg:
            raise RuntimeError("Network error. Please check your internet connection.")
        else:
            raise RuntimeError(f"Image fetching failed: {error}")
    
    def cleanup_temp_images(self):
        """Clean up temporary image files"""
        try:
            temp_files = [f for f in os.listdir(self.config.temp_dir) 
                         if f.startswith('image_') and f.endswith('.jpg')]
            
            for filename in temp_files:
                filepath = os.path.join(self.config.temp_dir, filename)
                if os.path.exists(filepath):
                    os.remove(filepath)
                    
        except Exception as e:
            print(f"Warning: Failed to cleanup temp images: {e}")

def create_image_fetcher() -> ImageFetcher:
    """Factory function to create ImageFetcher instance"""
    config = Config()
    return ImageFetcher(config)

# Example usage
if __name__ == "__main__":
    try:
        fetcher = create_image_fetcher()
        
        # Test image fetching
        keywords = "technology, artificial intelligence, future"
        print(f"Fetching images for: {keywords}")
        
        images = fetcher.fetch_images(keywords, 3)
        
        print(f"\n=== Downloaded {len(images)} images ===")
        for i, img in enumerate(images):
            print(f"{i+1}. {img['filename']} - {img['description'] or img['alt_description']}")
            print(f"   Size: {img['width']}x{img['height']}, Photographer: {img['photographer']}")
        
    except Exception as e:
        print(f"Error: {e}")