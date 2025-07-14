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
from subtitle_generator import SubtitleGenerator
from youtube_uploader import YouTubeUploader
from thumbnail_generator import ThumbnailGenerator


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
            self.subtitle_generator = SubtitleGenerator(self.config)
            self.youtube_uploader = YouTubeUploader(self.config)
            self.thumbnail_generator = ThumbnailGenerator(self.config)
            
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
    
    def generate_video(self, theme: str, output_filename: str = None, skip_cleanup: bool = False, custom_script: str = None) -> Dict[str, Any]:
        """
        テーマから動画を生成する全工程を実行
        
        Args:
            theme: 動画のテーマ
            output_filename: 出力ファイル名（オプション）
            skip_cleanup: 一時ファイルのクリーンアップをスキップするかどうか
            custom_script: カスタムスクリプト（オプション）
            
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
            if custom_script:
                self._update_progress("スクリプト生成", 10, "カスタムスクリプトを使用中...")
                script_data = {
                    'title': theme,
                    'script': custom_script,
                    'keywords': [theme]  # テーマをキーワードとして使用
                }
                result['steps']['script_generation'] = {
                    'success': True,
                    'data': script_data,
                    'custom': True
                }
                self._update_progress("スクリプト生成", 25, f"カスタムスクリプト使用: {script_data['title']}")
            else:
                self._update_progress("スクリプト生成", 10, f"テーマ '{theme}' からスクリプトを生成中...")
                script_data = self.script_generator.generate_script(theme)
                result['steps']['script_generation'] = {
                    'success': True,
                    'data': script_data,
                    'custom': False
                }
                self._update_progress("スクリプト生成", 25, f"スクリプト生成完了: {script_data['title']}")
            
            # ステップ3: 画像取得
            self._update_progress("画像取得", 30, "関連画像を検索・ダウンロード中...")
            images = self.image_fetcher.fetch_images(script_data['keywords'], self.config.max_images)
            result['steps']['image_fetching'] = {
                'success': True,
                'count': len(images),
                'images': images  # 画像リストを結果に保存
            }
            self._update_progress("画像取得", 50, f"{len(images)}枚の画像をダウンロード完了")
            
            # ステップ4: 音声生成
            self._update_progress("音声生成", 55, "スクリプトから音声を生成中...")
            is_custom = result['steps']['script_generation']['custom']
            audio_path = self.voice_generator.generate_voice(script_data['script'], is_custom_script=is_custom)
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
            
            video_path = self.video_creator.create_video(images, audio_path, output_filename, is_custom_script=is_custom)
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
            
            # 一時ファイルの削除（オプション）
            if not skip_cleanup:
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
    
    def generate_video_with_subtitles(self, theme: str, output_filename: str = None, 
                                    upload_to_youtube: bool = False, 
                                    youtube_privacy: str = 'private', 
                                    custom_script: str = None, 
                                    youtube_title: str = None, 
                                    thumbnail_text: str = None) -> Dict[str, Any]:
        """
        字幕付き動画を生成し、オプションでYouTubeにアップロード
        
        Args:
            theme: 動画のテーマ
            output_filename: 出力ファイル名（オプション）
            upload_to_youtube: YouTubeにアップロードするかどうか
            youtube_privacy: YouTube動画のプライバシー設定
            custom_script: カスタムスクリプト（オプション）
            youtube_title: YouTube動画のカスタムタイトル（オプション）
            thumbnail_text: サムネイルに入れる文字（オプション）
            
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
            'subtitle_path': None,
            'youtube_url': None,
            'duration': 0,
            'steps': {},
            'errors': []
        }
        
        try:
            # ステップ1-5: 基本動画生成（既存のワークフロー、一時ファイルはクリーンアップしない）
            basic_result = self.generate_video(theme, output_filename, skip_cleanup=True, custom_script=custom_script)
            if not basic_result['success']:
                result['errors'].extend(basic_result['errors'])
                return result
            
            basic_video_path = basic_result['output_path']
            script_data = basic_result['steps']['script_generation']['data']
            
            # ステップ6: 字幕生成
            self._update_progress("字幕生成", 85, "字幕ファイルを生成中...")
            subtitle_path = self.subtitle_generator.generate_subtitles(
                script_data['script'], 
                basic_result['steps']['voice_generation']['audio_path']
            )
            result['steps']['subtitle_generation'] = {
                'success': True,
                'subtitle_path': subtitle_path
            }
            
            # ステップ7: 字幕付き動画作成
            self._update_progress("字幕埋め込み", 90, "動画に字幕を埋め込み中...")
            
            # 字幕付き動画の出力パスを設定
            if output_filename:
                base_name = os.path.splitext(output_filename)[0]
                subtitled_filename = f"{base_name}_with_subtitles.mp4"
            else:
                base_name = os.path.splitext(os.path.basename(basic_video_path))[0]
                subtitled_filename = f"{base_name}_with_subtitles.mp4"
            
            subtitled_video_path = self.subtitle_generator.add_subtitles_to_video(
                basic_video_path, 
                subtitle_path, 
                subtitled_filename
            )
            
            result['steps']['subtitle_embedding'] = {
                'success': True,
                'video_path': subtitled_video_path
            }
            
            # 基本動画と字幕付き動画の両方のパスを保存
            result['output_path'] = subtitled_video_path
            result['subtitle_path'] = subtitle_path
            result['basic_video_path'] = basic_video_path
            
            self._update_progress("字幕埋め込み", 95, "字幕付き動画作成完了")
            
            # ステップ8: YouTube アップロード（オプション）
            if upload_to_youtube:
                self._update_progress("YouTube投稿", 96, "YouTube認証中...")
                
                # YouTube認証
                if not self.youtube_uploader.authenticate():
                    result['errors'].append("YouTube認証に失敗しました")
                    result['youtube_url'] = None
                else:
                    # サムネイル生成（オプション）
                    thumbnail_path = None
                    if thumbnail_text:
                        self._update_progress("サムネイル生成", 96, "サムネイル画像を生成中...")
                        try:
                            # 最初の取得画像を背景として使用
                            background_image_url = None
                            images = basic_result['steps']['image_fetching'].get('images', [])
                            if images and len(images) > 0:
                                background_image_url = images[0]  # 最初の画像のURLを使用
                            
                            thumbnail_path = self.thumbnail_generator.generate_thumbnail(
                                text=thumbnail_text,
                                background_image_url=background_image_url
                            )
                            
                            if self.thumbnail_generator.validate_thumbnail(thumbnail_path):
                                print(f"サムネイル生成完了: {thumbnail_path}")
                            else:
                                print("サムネイル検証に失敗しました。サムネイルなしでアップロードします。")
                                thumbnail_path = None
                                
                        except Exception as e:
                            print(f"サムネイル生成中にエラーが発生しました: {e}")
                            print("サムネイルなしでアップロードします。")
                            thumbnail_path = None
                    
                    self._update_progress("YouTube投稿", 97, "YouTubeに動画をアップロード中...")
                    
                    # プログレスコールバック
                    def upload_progress(message):
                        self._update_progress("YouTube投稿", 98, message)
                    
                    youtube_url = self.youtube_uploader.upload_video(
                        subtitled_video_path,
                        theme,
                        script_data['script'],
                        youtube_privacy,
                        upload_progress,
                        youtube_title,
                        thumbnail_path
                    )
                    
                    result['steps']['youtube_upload'] = {
                        'success': youtube_url is not None,
                        'url': youtube_url,
                        'privacy': youtube_privacy
                    }
                    result['youtube_url'] = youtube_url
                    
                    if youtube_url:
                        self._update_progress("YouTube投稿", 99, "YouTube投稿完了")
                    else:
                        result['errors'].append("YouTube投稿に失敗しました")
            
            # 結果の設定
            result['success'] = True
            result['duration'] = time.time() - start_time
            
            # 一時ファイルの削除
            self._cleanup_temp_files()
            
            self._update_progress("完了", 100, "全ての処理が完了しました")
            
            return result
            
        except Exception as e:
            import traceback
            error_traceback = traceback.format_exc()
            error_msg = f"字幕付き動画生成中にエラーが発生しました: {e}"
            print(f"\n詳細なエラー情報:\n{error_traceback}")
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
            if hasattr(self, 'subtitle_generator'):
                self.subtitle_generator.cleanup_temp_files()
            if hasattr(self, 'thumbnail_generator'):
                self.thumbnail_generator.cleanup_temp_thumbnails()
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
  python main.py -t "AI技術" --with-subtitles  # 字幕付き動画生成
  python main.py -t "科学技術" --upload-youtube --youtube-privacy public  # YouTube投稿
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
            '--with-subtitles',
            action='store_true',
            help='字幕付き動画を生成'
        )
        
        parser.add_argument(
            '--upload-youtube',
            action='store_true',
            help='YouTubeにアップロード'
        )
        
        parser.add_argument(
            '--youtube-privacy',
            type=str,
            choices=['private', 'public', 'unlisted'],
            default='private',
            help='YouTube動画のプライバシー設定（デフォルト: private）'
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
            if args.with_subtitles:
                print("字幕付き動画を生成します")
            if args.upload_youtube:
                print(f"YouTubeにアップロードします（プライバシー: {args.youtube_privacy}）")
            print()
            
            # 字幕付き動画またはYouTubeアップロードが指定された場合
            if args.with_subtitles or args.upload_youtube:
                result = self.workflow.generate_video_with_subtitles(
                    args.theme, 
                    args.output,
                    args.upload_youtube,
                    args.youtube_privacy
                )
            else:
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
                
                # カスタムスクリプトオプションの確認
                custom_script_choice = input("スクリプトを自分で作成しますか？ (Y/n): ").strip().lower()
                custom_script = None
                if custom_script_choice not in ['n', 'no']:
                    print("スクリプトを入力してください（改行は改行、終了は空行を2回入力）:")
                    custom_script_lines = []
                    empty_line_count = 0
                    while True:
                        line = input()
                        if line == "":
                            empty_line_count += 1
                            if empty_line_count >= 2:
                                break
                            custom_script_lines.append(line)
                        else:
                            empty_line_count = 0
                            custom_script_lines.append(line)
                    custom_script = '\n'.join(custom_script_lines).strip()
                    if not custom_script:
                        print("スクリプトが入力されていません。AI生成スクリプトを使用します。")
                        custom_script = None
                
                # 字幕オプションの確認
                subtitle_choice = input("字幕付き動画を生成しますか？ (Y/n): ").strip().lower()
                with_subtitles = subtitle_choice not in ['n', 'no']
                
                # YouTubeアップロードオプションの確認
                youtube_choice = input("YouTubeにアップロードしますか？ (Y/n): ").strip().lower()
                upload_youtube = youtube_choice not in ['n', 'no']
                
                youtube_privacy = 'private'
                youtube_title = None
                if upload_youtube:
                    privacy_choice = input("プライバシー設定 (private/public/unlisted) [private]: ").strip().lower()
                    if privacy_choice in ['public', 'unlisted']:
                        youtube_privacy = privacy_choice
                    
                    # カスタムタイトル入力
                    title_choice = input("YouTubeのタイトルを自分で設定しますか？ (Y/n): ").strip().lower()
                    if title_choice not in ['n', 'no']:
                        youtube_title = input("YouTubeのタイトルを入力してください: ").strip()
                        if not youtube_title:
                            print("タイトルが入力されていません。自動生成タイトルを使用します。")
                            youtube_title = None
                    
                    # サムネイル文字入力
                    thumbnail_text = None
                    thumbnail_choice = input("サムネイルに文字を入れますか？ (Y/n): ").strip().lower()
                    if thumbnail_choice not in ['n', 'no']:
                        while True:
                            thumbnail_text = input("サムネイルに入れる文字を入力してください（14文字以内）: ").strip()
                            if not thumbnail_text:
                                print("文字が入力されていません。サムネイル文字なしで生成します。")
                                thumbnail_text = None
                                break
                            elif len(thumbnail_text) > 14:
                                print(f"文字数が制限を超えています（{len(thumbnail_text)}文字）。14文字以内で入力してください。")
                            else:
                                break
                
                print()
                
                try:
                    # 動画生成実行
                    if with_subtitles or upload_youtube:
                        result = self.workflow.generate_video_with_subtitles(
                            theme, output_file, upload_youtube, youtube_privacy, custom_script, youtube_title, thumbnail_text
                        )
                    else:
                        result = self.workflow.generate_video(theme, output_file, custom_script=custom_script)
                    
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
            
            # 字幕ファイルの情報
            if 'subtitle_path' in result and result['subtitle_path']:
                print(f"📝 字幕ファイル: {result['subtitle_path']}")
            
            # 基本動画パス（字幕なし）の情報
            if 'basic_video_path' in result and result['basic_video_path']:
                print(f"📁 基本動画ファイル: {result['basic_video_path']}")
            
            # YouTube URL
            if 'youtube_url' in result and result['youtube_url']:
                print(f"🎬 YouTube URL: {result['youtube_url']}")
                if 'steps' in result and 'youtube_upload' in result['steps']:
                    privacy = result['steps']['youtube_upload'].get('privacy', 'private')
                    print(f"🔒 プライバシー設定: {privacy}")
            
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