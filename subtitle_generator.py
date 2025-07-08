import os
import subprocess
import re
from typing import List, Tuple, Optional
from config import Config

class SubtitleGenerator:
    def __init__(self, config: Config):
        self.config = config
        self.font_path = self._get_japanese_font_path()
    
    def _get_japanese_font_path(self) -> str:
        """日本語フォントのパスを取得"""
        font_candidates = [
            "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
            "/System/Library/Fonts/Hiragino Sans GB.ttc",
            "/System/Library/Fonts/Arial Unicode.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        ]
        
        for font_path in font_candidates:
            if os.path.exists(font_path):
                return font_path
        
        # デフォルトフォントを使用
        return "/System/Library/Fonts/Arial.ttf"
    
    def create_srt_file(self, script_text: str, audio_duration: float, output_path: str) -> str:
        """スクリプトテキストから.srtファイルを生成"""
        try:
            # テキストを文章単位に分割
            sentences = self._split_text_into_sentences(script_text)
            
            # 各文章のタイミングを計算
            subtitle_entries = self._calculate_subtitle_timing(sentences, audio_duration)
            
            # SRTファイルを生成
            srt_content = self._generate_srt_content(subtitle_entries)
            
            # ファイルに保存
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(srt_content)
            
            return output_path
            
        except Exception as e:
            raise Exception(f"SRTファイル生成エラー: {str(e)}")
    
    def _split_text_into_sentences(self, text: str) -> List[str]:
        """テキストを文章単位に分割"""
        # 改行で分割し、空の行を除去
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        sentences = []
        for line in lines:
            # 文章を句読点で分割（簡易版）
            parts = re.split(r'[。！？]', line)
            for part in parts:
                if part.strip():
                    sentences.append(part.strip() + ('。' if not part.endswith(('！', '？')) else ''))
        
        return [s for s in sentences if len(s) > 1]
    
    def _calculate_subtitle_timing(self, sentences: List[str], total_duration: float) -> List[Tuple[float, float, str]]:
        """字幕のタイミングを計算"""
        if not sentences:
            return []
        
        # 各文章の長さに基づいて時間を配分
        total_chars = sum(len(sentence) for sentence in sentences)
        
        subtitle_entries = []
        current_time = 0.0
        
        for sentence in sentences:
            # 文章の長さに比例して時間を配分
            sentence_duration = (len(sentence) / total_chars) * total_duration
            
            # 最小表示時間を確保（1秒）
            sentence_duration = max(sentence_duration, 1.0)
            
            start_time = current_time
            end_time = min(current_time + sentence_duration, total_duration)
            
            subtitle_entries.append((start_time, end_time, sentence))
            current_time = end_time
            
            if current_time >= total_duration:
                break
        
        return subtitle_entries
    
    def _generate_srt_content(self, subtitle_entries: List[Tuple[float, float, str]]) -> str:
        """SRTファイルの内容を生成"""
        srt_content = ""
        
        for i, (start_time, end_time, text) in enumerate(subtitle_entries, 1):
            start_timestamp = self._seconds_to_srt_timestamp(start_time)
            end_timestamp = self._seconds_to_srt_timestamp(end_time)
            
            srt_content += f"{i}\n"
            srt_content += f"{start_timestamp} --> {end_timestamp}\n"
            srt_content += f"{text}\n\n"
        
        return srt_content
    
    def _seconds_to_srt_timestamp(self, seconds: float) -> str:
        """秒をSRTタイムスタンプ形式に変換"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        milliseconds = int((seconds % 1) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"
    
    def add_subtitles_to_video(self, video_path: str, subtitle_path: str, output_filename: str) -> str:
        """FFmpegを使用して動画に字幕を追加"""
        try:
            # 入力ファイルの存在確認
            if not os.path.exists(video_path):
                raise Exception(f"動画ファイルが見つかりません: {video_path}")
            if not os.path.exists(subtitle_path):
                raise Exception(f"字幕ファイルが見つかりません: {subtitle_path}")
            
            # 出力パスを絶対パスに変換
            if not os.path.isabs(output_filename):
                # 動画ファイルと同じディレクトリに出力
                output_dir = os.path.dirname(video_path)
                output_path = os.path.join(output_dir, output_filename)
            else:
                output_path = output_filename
            
            # 出力ディレクトリを作成
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # FFmpegコマンドを構築（字幕ファイルのパスをエスケープ）
            escaped_subtitle_path = subtitle_path.replace(':', '\\:')
            subtitle_filter = f"subtitles='{escaped_subtitle_path}':force_style='FontName=Hiragino Sans,FontSize=24,PrimaryColour=&Hffffff,OutlineColour=&H000000,Outline=2,Shadow=1'"
            
            cmd = [
                'ffmpeg',
                '-i', video_path,
                '-vf', subtitle_filter,
                '-c:a', 'copy',
                '-y',  # 既存ファイルを上書き
                output_path
            ]
            
            print(f"FFmpegコマンド実行中: {' '.join(cmd)}")
            
            # FFmpegを実行
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise Exception(f"FFmpeg実行エラー: {result.stderr}")
            
            # 出力ファイルの存在確認
            if not os.path.exists(output_path):
                raise Exception(f"字幕付き動画の生成に失敗しました: {output_path}")
            
            return output_path
            
        except FileNotFoundError:
            raise Exception("FFmpegが見つかりません。FFmpegをインストールしてください。")
        except Exception as e:
            raise Exception(f"字幕追加エラー: {str(e)}")
    
    def generate_subtitled_video(self, video_path: str, script_text: str, audio_duration: float, output_dir: str) -> str:
        """字幕付き動画を生成（メイン処理）"""
        try:
            # 出力ディレクトリを作成
            os.makedirs(output_dir, exist_ok=True)
            
            # SRTファイルのパス
            srt_filename = os.path.basename(video_path).replace('.mp4', '.srt')
            srt_path = os.path.join(output_dir, srt_filename)
            
            # 字幕付き動画のパス
            subtitled_filename = os.path.basename(video_path).replace('.mp4', '_subtitled.mp4')
            subtitled_path = os.path.join(output_dir, subtitled_filename)
            
            # SRTファイルを生成
            self.create_srt_file(script_text, audio_duration, srt_path)
            
            # 動画に字幕を追加
            self.add_subtitles_to_video(video_path, srt_path, subtitled_path)
            
            return subtitled_path
            
        except Exception as e:
            raise Exception(f"字幕付き動画生成エラー: {str(e)}")
    
    def check_ffmpeg_available(self) -> bool:
        """FFmpegが利用可能かチェック"""
        try:
            subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def generate_subtitles(self, script_text: str, audio_path: str, output_dir: str = "output/subtitles") -> str:
        """字幕ファイルを生成"""
        try:
            # 音声ファイルのパスを絶対パスに変換
            audio_path = os.path.abspath(audio_path)
            
            # 音声ファイルの存在確認
            print(f"デバッグ: 音声ファイルパス確認中 - 元のパス: {audio_path}")
            print(f"デバッグ: 絶対パス変換後: {os.path.abspath(audio_path)}")
            
            if not os.path.exists(audio_path):
                # ファイルが見つからない場合、現在のディレクトリを確認
                current_dir = os.getcwd()
                print(f"エラー詳細: 現在のディレクトリ: {current_dir}")
                print(f"エラー詳細: 探しているファイル: {audio_path}")
                
                # tempディレクトリの中身を確認
                temp_dir = os.path.join(current_dir, "temp")
                if os.path.exists(temp_dir):
                    print(f"エラー詳細: tempディレクトリの中身: {os.listdir(temp_dir)}")
                else:
                    print(f"エラー詳細: tempディレクトリが存在しません: {temp_dir}")
                
                # 他の可能性のあるディレクトリもチェック
                for root, dirs, files in os.walk(current_dir):
                    if any(f.endswith('.wav') for f in files):
                        print(f"エラー詳細: .wavファイルが見つかったディレクトリ: {root}")
                        wav_files = [f for f in files if f.endswith('.wav')]
                        print(f"エラー詳細: .wavファイル一覧: {wav_files}")
                        break
                
                raise Exception(f"音声ファイルが見つかりません: {audio_path}")
            
            print(f"デバッグ: 音声ファイルが見つかりました: {audio_path}")
            
            # 音声ファイルの長さを取得
            import subprocess
            import json
            
            # ffprobeで音声の長さを取得
            cmd = [
                'ffprobe', '-v', 'quiet', '-print_format', 'json', 
                '-show_format', audio_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                # ffprobeが失敗した場合、デフォルト値を使用
                print(f"警告: ffprobeが失敗しました。デフォルトの30秒を使用します。エラー: {result.stderr}")
                audio_duration = 30.0  # デフォルト30秒
            else:
                try:
                    audio_info = json.loads(result.stdout)
                    audio_duration = float(audio_info['format']['duration'])
                except (json.JSONDecodeError, KeyError, ValueError) as e:
                    print(f"警告: 音声情報の解析に失敗しました。デフォルトの30秒を使用します。エラー: {e}")
                    audio_duration = 30.0  # デフォルト30秒
            
            # 出力ディレクトリを作成
            os.makedirs(output_dir, exist_ok=True)
            
            # SRTファイルのパス
            srt_filename = f"subtitles_{int(audio_duration)}s.srt"
            srt_path = os.path.join(output_dir, srt_filename)
            
            # SRTファイルを生成
            self.create_srt_file(script_text, audio_duration, srt_path)
            
            return srt_path
            
        except Exception as e:
            import traceback
            error_traceback = traceback.format_exc()
            print(f"字幕生成エラーの詳細トレースバック:\n{error_traceback}")
            raise Exception(f"字幕生成エラー: {str(e)}")
    
    def cleanup_temp_files(self):
        """一時ファイルをクリーンアップ"""
        # 現在は特別な一時ファイルは作成していないため、何もしない
        # 将来的に一時ファイルを作成する場合はここで削除処理を追加
        pass