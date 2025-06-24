import json
import google.generativeai as genai
from typing import Dict, Optional
from config import Config

class ScriptGenerator:
    """Generate video scripts using Google Gemini API"""
    
    def __init__(self, config: Config):
        self.config = config
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Gemini API client"""
        try:
            genai.configure(api_key=self.config.gemini_api_key)
            self.client = genai.GenerativeModel('gemini-1.5-flash')
        except Exception as e:
            raise RuntimeError(f"Failed to initialize Gemini client: {e}")
    
    def generate_script(self, theme: str) -> Dict[str, str]:
        """
        Generate a 30-second video script based on the given theme
        
        Args:
            theme: The theme/topic for the video
            
        Returns:
            Dict containing title, script, and keywords
        """
        if not theme or not theme.strip():
            raise ValueError("Theme cannot be empty")
        
        try:
            prompt = self._create_prompt_template(theme)
            response = self.client.generate_content(prompt)
            
            if not response or not response.text:
                raise RuntimeError("Empty response from Gemini API")
            
            return self._parse_and_validate_response(response.text)
            
        except Exception as e:
            self._handle_api_error(e)
    
    def _create_prompt_template(self, theme: str) -> str:
        """Create structured prompt for 30-second video script generation"""
        return f"""
30秒動画用のスクリプトを生成してください。以下の形式で出力してください：

テーマ: {theme}

要件:
- 30秒以内で読み上げ可能なテキスト量（約75-90文字）
- 視聴者の興味を引く導入
- 簡潔で分かりやすい内容
- 印象的な締めくくり

出力形式（JSON形式で出力してください）:
{{
    "title": "動画タイトル（魅力的で簡潔）",
    "script": "ナレーション用スクリプト（30秒以内で読める長さ）",
    "keywords": "画像検索用キーワード（カンマ区切りで3-5個）"
}}

注意:
- JSONの構文を正確に守ってください
- スクリプトは自然な日本語で記述してください
- キーワードは画像検索に適した具体的な単語を選んでください
"""
    
    def _parse_and_validate_response(self, response_text: str) -> Dict[str, str]:
        """Parse and validate the API response"""
        try:
            # Extract JSON from response if it contains extra text
            response_text = response_text.strip()
            
            # Find JSON block in the response
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}')
            
            if start_idx == -1 or end_idx == -1:
                raise ValueError("No valid JSON found in response")
            
            json_text = response_text[start_idx:end_idx+1]
            parsed_response = json.loads(json_text)
            
            # Validate required fields
            required_fields = ['title', 'script', 'keywords']
            for field in required_fields:
                if field not in parsed_response or not parsed_response[field]:
                    raise ValueError(f"Missing or empty field: {field}")
            
            # Validate script length (should be readable in 30 seconds)
            script_length = len(parsed_response['script'])
            if script_length > 150:  # Approximate 30-second limit
                raise ValueError(f"Script too long: {script_length} characters (max ~150)")
            
            if script_length < 20:  # Too short
                raise ValueError(f"Script too short: {script_length} characters (min ~20)")
            
            return {
                'title': parsed_response['title'].strip(),
                'script': parsed_response['script'].strip(),
                'keywords': parsed_response['keywords'].strip()
            }
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in response: {e}")
        except Exception as e:
            raise ValueError(f"Failed to parse response: {e}")
    
    def _handle_api_error(self, error: Exception):
        """Handle API-related errors with appropriate error messages"""
        error_msg = str(error).lower()
        
        if 'api key' in error_msg or 'authentication' in error_msg:
            raise RuntimeError("Invalid API key. Please check your Gemini API configuration.")
        elif 'quota' in error_msg or 'rate limit' in error_msg:
            raise RuntimeError("API quota exceeded. Please try again later.")
        elif 'network' in error_msg or 'connection' in error_msg:
            raise RuntimeError("Network error. Please check your internet connection.")
        else:
            raise RuntimeError(f"Script generation failed: {error}")
    
    def validate_theme_input(self, theme: str) -> bool:
        """Validate theme input before processing"""
        if not theme or not isinstance(theme, str):
            return False
        
        theme = theme.strip()
        if len(theme) < 2:
            return False
        
        if len(theme) > 100:  # Reasonable limit for theme length
            return False
        
        return True

def create_script_generator() -> ScriptGenerator:
    """Factory function to create ScriptGenerator instance"""
    config = Config()
    return ScriptGenerator(config)

# Example usage and testing
if __name__ == "__main__":
    try:
        generator = create_script_generator()
        
        # Test with sample theme
        theme = "人工知能の未来"
        print(f"Generating script for theme: {theme}")
        
        result = generator.generate_script(theme)
        
        print("\n=== Generated Script ===")
        print(f"Title: {result['title']}")
        print(f"Script: {result['script']}")
        print(f"Keywords: {result['keywords']}")
        print(f"Script length: {len(result['script'])} characters")
        
    except Exception as e:
        print(f"Error: {e}")