import os
import time
from typing import List, Dict, Optional
from moviepy.editor import (
    VideoFileClip, ImageClip, AudioFileClip, CompositeVideoClip,
    concatenate_videoclips, ColorClip, TextClip
)
from config import Config

class VideoCreator:
    """Create videos using MoviePy with video background and audio"""
    
    def __init__(self, config: Config):
        self.config = config
        self.target_duration = config.video_duration
        self.video_size = (config.video_width, config.video_height)
        self.fps = config.video_fps
    
    def create_video(self, images: List[Dict[str, str]], audio_path: str, output_filename: str = None, is_custom_script: bool = False, videos: Optional[List[Dict[str, str]]] = None) -> str:
        """
        Create a video with video background (or image slideshow fallback) and audio
        
        Args:
            images: List of image info dictionaries with 'local_path' key (fallback)
            audio_path: Path to audio file
            output_filename: Output video filename (optional)
            is_custom_script: Whether this is a custom script (bypasses 30-second rule)
            videos: List of video info dictionaries with 'local_path' key (primary)
            
        Returns:
            Path to created video file
        """
        if not videos and not images:
            raise ValueError("No videos or images provided for video creation")
        
        if not os.path.exists(audio_path):
            raise ValueError(f"Audio file not found: {audio_path}")
        
        try:
            # Load audio to get actual duration
            audio_clip = AudioFileClip(audio_path)
            # For custom scripts, use full audio duration; for regular scripts, limit to target duration
            actual_duration = audio_clip.duration if is_custom_script else min(audio_clip.duration, self.target_duration)
            
            # Create video background (videos prioritized over images)
            if videos and len(videos) > 0:
                video_clip = self._create_video_background(videos, actual_duration)
            else:
                # Fallback to image slideshow
                video_clip = self._create_image_slideshow(images, actual_duration)
            
            # Combine video and audio
            final_clip = video_clip.set_audio(audio_clip.subclip(0, actual_duration))
            
            # Generate output filename
            if output_filename is None:
                timestamp = int(time.time())
                output_filename = f"video_{timestamp}.mp4"
            
            output_path = os.path.join(self.config.output_dir, output_filename)
            
            # Render video
            self._render_video(final_clip, output_path)
            
            # Cleanup
            audio_clip.close()
            video_clip.close()
            final_clip.close()
            
            return output_path
            
        except Exception as e:
            self._handle_video_error(e)
    
    def _create_video_background(self, videos: List[Dict[str, str]], duration: float) -> VideoFileClip:
        """Create video background with looping/cutting to match audio duration"""
        try:
            print(f"🔍 DEBUG: _create_video_background called with {len(videos)} videos, duration={duration}")
            
            # Validate inputs
            if not videos:
                raise ValueError("No videos provided")
            
            if duration <= 0:
                raise ValueError("Duration must be positive")
            
            # Select the first valid video
            video_path = None
            for i, video_info in enumerate(videos):
                print(f"🔍 DEBUG: Checking video {i}: {video_info}")
                if 'local_path' in video_info and os.path.exists(video_info['local_path']):
                    video_path = video_info['local_path']
                    print(f"🔍 DEBUG: Selected video path: {video_path}")
                    break
            
            if not video_path:
                raise RuntimeError("No valid video files found")
            
            # Load video clip
            print(f"🔍 DEBUG: Loading video clip from: {video_path}")
            video_clip = VideoFileClip(video_path)
            print(f"🔍 DEBUG: Loaded video clip: duration={video_clip.duration}, size={video_clip.size}")
            
            # Validate loaded video clip
            if not video_clip or video_clip.duration <= 0:
                video_clip.close()
                raise RuntimeError(f"Invalid video file: {video_path}")
            
            # Resize video to match target dimensions
            print(f"🔍 DEBUG: Resizing video clip...")
            resized_clip = self._resize_and_fit_video(video_clip)
            print(f"🔍 DEBUG: Resized clip: duration={resized_clip.duration}, size={resized_clip.size}")
            print(f"🔍 DEBUG: Resized clip type: {type(resized_clip)}")
            
            # Validate resized clip
            if not resized_clip or resized_clip.duration <= 0:
                video_clip.close()
                if resized_clip:
                    resized_clip.close()
                raise RuntimeError("Failed to resize video clip")
            
            # Adjust video duration to match audio
            if resized_clip.duration >= duration:
                # Video is longer than needed, cut it
                print(f"🔍 DEBUG: Cutting video from {resized_clip.duration}s to {duration}s")
                final_video = resized_clip.subclip(0, duration)
            else:
                # Video is shorter than needed, loop it
                print(f"🔍 DEBUG: Looping video from {resized_clip.duration}s to {duration}s")
                final_video = self._loop_video(resized_clip, duration)
            
            print(f"🔍 DEBUG: Final video: duration={final_video.duration}, type={type(final_video)}")
            
            # Remove original audio from video (we'll use the generated audio)
            final_video = final_video.without_audio()
            print(f"🔍 DEBUG: Audio removed, final video ready")
            
            # Cleanup
            video_clip.close()
            if resized_clip != final_video:
                resized_clip.close()
            
            return final_video
            
        except Exception as e:
            print(f"🔍 DEBUG: Exception in _create_video_background: {e}")
            raise RuntimeError(f"Failed to create video background: {e}")
    
    def _resize_and_fit_video(self, video_clip: VideoFileClip) -> VideoFileClip:
        """Resize and fit video to target dimensions while maintaining aspect ratio"""
        try:
            print(f"🔍 DEBUG: _resize_and_fit_video called with clip: {type(video_clip)}")
            
            # Validate input
            if not video_clip:
                raise ValueError("Invalid video clip provided")
            
            if not hasattr(video_clip, 'size') or not video_clip.size:
                raise ValueError("Video clip missing size information")
            
            # Get original dimensions
            orig_w, orig_h = video_clip.size
            target_w, target_h = self.video_size
            print(f"🔍 DEBUG: Original size: {orig_w}x{orig_h}, Target size: {target_w}x{target_h}")
            
            if orig_w <= 0 or orig_h <= 0:
                raise ValueError(f"Invalid video dimensions: {orig_w}x{orig_h}")
            
            # Calculate scale factor to fit within target dimensions
            scale_w = target_w / orig_w
            scale_h = target_h / orig_h
            scale = min(scale_w, scale_h)
            
            # Resize video
            new_w = int(orig_w * scale)
            new_h = int(orig_h * scale)
            print(f"🔍 DEBUG: Calculated new size: {new_w}x{new_h}, scale: {scale}")
            
            # Ensure minimum dimensions
            if new_w <= 0 or new_h <= 0:
                raise ValueError(f"Calculated dimensions too small: {new_w}x{new_h}")
            
            resized_clip = video_clip.resize((new_w, new_h))
            print(f"🔍 DEBUG: Resized clip created: {type(resized_clip)}")
            
            # Validate resized clip
            if not resized_clip:
                raise RuntimeError("Failed to resize video clip")
            
            # If video doesn't fill the entire frame, add black background
            if new_w < target_w or new_h < target_h:
                print(f"🔍 DEBUG: Video needs background - creating composite")
                
                # Create black background
                background = ColorClip(size=self.video_size, color=(0, 0, 0))
                background = background.set_duration(video_clip.duration)
                print(f"🔍 DEBUG: Background created: {type(background)}, duration: {background.duration}")
                
                # Validate background
                if not background:
                    raise RuntimeError("Failed to create background clip")
                
                # Center the video on the background
                x_offset = (target_w - new_w) // 2
                y_offset = (target_h - new_h) // 2
                print(f"🔍 DEBUG: Positioning video at offset: ({x_offset}, {y_offset})")
                
                resized_clip = resized_clip.set_position((x_offset, y_offset))
                print(f"🔍 DEBUG: Positioned clip: {type(resized_clip)}")
                
                # Create composite clip with validation
                try:
                    print(f"🔍 DEBUG: Creating CompositeVideoClip with background and resized clip")
                    final_clip = CompositeVideoClip([background, resized_clip])
                    print(f"🔍 DEBUG: CompositeVideoClip created: {type(final_clip)}")
                    
                    # Check if the composite clip has the bg attribute
                    if hasattr(final_clip, 'bg'):
                        print(f"🔍 DEBUG: CompositeVideoClip.bg: {final_clip.bg}")
                    else:
                        print(f"🔍 DEBUG: CompositeVideoClip has no bg attribute!")
                    
                    # Validate final clip
                    if not final_clip:
                        raise RuntimeError("Failed to create composite video clip")
                    
                    return final_clip
                except Exception as e:
                    print(f"🔍 DEBUG: Exception creating composite clip: {e}")
                    # Clean up on error
                    if background:
                        background.close()
                    if resized_clip:
                        resized_clip.close()
                    raise RuntimeError(f"Failed to create composite clip: {e}")
            else:
                print(f"🔍 DEBUG: Video fits perfectly, no background needed")
            
            return resized_clip
            
        except Exception as e:
            print(f"🔍 DEBUG: Exception in _resize_and_fit_video: {e}")
            raise RuntimeError(f"Failed to resize video: {e}")
    
    def _loop_video(self, video_clip: VideoFileClip, target_duration: float) -> VideoFileClip:
        """Loop video to match target duration"""
        try:
            print(f"🔍 DEBUG: _loop_video called with duration={video_clip.duration}, target={target_duration}")
            
            # Validate input
            if not video_clip or video_clip.duration <= 0:
                raise ValueError("Invalid video clip provided")
            
            if target_duration <= 0:
                raise ValueError("Target duration must be positive")
            
            # If video is already longer than target, just cut it
            if video_clip.duration >= target_duration:
                print(f"🔍 DEBUG: Video is longer than target, cutting to {target_duration}s")
                return video_clip.subclip(0, target_duration)
            
            clips = []
            current_duration = 0
            
            while current_duration < target_duration:
                remaining_duration = target_duration - current_duration
                
                if remaining_duration >= video_clip.duration:
                    # Add full video clip (use subclip to preserve reader)
                    clip_copy = video_clip.subclip(0, video_clip.duration)
                    clips.append(clip_copy)
                    current_duration += video_clip.duration
                    print(f"🔍 DEBUG: Added full clip subclip {len(clips)}, duration={clip_copy.duration}")
                else:
                    # Add partial clip to reach exact duration
                    partial_clip = video_clip.subclip(0, remaining_duration)
                    clips.append(partial_clip)
                    current_duration += remaining_duration
                    print(f"🔍 DEBUG: Added partial clip {len(clips)}, duration={partial_clip.duration}")
            
            # Ensure we have clips to concatenate
            if not clips:
                raise RuntimeError("No clips generated for looping")
            
            print(f"🔍 DEBUG: About to concatenate {len(clips)} clips")
            
            # Validate all clips before concatenation
            for i, clip in enumerate(clips):
                if not clip or not hasattr(clip, 'duration') or clip.duration <= 0:
                    raise RuntimeError(f"Invalid clip at index {i}")
                
                print(f"🔍 DEBUG: Clip {i}: type={type(clip)}, duration={clip.duration}")
                
                # Check if this is a CompositeVideoClip and examine its bg
                if hasattr(clip, 'bg'):
                    print(f"🔍 DEBUG: Clip {i} has bg attribute: {clip.bg}")
                    if clip.bg is None:
                        print(f"🔍 DEBUG: ⚠️ WARNING: Clip {i} has None bg!")
            
            # Concatenate all clips with method='compose'
            print(f"🔍 DEBUG: Concatenating clips with method='compose'")
            looped_video = concatenate_videoclips(clips, method='compose')
            print(f"🔍 DEBUG: Concatenated video: type={type(looped_video)}, duration={looped_video.duration}")
            
            # Check the final concatenated video for bg issues
            if hasattr(looped_video, 'bg'):
                print(f"🔍 DEBUG: Final looped video bg: {looped_video.bg}")
            
            return looped_video
            
        except Exception as e:
            print(f"🔍 DEBUG: Exception in _loop_video: {e}")
            raise RuntimeError(f"Failed to loop video: {e}")
    
    def _create_image_slideshow(self, images: List[Dict[str, str]], duration: float) -> VideoFileClip:
        """Create image slideshow with transitions"""
        try:
            # Calculate duration per image
            image_duration = duration / len(images)
            transition_duration = 0.5  # 0.5 seconds for fade transition
            
            clips = []
            
            for i, image_info in enumerate(images):
                image_path = image_info['local_path']
                
                if not os.path.exists(image_path):
                    print(f"Warning: Image not found: {image_path}")
                    continue
                
                # Create image clip
                img_clip = ImageClip(image_path)
                
                # Resize and fit to video dimensions
                img_clip = self._resize_and_fit_image(img_clip)
                
                # Set duration
                img_clip = img_clip.set_duration(image_duration)
                
                # Add fade transitions (except for first and last clips)
                if i > 0:
                    img_clip = img_clip.fadein(transition_duration)
                if i < len(images) - 1:
                    img_clip = img_clip.fadeout(transition_duration)
                
                clips.append(img_clip)
            
            if not clips:
                raise RuntimeError("No valid images found for slideshow")
            
            # Concatenate all clips
            final_clip = concatenate_videoclips(clips, method="compose")
            
            # Ensure exact duration
            if final_clip.duration > duration:
                final_clip = final_clip.subclip(0, duration)
            elif final_clip.duration < duration:
                # Extend last frame if needed
                last_frame = clips[-1].to_ImageClip()
                extension = last_frame.set_duration(duration - final_clip.duration)
                final_clip = concatenate_videoclips([final_clip, extension])
            
            return final_clip
            
        except Exception as e:
            raise RuntimeError(f"Failed to create image slideshow: {e}")
    
    def _resize_and_fit_image(self, image_clip: ImageClip) -> ImageClip:
        """Resize and fit image to video dimensions while maintaining aspect ratio"""
        try:
            # Get original dimensions
            orig_w, orig_h = image_clip.size
            target_w, target_h = self.video_size
            
            # Calculate scale factor to fit within target dimensions
            scale_w = target_w / orig_w
            scale_h = target_h / orig_h
            scale = min(scale_w, scale_h)
            
            # Resize image
            new_w = int(orig_w * scale)
            new_h = int(orig_h * scale)
            
            resized_clip = image_clip.resize((new_w, new_h))
            
            # If image doesn't fill the entire frame, add black background
            if new_w < target_w or new_h < target_h:
                # Create black background
                background = ColorClip(size=self.video_size, color=(0, 0, 0))
                
                # Center the image on the background
                x_offset = (target_w - new_w) // 2
                y_offset = (target_h - new_h) // 2
                
                resized_clip = resized_clip.set_position((x_offset, y_offset))
                final_clip = CompositeVideoClip([background, resized_clip])
                
                return final_clip
            
            return resized_clip
            
        except Exception as e:
            raise RuntimeError(f"Failed to resize image: {e}")
    
    def _render_video(self, clip: VideoFileClip, output_path: str):
        """Render video to MP4 format"""
        try:
            # Video codec settings for good quality and compatibility
            codec_params = {
                'codec': 'libx264',
                'audio_codec': 'aac',
                'fps': self.fps,
                'bitrate': '2000k',  # 2 Mbps for good quality
                'audio_bitrate': '128k'
            }
            
            # Render video with progress bar
            clip.write_videofile(
                output_path,
                **codec_params,
                verbose=False,
                logger=None,  # Disable verbose logging
                temp_audiofile='temp-audio.m4a',
                remove_temp=True
            )
            
            # Verify output file
            if not os.path.exists(output_path):
                raise RuntimeError("Video file was not created")
            
            file_size = os.path.getsize(output_path)
            if file_size < 1000:  # Less than 1KB indicates error
                raise RuntimeError("Video file appears to be corrupted")
            
        except Exception as e:
            # Clean up partial file if it exists
            if os.path.exists(output_path):
                try:
                    os.remove(output_path)
                except:
                    pass
            raise RuntimeError(f"Failed to render video: {e}")
    
    def _handle_video_error(self, error: Exception):
        """Handle video creation errors"""
        error_msg = str(error).lower()
        
        if 'codec' in error_msg:
            raise RuntimeError("Video codec error. Please check MoviePy installation.")
        elif 'memory' in error_msg:
            raise RuntimeError("Insufficient memory for video processing.")
        elif 'permission' in error_msg:
            raise RuntimeError("Permission denied. Check output directory permissions.")
        elif 'disk' in error_msg or 'space' in error_msg:
            raise RuntimeError("Insufficient disk space for video creation.")
        else:
            raise RuntimeError(f"Video creation failed: {error}")
    
    def get_video_info(self, video_path: str) -> Dict[str, any]:
        """Get information about created video"""
        try:
            if not os.path.exists(video_path):
                return None
            
            clip = VideoFileClip(video_path)
            info = {
                'duration': clip.duration,
                'fps': clip.fps,
                'size': clip.size,
                'file_size': os.path.getsize(video_path),
                'has_audio': clip.audio is not None
            }
            clip.close()
            
            return info
            
        except Exception as e:
            print(f"Warning: Could not get video info: {e}")
            return None
    
    def cleanup_temp_files(self):
        """Clean up temporary files created during video processing"""
        try:
            # Clean up MoviePy temporary files
            temp_files = ['temp-audio.m4a', 'temp-audio.wav']
            
            for temp_file in temp_files:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            
            # Clean up any other temporary video files
            for filename in os.listdir('.'):
                if filename.startswith('TEMP_MPY_'):
                    try:
                        os.remove(filename)
                    except:
                        pass
            
            # Clean up temporary video files from temp directory
            try:
                if os.path.exists(self.config.temp_dir):
                    temp_video_files = [f for f in os.listdir(self.config.temp_dir) 
                                      if f.startswith('video_') and f.endswith(('.mp4', '.mov', '.avi'))]
                    
                    for filename in temp_video_files:
                        filepath = os.path.join(self.config.temp_dir, filename)
                        if os.path.exists(filepath):
                            os.remove(filepath)
            except Exception as e:
                print(f"Warning: Failed to cleanup temp video files: {e}")
                        
        except Exception as e:
            print(f"Warning: Failed to cleanup temp files: {e}")

def create_video_creator() -> VideoCreator:
    """Factory function to create VideoCreator instance"""
    config = Config()
    return VideoCreator(config)

# Example usage
if __name__ == "__main__":
    try:
        creator = create_video_creator()
        
        # Example image list (would come from ImageFetcher)
        images = [
            {'local_path': 'temp/image_1.jpg'},
            {'local_path': 'temp/image_2.jpg'},
            {'local_path': 'temp/image_3.jpg'}
        ]
        
        # Example audio path (would come from VoiceGenerator)
        audio_path = 'temp/voice_audio.wav'
        
        print("Creating video with images and audio...")
        
        # This would only run if the files exist
        if all(os.path.exists(img['local_path']) for img in images) and os.path.exists(audio_path):
            video_path = creator.create_video(images, audio_path)
            
            print(f"\n=== Video Created ===")
            print(f"Video file: {video_path}")
            
            # Get video info
            info = creator.get_video_info(video_path)
            if info:
                print(f"Duration: {info['duration']:.1f} seconds")
                print(f"Size: {info['size']}")
                print(f"File size: {info['file_size'] / 1024 / 1024:.1f} MB")
        else:
            print("Example files not found. Video creation skipped.")
        
    except Exception as e:
        print(f"Error: {e}")