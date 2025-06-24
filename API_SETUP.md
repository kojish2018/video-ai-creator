# API Setup Guide

## Required API Keys

### 1. Google Gemini API Key
1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Copy the API key and add it to your `.env` file:
   ```
   GEMINI_API_KEY=your_actual_api_key_here
   ```

### 2. Unsplash API Key
1. Go to [Unsplash Developers](https://unsplash.com/developers)
2. Create a new application
3. Copy the Access Key and add it to your `.env` file:
   ```
   UNSPLASH_ACCESS_KEY=your_actual_access_key_here
   ```

### 3. VOICEVOX Local Setup
1. Download VOICEVOX from [official website](https://voicevox.hiroshiba.jp/)
2. Install and run VOICEVOX
3. Ensure the server is running on `http://127.0.0.1:50021`
4. The `.env` file should have:
   ```
   VOICEVOX_SERVER_URL=http://127.0.0.1:50021
   ```

## Environment Setup Steps

1. Copy `.env.template` to `.env`:
   ```bash
   cp .env.template .env
   ```

2. Edit `.env` file with your actual API keys

3. Test configuration:
   ```python
   from config import Config
   config = Config()
   config.validate()  # Should not raise any errors
   ```

## Troubleshooting

- **Gemini API**: Make sure the API key is valid and has proper permissions
- **Unsplash API**: Check that your application has the necessary access
- **VOICEVOX**: Ensure the application is running and accessible on the specified URL