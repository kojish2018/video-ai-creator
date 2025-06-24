#!/usr/bin/env python3
"""
自動動画生成システム - メイン実行ファイル

テーマを入力すると、AIが自動で30秒動画を生成します。
- スクリプト生成（Gemini API）
- 画像取得（Unsplash API）  
- 音声生成（VOICEVOX）
- 動画作成（MoviePy）
"""

import os
import sys
import argparse
import time
from typing import Optional, Dict, Any
from datetime import datetime

# 自作モジュールのインポート
from config import Config
from script_generator import ScriptGenerator
from image_fetcher import ImageFetcher
from voice_generator import VoiceGenerator
from video_creator import VideoCreator


class VideoWorkflow:
    """動画生成ワークフローを制御するクラス"""
    
    def __init__(self, config: Config = None):
        self.config = config or Config()
        self._initialize_components()
        self.progress_callback = None
        
    def _initialize_components(self):
        """各コンポーネントを初期化"""
        try:
            self.script_generator = ScriptGenerator(self.config)
            self.image_fetcher = ImageFetcher(self.config)
            self.voice_generator = VoiceGenerator(self.config)
            self.video_creator = VideoCreator(self.config)
            
        except Exception as e:
            raise RuntimeError(f"コンポーネントの初期化に失敗しました: {e}")
    
    def set_progress_callback(self, callback):
        """進行状況コールバック関数を設定"""
        self.progress_callback = callback
    
    def _update_progress(self, step: str, progress: int, message: str = ""):
        """進行状況を更新"""
        if self.progress_callback:
            self.progress_callback(step, progress, message)
        else:
            print(f"[{progress:3d}%] {step}: {message}")
    
    def generate_video(self, theme: str, output_filename: str = None) -> Dict[str, Any]:
        """
        テーマから動画を生成する全工程を実行
        
        Args:
            theme: 動画のテーマ
            output_filename: 出力ファイル名（オプション）
            
        Returns:
            生成結果の辞書
        """
        if not theme or not theme.strip():
            raise ValueError("テーマが指定されていません")
        
        start_time = time.time()
        result = {
            'theme': theme,
            'success': False,
            'output_path': None,
            'duration': 0,
            'steps': {},
            'errors': []
        }
        
        try:
            # ステップ1: 設定検証
            self._update_progress("設定検証", 0, "API設定を確認中...")
            self.config.validate()
            result['steps']['config_validation'] = {'success': True}
            
            # ステップ2: スクリプト生成
            self._update_progress("スクリプト生成", 10, f"テーマ '{theme}' からスクリプトを生成中...")
            script_data = self.script_generator.generate_script(theme)
            result['steps']['script_generation'] = {
                'success': True,
                'data': script_data
            }
            self._update_progress("スクリプト生成", 25, f"スクリプト生成完了: {script_data['title']}")
            
            # ステップ3: 画像取得
            self._update_progress("画像取得", 30, "関連画像を検索・ダウンロード中...")
            images = self.image_fetcher.fetch_images(script_data['keywords'], self.config.max_images)
            result['steps']['image_fetching'] = {
                'success': True,
                'count': len(images)
            }
            self._update_progress("画像取得", 50, f"{len(images)}枚の画像をダウンロード完了")
            
            # ステップ4: 音声生成
            self._update_progress("音声生成", 55, "スクリプトから音声を生成中...")
            audio_path = self.voice_generator.generate_voice(script_data['script'])
            result['steps']['voice_generation'] = {
                'success': True,
                'audio_path': audio_path
            }
            self._update_progress("音声生成", 75, "音声生成完了")
            
            # ステップ5: 動画作成
            self._update_progress("動画作成", 80, "画像と音声を結合して動画を作成中...")
            
            if output_filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                clean_theme = "".join(c for c in theme if c.isalnum() or c in "- _")[:20]
                output_filename = f"{clean_theme}_{timestamp}.mp4"
            
            video_path = self.video_creator.create_video(images, audio_path, output_filename)
            result['steps']['video_creation'] = {
                'success': True,
                'video_path': video_path
            }
            self._update_progress("動画作成", 95, "動画作成完了")
            
            # ステップ6: 後処理・検証
            self._update_progress("完了処理", 98, "生成結果を検証中...")
            video_info = self.video_creator.get_video_info(video_path)
            
            # 結果の設定
            result['success'] = True
            result['output_path'] = video_path
            result['video_info'] = video_info
            result['duration'] = time.time() - start_time
            
            # 一時ファイルの削除
            self._cleanup_temp_files()
            
            self._update_progress("完了", 100, f"動画生成完了: {os.path.basename(video_path)}")
            
            return result
            
        except Exception as e:
            error_msg = f"動画生成中にエラーが発生しました: {e}"
            result['errors'].append(error_msg)
            result['duration'] = time.time() - start_time
            
            # エラー時も一時ファイルを削除
            self._cleanup_temp_files()
            
            raise RuntimeError(error_msg)
    
    def _cleanup_temp_files(self):
        """一時ファイルをクリーンアップ"""
        try:
            self.image_fetcher.cleanup_temp_images()
            self.voice_generator.cleanup_temp_audio()
            self.video_creator.cleanup_temp_files()
        except Exception as e:
            print(f"警告: 一時ファイルの削除中にエラーが発生しました: {e}")


class CLIInterface:
    """コマンドライン インターフェース"""
    
    def __init__(self):
        self.workflow = None
        
    def run(self):
        """メイン実行関数"""
        try:
            # コマンドライン引数の解析
            args = self._parse_arguments()
            
            # 設定の初期化
            config = Config()
            self.workflow = VideoWorkflow(config)
            self.workflow.set_progress_callback(self._progress_callback)
            
            # バナー表示
            self._print_banner()
            
            # 対話モードまたは引数モードで実行
            if args.theme:
                self._run_with_args(args)
            else:
                self._run_interactive_mode()
                
        except KeyboardInterrupt:
            print("\n\n処理が中断されました。")
            sys.exit(1)
        except Exception as e:
            print(f"\nエラー: {e}")
            sys.exit(1)
    
    def _parse_arguments(self) -> argparse.Namespace:
        """コマンドライン引数を解析"""
        parser = argparse.ArgumentParser(
            description="AI自動動画生成システム",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
使用例:
  python main.py                           # 対話モード
  python main.py -t "人工知能の未来"       # テーマ指定モード
  python main.py --theme "宇宙探査" -o "space_video.mp4"  # 出力ファイル名指定
            """
        )
        
        parser.add_argument(
            '-t', '--theme',
            type=str,
            help='動画のテーマ'
        )
        
        parser.add_argument(
            '-o', '--output',
            type=str,
            help='出力動画ファイル名'
        )
        
        parser.add_argument(
            '--test-config',
            action='store_true',
            help='設定をテストして終了'
        )
        
        return parser.parse_args()
    
    def _print_banner(self):
        """バナーを表示"""
        print("=" * 60)
        print("   🎬 AI自動動画生成システム")
        print("   30秒動画を自動生成します")
        print("=" * 60)
        print()
    
    def _run_with_args(self, args):
        """引数モードで実行"""
        try:
            if args.test_config:
                self._test_configuration()
                return
            
            print(f"テーマ: {args.theme}")
            if args.output:
                print(f"出力ファイル名: {args.output}")
            print()
            
            result = self.workflow.generate_video(args.theme, args.output)
            self._print_result(result)
            
        except Exception as e:
            print(f"エラー: {e}")
            sys.exit(1)
    
    def _run_interactive_mode(self):
        """対話モードで実行"""
        try:
            print("対話モードで動画を生成します。")
            print("設定をテスト中...")
            
            # 設定テスト
            try:
                self.workflow.config.validate()
                print("✅ 設定確認完了")
            except Exception as e:
                print(f"❌ 設定エラー: {e}")
                print("\nAPI_SETUP.mdを参照して設定を確認してください。")
                return
            
            print()
            
            while True:
                # テーマ入力
                theme = input("動画のテーマを入力してください（終了するには 'quit' または 'exit'）: ").strip()
                
                if theme.lower() in ['quit', 'exit', 'q']:
                    print("終了します。")
                    break
                
                if not theme:
                    print("テーマを入力してください。")
                    continue
                
                # 出力ファイル名の確認
                output_file = input("出力ファイル名（空白で自動生成）: ").strip()
                if not output_file:
                    output_file = None
                
                print()
                
                try:
                    # 動画生成実行
                    result = self.workflow.generate_video(theme, output_file)
                    self._print_result(result)
                    
                    # 継続確認
                    print()
                    continue_prompt = input("別の動画を生成しますか？ (y/N): ").strip().lower()
                    if continue_prompt not in ['y', 'yes']:
                        break
                    
                    print("-" * 60)
                    
                except Exception as e:
                    print(f"❌ エラー: {e}")
                    print()
                    continue_prompt = input("別のテーマで再試行しますか？ (y/N): ").strip().lower()
                    if continue_prompt not in ['y', 'yes']:
                        break
                    print()
                    
        except KeyboardInterrupt:
            print("\n\n処理が中断されました。")
    
    def _test_configuration(self):
        """設定をテスト"""
        print("設定をテスト中...")
        try:
            config = Config()
            config.validate()
            
            print("✅ 基本設定: OK")
            
            # VOICEVOX接続テスト
            voice_gen = VoiceGenerator(config)
            if voice_gen.test_connection():
                print("✅ VOICEVOX接続: OK")
            else:
                print("❌ VOICEVOX接続: 失敗")
            
            print("\n設定テスト完了")
            
        except Exception as e:
            print(f"❌ 設定エラー: {e}")
            sys.exit(1)
    
    def _progress_callback(self, step: str, progress: int, message: str = ""):
        """進行状況表示コールバック"""
        # プログレスバーの表示
        bar_length = 40
        filled_length = int(bar_length * progress // 100)
        bar = '█' * filled_length + '-' * (bar_length - filled_length)
        
        print(f'\r{step}: [{bar}] {progress:3d}% {message}', end='', flush=True)
        
        if progress >= 100:
            print()  # 改行
    
    def _print_result(self, result: Dict[str, Any]):
        """結果を表示"""
        print()
        print("=" * 60)
        
        if result['success']:
            print("🎉 動画生成完了！")
            print(f"📁 出力ファイル: {result['output_path']}")
            
            if 'video_info' in result and result['video_info']:
                info = result['video_info']
                print(f"⏱️  動画時間: {info['duration']:.1f}秒")
                print(f"📏 解像度: {info['size'][0]}x{info['size'][1]}")
                print(f"💾 ファイルサイズ: {info['file_size'] / 1024 / 1024:.1f}MB")
            
            print(f"🕒 処理時間: {result['duration']:.1f}秒")
            
        else:
            print("❌ 動画生成に失敗しました")
            if result['errors']:
                for error in result['errors']:
                    print(f"   エラー: {error}")
        
        print("=" * 60)


def main():
    """メイン関数"""
    cli = CLIInterface()
    cli.run()


if __name__ == "__main__":
    main()