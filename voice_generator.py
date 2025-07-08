import os
import requests
import json
import wave
import time
import re
from typing import Dict, List, Optional
from config import Config

class VoiceGenerator:
    """Generate voice audio using VOICEVOX API"""
    
    def __init__(self, config: Config):
        self.config = config
        self.base_url = config.voicevox_server_url.rstrip('/')
        self.session = requests.Session()
        self.session.timeout = 600
    
    def generate_voice(self, script: str, output_filename: str = None, is_custom_script: bool = False) -> str:
        """
        Generate voice audio from script text
        
        Args:
            script: Text script to convert to voice
            output_filename: Output filename (optional)
            is_custom_script: Whether this is a custom script (bypasses 30-second rule)
            
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
            audio_data = self._synthesize_voice(audio_query, is_custom_script)
            
            # Save audio file
            if output_filename is None:
                timestamp = int(time.time())
                output_filename = f"voice_{timestamp}.wav"
            
            output_path = os.path.join(self.config.temp_dir, output_filename)
            self._save_audio_file(audio_data, output_path)
            
            # Validate audio duration (skip for custom scripts)
            duration = self._get_audio_duration(output_path)
            if not is_custom_script and duration > 35:  # Allow 5 seconds buffer for 30-second target
                print(f"Warning: Audio duration ({duration:.1f}s) exceeds 30-second target")
            
            return output_path
            
        except Exception as e:
            self._handle_voice_error(e)
    
    def generate_long_voice(self, script: str, output_filename: str = None, max_chunk_chars: int = 200) -> str:
        """
        Generate voice audio from long script text by splitting into chunks
        
        Args:
            script: Long text script to convert to voice
            output_filename: Output filename (optional)
            max_chunk_chars: Maximum characters per chunk (default: 200)
            
        Returns:
            Path to generated audio file
        """
        if not script or not script.strip():
            raise ValueError("Script text cannot be empty")
        
        try:
            # Split text into manageable chunks
            text_chunks = self._split_text_for_voice(script, max_chunk_chars)
            print(f"Split text into {len(text_chunks)} chunks")
            
            # Generate audio for each chunk
            temp_audio_files = []
            for i, chunk in enumerate(text_chunks):
                print(f"Generating audio for chunk {i + 1}/{len(text_chunks)}")
                
                # Generate audio for this chunk
                chunk_filename = f"chunk_{i}_{int(time.time())}.wav"
                chunk_path = self.generate_voice(chunk, chunk_filename, is_custom_script=True)
                temp_audio_files.append(chunk_path)
            
            # Combine all audio files
            if output_filename is None:
                timestamp = int(time.time())
                output_filename = f"voice_long_{timestamp}.wav"
            
            output_path = os.path.join(self.config.temp_dir, output_filename)
            combined_path = self._combine_audio_files(temp_audio_files, output_path)
            
            # Clean up temporary chunk files
            for temp_file in temp_audio_files:
                try:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                except Exception:
                    pass
            
            # Get final duration
            duration = self._get_audio_duration(combined_path)
            print(f"Generated long audio: {duration:.1f} seconds")
            
            return combined_path
            
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
    
    def _split_text_for_voice(self, text: str, max_chars: int = 200) -> List[str]:
        """Split text into smaller chunks for voice generation"""
        if len(text) <= max_chars:
            return [text]
        
        chunks = []
        current_chunk = ""
        
        # Split by natural break points
        sentences = re.split(r'([。！？])', text)
        
        for i in range(0, len(sentences), 2):
            if i + 1 < len(sentences):
                sentence = sentences[i] + sentences[i + 1]
            else:
                sentence = sentences[i]
            
            if len(current_chunk) + len(sentence) <= max_chars:
                current_chunk += sentence
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = sentence
                else:
                    # If single sentence is too long, split by commas
                    comma_parts = re.split(r'([、，])', sentence)
                    for j in range(0, len(comma_parts), 2):
                        if j + 1 < len(comma_parts):
                            part = comma_parts[j] + comma_parts[j + 1]
                        else:
                            part = comma_parts[j]
                        
                        if len(current_chunk) + len(part) <= max_chars:
                            current_chunk += part
                        else:
                            if current_chunk:
                                chunks.append(current_chunk.strip())
                            current_chunk = part
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return [chunk for chunk in chunks if chunk.strip()]
    
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
                timeout=300
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
    
    def _synthesize_voice(self, audio_query: Dict, is_custom_script: bool = False) -> bytes:
        """Synthesize voice from audio query"""
        try:
            # Adjust speaking speed to fit 30-second target (skip for custom scripts)
            if not is_custom_script:
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
                timeout=600
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
    
    def _combine_audio_files(self, audio_files: List[str], output_path: str) -> str:
        """Combine multiple WAV files into a single file"""
        if not audio_files:
            raise ValueError("No audio files to combine")
        
        if len(audio_files) == 1:
            # If only one file, just copy it
            import shutil
            shutil.copy2(audio_files[0], output_path)
            return output_path
        
        try:
            # Get parameters from first file
            with wave.open(audio_files[0], 'rb') as first_wav:
                params = first_wav.getparams()
                sample_rate = first_wav.getframerate()
                sample_width = first_wav.getsampwidth()
                channels = first_wav.getnchannels()
            
            # Create output file
            with wave.open(output_path, 'wb') as output_wav:
                output_wav.setparams(params)
                
                # Add silence between chunks (0.2 seconds)
                silence_frames = int(sample_rate * 0.2)
                silence_data = b'\x00' * (silence_frames * sample_width * channels)
                
                for i, audio_file in enumerate(audio_files):
                    with wave.open(audio_file, 'rb') as input_wav:
                        # Verify compatibility
                        if (input_wav.getframerate() != sample_rate or 
                            input_wav.getsampwidth() != sample_width or 
                            input_wav.getnchannels() != channels):
                            raise RuntimeError(f"Audio file {audio_file} has incompatible format")
                        
                        # Copy audio data
                        output_wav.writeframes(input_wav.readframes(input_wav.getnframes()))
                        
                        # Add silence between files (except after last file)
                        if i < len(audio_files) - 1:
                            output_wav.writeframes(silence_data)
            
            return output_path
            
        except Exception as e:
            raise RuntimeError(f"Failed to combine audio files: {e}")
    
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
            response = self.session.get(f"{self.base_url}/speakers", timeout=60)
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