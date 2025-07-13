# GEMINI.md

## プロジェクト概要

このプロジェクトは、指定されたテーマに基づき、YouTubeショート動画（30秒）を自動生成し、アップロードまでを行うPythonアプリケーションです。

動画制作の主要な工程（台本生成、画像収集、ナレーション音声合成、動画編集、字幕生成）を自動化し、一連のプロセスを `main.py` を実行するだけで完結できます。

## 主な機能と処理の流れ

1.  **テーマ設定**: ユーザーが動画のテーマ（例：「人工知能の未来」）を指定します。
2.  **台本生成 (`script_generator.py`)**:
    *   Google Gemini API を利用して、指定されたテーマに基づいた30秒の動画用台本（タイトル、ナレーション、画像検索用キーワード）を自動生成します。
3.  **画像収集 (`image_fetcher.py`)**:
    *   Unsplash API を利用し、生成されたキーワードに基づいて動画に使用する画像を複数枚ダウンロードします。
4.  **音声合成 (`voice_generator.py`)**:
    *   VOICEVOX API を利用して、生成されたナレーション台本から音声を合成し、WAVファイルとして保存します。
5.  **動画制作 (`video_creator.py`)**:
    *   `moviepy` ライブラリを使用し、収集した画像をスライドショー形式で繋ぎ合わせ、合成したナレーション音声をBGMとして追加し、一本の動画ファイル（MP4）を生成します。
6.  **字幕生成 (`subtitle_generator.py`)**:
    *   `ffmpeg` を利用して、台本からSRT形式の字幕ファイルを生成し、動画に焼き込みます。
7.  **YouTubeアップロード (`youtube_uploader.py`)**:
    *   YouTube Data API v3 を利用して、完成した動画をYouTubeにアップロードします。OAuth 2.0認証に対応しており、動画のタイトル、説明文、タグも自動で設定されます。

## 主要なモジュールと役割

*   **`main.py`**:
    *   プロジェクト全体のエントリーポイント。各モジュールを順番に呼び出し、動画生成からアップロードまでの一連の処理を実行します。
*   **`config.py`**:
    *   各種APIキー（Gemini, Unsplash, VOICEVOX）、動画設定（解像度、フレームレート）、ファイルパスなどの設定情報を一元管理します。
*   **`script_generator.py`**:
    *   Google Gemini API と連携し、動画の台本を生成します。
*   **`image_fetcher.py`**:
    *   Unsplash API から画像を検索・ダウンロードします。
*   **`voice_generator.py`**:
    *   VOICEVOX API と連携し、テキストから音声を合成します。
*   **`video_creator.py`**:
    *   収集した画像と音声から、`moviepy` を使って動画を組み立てます。
*   **`subtitle_generator.py`**:
    *   `ffmpeg` を使って動画に字幕を追加します。
*   **`youtube_uploader.py`**:
    *   YouTubeへの動画アップロード機能を提供します。

## 実行に必要な設定

1.  **APIキーの設定**:
    *   `.env.template` を参考に `.env` ファイルを作成し、以下のAPIキーを設定する必要があります。
        *   `GEMINI_API_KEY`
        *   `UNSPLASH_ACCESS_KEY`
2.  **VOICEVOX**:
    *   ローカルでVOICEVOXアプリケーションを実行しておく必要があります。
3.  **YouTube API**:
    *   Google Cloud Platform でOAuth 2.0クライアントIDを作成し、`credentials.json` としてプロジェクトルートに配置する必要があります。初回実行時にはブラウザでの認証が求められます。
