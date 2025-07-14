#!/usr/bin/env python3
"""
動画取得モジュール

Pexels APIを使用してテーマに基づいた動画を取得します。
"""

import os
import requests
import time
from typing import List, Dict, Optional
from urllib.parse import urlparse
from config import Config

class VideoFetcher:
    """Pexels APIを使用して動画を取得するクラス"""
    
    def __init__(self, config: Config):
        self.config = config
        self.base_url = "https://api.pexels.com"
        self.headers = {
            "Authorization": config.pexels_api_key,
            "User-Agent": "AutoYoutube/1.0"
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
    def fetch_videos(self, keywords: str, count: int = None) -> List[Dict[str, str]]:
        """
        キーワードに基づいて動画を取得
        
        Args:
            keywords: 動画検索用のキーワード（カンマ区切りまたはリスト）
            count: 取得する動画数（設定のデフォルト値を使用）
            
        Returns:
            動画情報の辞書リスト
        """
        if count is None:
            count = min(self.config.max_videos, max(self.config.min_videos, 2))
        
        try:
            search_terms = self._process_keywords(keywords)
            videos = []
            
            for term in search_terms:
                if len(videos) >= count:
                    break
                    
                term_videos = self._search_videos(term, count - len(videos))
                videos.extend(term_videos)
                
                # Rate limiting - Pexels API制限に配慮
                time.sleep(0.2)
            
            # 十分な動画が取得できない場合のフォールバック
            if len(videos) < self.config.min_videos:
                fallback_videos = self._search_videos("nature landscape", count)
                videos.extend(fallback_videos[:count - len(videos)])
            
            return self._download_and_validate_videos(videos[:count])
            
        except Exception as e:
            self._handle_fetch_error(e)
    
    def _process_keywords(self, keywords) -> List[str]:
        """検索用キーワードを処理・クリーニング"""
        if not keywords:
            return ["nature", "landscape"]
        
        # 文字列とリストの両方を処理
        if isinstance(keywords, list):
            terms = [str(term).strip() for term in keywords]
        else:
            # カンマ区切りで分割してクリーニング
            terms = [term.strip() for term in str(keywords).split(',')]
        
        # 空の要素と重複を除去
        terms = list(set([term for term in terms if term]))
        
        # 最低1つの検索語を保証
        if not terms:
            terms = ["nature", "landscape"]
        
        return terms[:3]  # API呼び出し数を制限するため3つまで
    
    def _search_videos(self, query: str, per_page: int) -> List[Dict[str, str]]:
        """Pexels APIで動画を検索"""
        try:
            params = {
                'query': query,
                'per_page': min(per_page, 10),  # Pexels API制限
                'orientation': 'landscape',
                'size': 'medium',  # medium, large, small
                'locale': 'en-US'
            }
            
            response = self.session.get(
                f"{self.base_url}/videos/search",
                params=params,
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                return self._extract_video_info(data)
            elif response.status_code == 403:
                raise RuntimeError("Pexels API access denied. Check your API key.")
            elif response.status_code == 429:
                raise RuntimeError("Pexels API rate limit exceeded. Please try again later.")
            else:
                raise RuntimeError(f"Pexels API error: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Network error while searching videos: {e}")
    
    def _extract_video_info(self, data: Dict) -> List[Dict[str, str]]:
        """API レスポンスから動画情報を抽出"""
        videos = []
        
        for video in data.get('videos', []):
            if 'video_files' in video and video['video_files']:
                # 最適な品質の動画ファイルを選択
                best_video = self._select_best_video_quality(video['video_files'])
                
                if best_video:
                    video_info = {
                        'id': str(video.get('id', '')),
                        'url': video.get('url', ''),
                        'download_url': best_video['link'],
                        'duration': video.get('duration', 0),
                        'width': video.get('width', 0),
                        'height': video.get('height', 0),
                        'quality': best_video.get('quality', 'unknown'),
                        'file_type': best_video.get('file_type', 'mp4'),
                        'photographer': video.get('user', {}).get('name', 'Unknown')
                    }
                    videos.append(video_info)
        
        return videos
    
    def _select_best_video_quality(self, video_files: List[Dict]) -> Optional[Dict]:
        """最適な品質の動画ファイルを選択"""
        # 品質の優先順位 (HD → SD → その他)
        quality_priority = ['hd', 'sd', 'hls']
        
        for quality in quality_priority:
            for video_file in video_files:
                if video_file.get('quality') == quality:
                    return video_file
        
        # フォールバック: 最初の利用可能な動画ファイル
        return video_files[0] if video_files else None
    
    def _download_and_validate_videos(self, video_list: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """動画をダウンロードして品質を検証"""
        downloaded_videos = []
        
        for i, video_info in enumerate(video_list):
            try:
                filename = f"video_{i+1}_{video_info['id']}.mp4"
                filepath = os.path.join(self.config.temp_dir, filename)
                
                # 動画をダウンロード
                if self._download_video(video_info['download_url'], filepath):
                    # 動画を検証
                    if self._validate_video(filepath, video_info):
                        video_info['local_path'] = filepath
                        video_info['filename'] = filename
                        downloaded_videos.append(video_info)
                    else:
                        # 無効な動画ファイルを削除
                        if os.path.exists(filepath):
                            os.remove(filepath)
                
            except Exception as e:
                print(f"Warning: Failed to download video {i+1}: {e}")
                continue
        
        if len(downloaded_videos) == 0:
            raise RuntimeError("No valid videos could be downloaded")
        
        return downloaded_videos
    
    def _download_video(self, url: str, filepath: str) -> bool:
        """単一の動画をダウンロード"""
        try:
            response = requests.get(url, stream=True, timeout=60)
            response.raise_for_status()
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            return True
            
        except Exception as e:
            print(f"Failed to download video from {url}: {e}")
            return False
    
    def _validate_video(self, filepath: str, video_info: Dict) -> bool:
        """ダウンロードした動画の品質と形式を検証"""
        try:
            # ファイルサイズチェック
            file_size = os.path.getsize(filepath)
            if file_size < 100000:  # 100KB minimum
                return False
            
            # 最大ファイルサイズチェック (100MB)
            if file_size > 100 * 1024 * 1024:
                return False
            
            # 動画情報の基本チェック
            duration = video_info.get('duration', 0)
            width = video_info.get('width', 0)
            height = video_info.get('height', 0)
            
            # 最小解像度チェック
            if width < 640 or height < 360:
                return False
            
            # 時間チェック (5秒〜120秒)
            if duration < 5 or duration > 120:
                return False
            
            # ファイル拡張子チェック
            if not filepath.lower().endswith(('.mp4', '.mov', '.avi')):
                return False
            
            return True
            
        except Exception:
            return False
    
    def _handle_fetch_error(self, error: Exception):
        """動画取得エラーの処理"""
        error_msg = str(error).lower()
        
        if 'api key' in error_msg or 'authorization' in error_msg:
            raise RuntimeError("Invalid Pexels API key. Please check your configuration.")
        elif 'rate limit' in error_msg:
            raise RuntimeError("Pexels API rate limit exceeded. Please try again later.")
        elif 'network' in error_msg or 'connection' in error_msg:
            raise RuntimeError("Network error. Please check your internet connection.")
        else:
            raise RuntimeError(f"Video fetching failed: {error}")
    
    def cleanup_temp_videos(self):
        """一時動画ファイルをクリーンアップ"""
        try:
            temp_files = [f for f in os.listdir(self.config.temp_dir) 
                         if f.startswith('video_') and f.endswith(('.mp4', '.mov', '.avi'))]
            
            for filename in temp_files:
                filepath = os.path.join(self.config.temp_dir, filename)
                if os.path.exists(filepath):
                    os.remove(filepath)
                    
        except Exception as e:
            print(f"Warning: Failed to cleanup temp videos: {e}")

def create_video_fetcher() -> VideoFetcher:
    """ファクトリー関数でVideoFetcherインスタンスを作成"""
    config = Config()
    return VideoFetcher(config)

# 使用例
if __name__ == "__main__":
    try:
        fetcher = create_video_fetcher()
        
        # 動画取得テスト
        keywords = "technology, artificial intelligence, future"
        print(f"Fetching videos for: {keywords}")
        
        videos = fetcher.fetch_videos(keywords, 2)
        
        print(f"\n=== Downloaded {len(videos)} videos ===")
        for i, video in enumerate(videos):
            print(f"{i+1}. {video['filename']} - Duration: {video['duration']}s")
            print(f"   Size: {video['width']}x{video['height']}, Quality: {video['quality']}")
            print(f"   Photographer: {video['photographer']}")
        
    except Exception as e:
        print(f"Error: {e}")