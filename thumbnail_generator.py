#!/usr/bin/env python3
"""
サムネイル画像生成モジュール

指定されたテキストを含むYouTube用サムネイル画像を生成します。
"""

import os
import sys
from typing import Optional, Tuple
from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO
from config import Config


class ThumbnailGenerator:
    """YouTubeサムネイル画像生成クラス"""
    
    # YouTubeサムネイルの推奨サイズ
    THUMBNAIL_SIZE = (1280, 720)  # 16:9 アスペクト比
    
    def __init__(self, config: Config):
        """サムネイル生成器を初期化"""
        self.config = config
        self.temp_dir = self.config.temp_dir
        
        # 一時ディレクトリを作成
        os.makedirs(self.temp_dir, exist_ok=True)
    
    def generate_thumbnail(self, text: str = "", background_image_url: str = None, 
                         output_filename: str = None) -> str:
        """
        サムネイル画像を生成
        
        Args:
            text: サムネイルに表示するテキスト（14文字以内推奨）
            background_image_url: 背景画像のURL（オプション）
            output_filename: 出力ファイル名（オプション）
            
        Returns:
            生成されたサムネイル画像のパス
        """
        if not text:
            text = ""
        
        # 出力ファイル名を決定
        if output_filename is None:
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"thumbnail_{timestamp}.jpg"
        
        output_path = os.path.join(self.temp_dir, output_filename)
        
        try:
            # 背景画像を準備
            background = self._create_background(background_image_url)
            
            # テキストを描画
            if text:
                background = self._add_text_to_image(background, text)
            
            # ファイルに保存
            background.save(output_path, "JPEG", quality=95)
            
            print(f"サムネイル生成完了: {output_path}")
            return output_path
            
        except Exception as e:
            raise RuntimeError(f"サムネイル生成中にエラーが発生しました: {e}")
    
    def _create_background(self, image_url: str = None) -> Image.Image:
        """背景画像を作成または取得"""
        if image_url:
            try:
                # URLから画像をダウンロード
                response = requests.get(image_url, timeout=10)
                response.raise_for_status()
                
                # 画像を開く
                background = Image.open(BytesIO(response.content))
                
                # RGBモードに変換（アルファチャンネルを削除）
                if background.mode != 'RGB':
                    background = background.convert('RGB')
                
                # サムネイルサイズにリサイズ（アスペクト比を保持してクロップ）
                background = self._resize_and_crop(background, self.THUMBNAIL_SIZE)
                
                return background
                
            except Exception as e:
                print(f"背景画像の取得に失敗しました: {e}")
                print("デフォルト背景を使用します。")
        
        # デフォルト背景（グラデーション）を作成
        return self._create_gradient_background()
    
    def _resize_and_crop(self, image: Image.Image, target_size: Tuple[int, int]) -> Image.Image:
        """画像をリサイズしてクロップ"""
        target_width, target_height = target_size
        original_width, original_height = image.size
        
        # アスペクト比を計算
        target_ratio = target_width / target_height
        original_ratio = original_width / original_height
        
        if original_ratio > target_ratio:
            # 幅が広すぎる場合、高さに合わせてリサイズしてから幅をクロップ
            new_height = target_height
            new_width = int(original_width * (target_height / original_height))
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # 中央でクロップ
            left = (new_width - target_width) // 2
            image = image.crop((left, 0, left + target_width, target_height))
        else:
            # 高さが高すぎる場合、幅に合わせてリサイズしてから高さをクロップ
            new_width = target_width
            new_height = int(original_height * (target_width / original_width))
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # 中央でクロップ
            top = (new_height - target_height) // 2
            image = image.crop((0, top, target_width, top + target_height))
        
        return image
    
    def _create_gradient_background(self) -> Image.Image:
        """グラデーション背景を作成"""
        width, height = self.THUMBNAIL_SIZE
        
        # 新しい画像を作成
        image = Image.new('RGB', (width, height))
        draw = ImageDraw.Draw(image)
        
        # 青から紫へのグラデーション
        start_color = (64, 128, 255)   # 明るい青
        end_color = (128, 64, 255)     # 紫
        
        for y in range(height):
            # グラデーション比率を計算
            ratio = y / height
            
            # 色を補間
            r = int(start_color[0] * (1 - ratio) + end_color[0] * ratio)
            g = int(start_color[1] * (1 - ratio) + end_color[1] * ratio)
            b = int(start_color[2] * (1 - ratio) + end_color[2] * ratio)
            
            # 水平線を描画
            draw.line([(0, y), (width, y)], fill=(r, g, b))
        
        return image
    
    def _add_text_to_image(self, image: Image.Image, text: str) -> Image.Image:
        """画像にテキストを描画"""
        draw = ImageDraw.Draw(image)
        width, height = image.size
        
        # フォントサイズを自動調整
        font_size = self._calculate_font_size(text, width * 0.8)  # 幅の80%を使用
        font = self._get_font(font_size)
        
        # テキストのバウンディングボックスを取得
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # テキストの位置を計算（中央配置）
        x = (width - text_width) // 2
        y = (height - text_height) // 2
        
        # 影を描画（テキストの可読性向上）
        shadow_offset = max(2, font_size // 20)
        draw.text((x + shadow_offset, y + shadow_offset), text, font=font, fill=(0, 0, 0, 128))
        
        # アウトラインを描画
        outline_width = max(1, font_size // 30)
        for dx in range(-outline_width, outline_width + 1):
            for dy in range(-outline_width, outline_width + 1):
                if dx != 0 or dy != 0:
                    draw.text((x + dx, y + dy), text, font=font, fill=(0, 0, 0))
        
        # メインテキストを描画
        draw.text((x, y), text, font=font, fill=(255, 255, 255))
        
        return image
    
    def _calculate_font_size(self, text: str, max_width: float) -> int:
        """テキストの長さに基づいてフォントサイズを計算"""
        # 基本フォントサイズ
        base_size = 120
        
        # テキストの長さに基づいて調整
        text_length = len(text)
        if text_length <= 5:
            size_factor = 1.0
        elif text_length <= 8:
            size_factor = 0.8
        elif text_length <= 12:
            size_factor = 0.6
        else:
            size_factor = 0.5
        
        return int(base_size * size_factor)
    
    def _get_font(self, size: int) -> ImageFont.FreeTypeFont:
        """フォントを取得"""
        try:
            # システムのデフォルトフォントパスを試す
            font_paths = [
                "/System/Library/Fonts/Helvetica.ttc",  # macOS
                "/System/Library/Fonts/Arial.ttf",      # macOS
                "C:/Windows/Fonts/arial.ttf",           # Windows
                "C:/Windows/Fonts/meiryo.ttc",          # Windows（日本語）
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",  # Linux
                "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",  # Linux
            ]
            
            for font_path in font_paths:
                if os.path.exists(font_path):
                    return ImageFont.truetype(font_path, size)
            
            # システムフォントが見つからない場合はデフォルトフォントを使用
            return ImageFont.load_default()
            
        except Exception:
            # フォント読み込みに失敗した場合はデフォルトフォントを使用
            return ImageFont.load_default()
    
    def validate_thumbnail(self, thumbnail_path: str) -> bool:
        """サムネイル画像を検証"""
        if not os.path.exists(thumbnail_path):
            print(f"エラー: サムネイル画像が見つかりません: {thumbnail_path}")
            return False
        
        try:
            # 画像を開いて検証
            with Image.open(thumbnail_path) as img:
                # ファイルサイズチェック（YouTubeの制限: 2MB）
                file_size = os.path.getsize(thumbnail_path)
                max_size = 2 * 1024 * 1024  # 2MB
                
                if file_size > max_size:
                    print(f"エラー: サムネイル画像が大きすぎます: {file_size / (1024*1024):.1f}MB (最大: 2MB)")
                    return False
                
                # サイズと形式チェック
                width, height = img.size
                if width < 640 or height < 360:
                    print(f"エラー: サムネイル画像が小さすぎます: {width}x{height} (最小: 640x360)")
                    return False
                
                print(f"サムネイル検証成功: {os.path.basename(thumbnail_path)} ({width}x{height}, {file_size / 1024:.1f}KB)")
                return True
                
        except Exception as e:
            print(f"エラー: サムネイル画像の検証に失敗しました: {e}")
            return False
    
    def cleanup_temp_thumbnails(self):
        """一時サムネイルファイルをクリーンアップ"""
        try:
            if os.path.exists(self.temp_dir):
                for filename in os.listdir(self.temp_dir):
                    if filename.startswith('thumbnail_') and filename.endswith(('.jpg', '.jpeg', '.png')):
                        file_path = os.path.join(self.temp_dir, filename)
                        os.remove(file_path)
                        print(f"一時サムネイルファイルを削除: {filename}")
        except Exception as e:
            print(f"警告: 一時サムネイルファイルの削除中にエラーが発生しました: {e}")


def create_thumbnail_generator(config: Config) -> ThumbnailGenerator:
    """ファクトリー関数でThumbnailGeneratorインスタンスを作成"""
    return ThumbnailGenerator(config)


# 使用例とテスト
if __name__ == "__main__":
    from config import create_config
    
    # 設定を作成
    config = create_config()
    
    # サムネイル生成器を作成
    generator = create_thumbnail_generator(config)
    
    # テストケース
    test_cases = [
        "AI技術",
        "人工知能の未来",
        "プログラミング学習",
        "データサイエンス入門"
    ]
    
    print("サムネイル生成テスト開始...")
    
    for i, text in enumerate(test_cases, 1):
        try:
            print(f"\nテスト {i}: '{text}'")
            thumbnail_path = generator.generate_thumbnail(
                text=text,
                output_filename=f"test_thumbnail_{i}.jpg"
            )
            
            # 検証
            if generator.validate_thumbnail(thumbnail_path):
                print(f"✅ テスト {i} 成功: {thumbnail_path}")
            else:
                print(f"❌ テスト {i} 失敗: 検証エラー")
                
        except Exception as e:
            print(f"❌ テスト {i} 失敗: {e}")
    
    print(f"\nテスト完了。生成されたファイルは {config.temp_dir} にあります。")