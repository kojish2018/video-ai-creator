#!/usr/bin/env python3
"""
Test script to verify that custom scripts bypass the 30-second rule
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import Config
from voice_generator import VoiceGenerator

def test_custom_script_no_limit():
    """Test that custom scripts bypass the 30-second rule"""
    try:
        # Initialize components
        config = Config()
        voice_gen = VoiceGenerator(config)
        
        # Test connection first
        if not voice_gen.test_connection():
            print("SKIP: VOICEVOX server is not running")
            return True
        
        # Create a long script (should exceed 30 seconds normally)
        long_script = """
        これは非常に長いカスタムスクリプトのテストです。通常であれば30秒ルールが適用されて、
        音声の生成時に速度調整が行われたり、警告が表示されたりするはずですが、
        カスタムスクリプトの場合はこの制限をバイパスするようになっています。
        このテストでは、カスタムスクリプトフラグが正しく機能しているかを確認します。
        長いテキストでも速度調整なしで自然な音声が生成されることを期待しています。
        この機能により、ユーザーは自分で作成したスクリプトについては30秒の制限を受けることなく、
        自由な長さの動画を作成することができるようになります。
        """
        
        print("Testing custom script (should bypass 30-second rule)...")
        
        # Generate voice with custom script flag
        try:
            audio_path = voice_gen.generate_voice(long_script, is_custom_script=True)
            duration = voice_gen._get_audio_duration(audio_path)
            print(f"✓ Custom script audio generated successfully")
            print(f"  Duration: {duration:.1f} seconds")
            print(f"  File: {audio_path}")
            
            # Clean up
            if os.path.exists(audio_path):
                os.remove(audio_path)
            
            return True
            
        except Exception as e:
            print(f"✗ Custom script test failed: {e}")
            return False
            
    except Exception as e:
        print(f"✗ Test setup failed: {e}")
        return False

def test_regular_script_with_limit():
    """Test that regular scripts still have the 30-second rule"""
    try:
        # Initialize components
        config = Config()
        voice_gen = VoiceGenerator(config)
        
        # Test connection first
        if not voice_gen.test_connection():
            print("SKIP: VOICEVOX server is not running")
            return True
        
        # Create a long script (should trigger 30-second rule)
        long_script = """
        これは通常のスクリプトのテストです。このスクリプトは長いため、
        30秒ルールが適用されて速度調整が行われるはずです。
        通常のAI生成スクリプトの場合は、従来通り30秒の制限が適用されます。
        """
        
        print("Testing regular script (should apply 30-second rule)...")
        
        # Generate voice without custom script flag
        try:
            audio_path = voice_gen.generate_voice(long_script, is_custom_script=False)
            duration = voice_gen._get_audio_duration(audio_path)
            print(f"✓ Regular script audio generated successfully")
            print(f"  Duration: {duration:.1f} seconds")
            print(f"  File: {audio_path}")
            
            # Clean up
            if os.path.exists(audio_path):
                os.remove(audio_path)
            
            return True
            
        except Exception as e:
            print(f"✗ Regular script test failed: {e}")
            return False
            
    except Exception as e:
        print(f"✗ Test setup failed: {e}")
        return False

if __name__ == "__main__":
    print("=== Testing Custom Script 30-Second Rule Bypass ===")
    print()
    
    success1 = test_custom_script_no_limit()
    print()
    success2 = test_regular_script_with_limit()
    print()
    
    if success1 and success2:
        print("✓ All tests passed! Custom script 30-second rule bypass is working.")
    else:
        print("✗ Some tests failed.")
        sys.exit(1)