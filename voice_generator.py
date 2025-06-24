import os
import requests
import json
import wave
import time
from typing import Dict, List, Optional
from config import Config

class VoiceGenerator:
    """Generate voice audio using VOICEVOX API"""
    
    def __init__(self, config: Config):
        self.config = config
        self.base_url = config.voicevox_server_url.rstrip('/')
        self.session = requests.Session()
        self.session.timeout = 30
    
    def generate_voice(self, script: str, output_filename: str = None) -> str:
        """
        Generate voice audio from script text
        
        Args:
            script: Text script to convert to voice
            output_filename: Output filename (optional)
            
        Returns:
            Path to generated audio file
        """
        if not script or not script.strip():
            raise ValueError("Script text cannot be empty")
        
        try:
            # Preprocess text
            processed_text = self._preprocess_text(script)
            
            # Generate audio query
            audio_query = self._create_audio_query(processed_text)
            
            # Synthesize voice
            audio_data = self._synthesize_voice(audio_query)
            
            # Save audio file
            if output_filename is None:
                timestamp = int(time.time())
                output_filename = f"voice_{timestamp}.wav"
            
            output_path = os.path.join(self.config.temp_dir, output_filename)
            self._save_audio_file(audio_data, output_path)
            
            # Validate audio duration
            duration = self._get_audio_duration(output_path)
            if duration > 35:  # Allow 5 seconds buffer for 30-second target
                print(f"Warning: Audio duration ({duration:.1f}s) exceeds 30-second target")
            
            return output_path
            
        except Exception as e:
            self._handle_voice_error(e)
    
    def _preprocess_text(self, text: str) -> str:
        """Preprocess text for better voice synthesis"""
        # Remove extra whitespace
        processed = ' '.join(text.split())
        
        # Add pauses for better pacing
        processed = processed.replace('。', '。、')
        processed = processed.replace('！', '！、')
        processed = processed.replace('？', '？、')
        
        # Handle special characters
        replacements = {
            '・': 'と',
            '～': 'から',
            '&': 'アンド',
            '%': 'パーセント',
            '…': '。'
        }
        
        for old, new in replacements.items():
            processed = processed.replace(old, new)
        
        return processed.strip()
    
    def _create_audio_query(self, text: str) -> Dict:
        """Create audio query using VOICEVOX API"""
        try:
            params = {
                'text': text,
                'speaker': self.config.speaker_id
            }
            
            response = self.session.post(
                f"{self.base_url}/audio_query",
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 400:
                raise RuntimeError("Invalid text or speaker ID")
            elif response.status_code == 503:
                raise RuntimeError("VOICEVOX server is not running")
            else:
                raise RuntimeError(f"VOICEVOX API error: {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            raise RuntimeError("Cannot connect to VOICEVOX server. Please ensure it's running.")
        except requests.exceptions.Timeout:
            raise RuntimeError("VOICEVOX server timeout. Please try again.")
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Network error: {e}")
    
    def _synthesize_voice(self, audio_query: Dict) -> bytes:
        """Synthesize voice from audio query"""
        try:
            # Adjust speaking speed to fit 30-second target
            estimated_duration = self._estimate_duration(audio_query)
            if estimated_duration > 30:
                speed_factor = min(estimated_duration / 28, 2.0)  # Max 2x speed
                audio_query['speedScale'] = audio_query.get('speedScale', 1.0) * speed_factor
            
            params = {
                'speaker': self.config.speaker_id
            }
            
            response = self.session.post(
                f"{self.base_url}/synthesis",
                params=params,
                json=audio_query,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.content
            else:
                raise RuntimeError(f"Voice synthesis failed: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Voice synthesis network error: {e}")
    
    def _estimate_duration(self, audio_query: Dict) -> float:
        """Estimate audio duration from audio query"""
        try:
            # Simple estimation based on mora count and speed
            accent_phrases = audio_query.get('accent_phrases', [])
            total_moras = sum(len(phrase.get('moras', [])) for phrase in accent_phrases)
            
            # Approximate: 1 mora ≈ 0.15 seconds at normal speed
            base_duration = total_moras * 0.15
            speed_scale = audio_query.get('speedScale', 1.0)
            
            return base_duration / speed_scale
            
        except Exception:
            # Fallback estimation based on character count
            return len(str(audio_query)) * 0.1
    
    def _save_audio_file(self, audio_data: bytes, output_path: str):
        """Save audio data to WAV file"""
        try:
            with open(output_path, 'wb') as f:
                f.write(audio_data)
            
            # Verify the file was created and is valid
            if not os.path.exists(output_path):
                raise RuntimeError("Failed to create audio file")
            
            # Basic WAV file validation
            try:
                with wave.open(output_path, 'rb') as wav_file:
                    if wav_file.getnframes() == 0:
                        raise RuntimeError("Generated audio file is empty")
            except wave.Error:
                raise RuntimeError("Generated audio file is corrupted")
                
        except IOError as e:
            raise RuntimeError(f"Failed to save audio file: {e}")
    
    def _get_audio_duration(self, audio_path: str) -> float:
        """Get duration of audio file in seconds"""
        try:
            with wave.open(audio_path, 'rb') as wav_file:
                frames = wav_file.getnframes()
                sample_rate = wav_file.getframerate()
                duration = frames / sample_rate
                return duration
        except Exception:
            return 0.0
    
    def _handle_voice_error(self, error: Exception):
        """Handle voice generation errors"""
        error_msg = str(error).lower()
        
        if 'connection' in error_msg or 'not running' in error_msg:
            raise RuntimeError("VOICEVOX server is not accessible. Please start VOICEVOX application.")
        elif 'timeout' in error_msg:
            raise RuntimeError("VOICEVOX server timeout. Please try again.")
        elif 'speaker' in error_msg:
            raise RuntimeError("Invalid speaker ID. Please check VOICEVOX configuration.")
        else:
            raise RuntimeError(f"Voice generation failed: {error}")
    
    def cleanup_temp_audio(self):
        """Clean up temporary audio files"""
        try:
            temp_files = [f for f in os.listdir(self.config.temp_dir) 
                         if f.startswith('voice_') and f.endswith('.wav')]
            
            for filename in temp_files:
                filepath = os.path.join(self.config.temp_dir, filename)
                if os.path.exists(filepath):
                    os.remove(filepath)
                    
        except Exception as e:
            print(f"Warning: Failed to cleanup temp audio files: {e}")
    
    def test_connection(self) -> bool:
        """Test connection to VOICEVOX server"""
        try:
            response = self.session.get(f"{self.base_url}/version", timeout=5)
            return response.status_code == 200
        except Exception:
            return False
    
    def get_available_speakers(self) -> List[Dict]:
        """Get list of available speakers"""
        try:
            response = self.session.get(f"{self.base_url}/speakers", timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                return []
        except Exception:
            return []

def create_voice_generator() -> VoiceGenerator:
    """Factory function to create VoiceGenerator instance"""
    config = Config()
    return VoiceGenerator(config)

# Example usage
if __name__ == "__main__":
    try:
        generator = create_voice_generator()
        
        # Test connection
        if not generator.test_connection():
            print("Error: VOICEVOX server is not accessible")
            exit(1)
        
        # Test voice generation
        script = "こんにちは。これはテスト用の音声です。AIが生成した動画の音声として使用されます。"
        print(f"Generating voice for: {script}")
        
        audio_path = generator.generate_voice(script)
        duration = generator._get_audio_duration(audio_path)
        
        print(f"\n=== Voice Generated ===")
        print(f"Audio file: {audio_path}")
        print(f"Duration: {duration:.1f} seconds")
        
    except Exception as e:
        print(f"Error: {e}")