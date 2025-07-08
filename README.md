# autoYoutube

AI自動動画生成システム - テーマを入力するだけで30秒動画を自動生成

## 🎬 概要 (最新更新版 - Hook動作テスト)

autoYoutubeは、AIを活用してテーマから自動的に30秒の動画を生成する最新システムです。スクリプト生成、画像取得、音声生成、動画作成の全工程を自動化し、完全なパイプライン処理を実現します。

## ✨ 機能

- **スクリプト生成**: Gemini APIを使用してテーマから動画スクリプトを自動生成
- **画像取得**: Unsplash APIから関連画像を自動収集
- **音声生成**: VOICEVOXを使用してスクリプトから音声を生成
- **動画作成**: MoviePyで画像と音声を組み合わせて動画を作成
- **プログレス表示**: リアルタイムで生成進行状況を表示
- **対話モード**: コマンドラインでの対話的な動画生成
- **バッチモード**: コマンドライン引数での一括処理
- **字幕生成**: 自動字幕生成機能をサポート
- **YouTube連携**: 生成した動画を直接YouTubeにアップロード可能

## 🚀 インストール

### 前提条件

- Python 3.8以上
- VOICEVOX（音声生成用）

### 依存関係のインストール

```bash
pip install -r requirements.txt
```

### API設定

1. `.env`ファイルを作成：
```bash
cp .env.example .env
```

2. 必要なAPIキーを設定：
```
GEMINI_API_KEY=your_gemini_api_key
UNSPLASH_ACCESS_KEY=your_unsplash_access_key
```

詳細な設定方法は[API_SETUP.md](API_SETUP.md)を参照してください。

## 📖 使用方法

### 対話モード

```bash
python main.py
```

### コマンドライン引数指定

```bash
# テーマを指定して実行
python main.py -t "人工知能の未来"

# 出力ファイル名も指定
python main.py --theme "宇宙探査" -o "space_video.mp4"

# 設定テスト
python main.py --test-config
```

## 📁 プロジェクト構成

```
autoYoutube/
├── main.py              # メイン実行ファイル
├── config.py            # 設定管理
├── script_generator.py  # スクリプト生成
├── image_fetcher.py     # 画像取得
├── voice_generator.py   # 音声生成
├── video_creator.py     # 動画作成
├── subtitle_generator.py # 字幕生成
├── youtube_uploader.py  # YouTube連携
├── output/              # 生成された動画の出力先
├── temp/                # 一時ファイル
├── requirements.txt     # Python依存関係
├── API_SETUP.md         # API設定ガイド
└── tests/               # テストファイル
```

## 🧪 テスト

```bash
# 全テストの実行
python -m pytest

# 特定のテストファイルの実行
python test_config.py
python test_api_integration.py
```

## ⚙️ 設定

主要な設定項目：

- `VIDEO_DURATION`: 動画の長さ（デフォルト: 30秒）
- `MAX_IMAGES`: 使用する画像の最大数（デフォルト: 5枚）
- `VIDEO_SIZE`: 動画解像度（デフォルト: 1920x1080）
- `VOICE_SPEED`: 音声読み上げ速度（デフォルト: 1.0）

設定の詳細は`config.py`を参照してください。

## 🤝 コントリビューション

1. このリポジトリをフォーク
2. 機能ブランチを作成（`git checkout -b feature/amazing-feature`）
3. 変更をコミット（`git commit -m 'Add amazing feature'`）
4. ブランチにプッシュ（`git push origin feature/amazing-feature`）
5. プルリクエストを作成

## 📝 ライセンス

このプロジェクトは[MIT License](LICENSE)の下で公開されています。

## 🙏 謝辞

- [Gemini API](https://ai.google.dev/) - スクリプト生成
- [Unsplash API](https://unsplash.com/developers) - 画像提供
- [VOICEVOX](https://voicevox.hiroshiba.jp/) - 音声合成
- [MoviePy](https://zulko.github.io/moviepy/) - 動画編集

## 📞 サポート

問題が発生した場合は、[Issues](https://github.com/your-username/autoYoutube/issues)で報告してください。