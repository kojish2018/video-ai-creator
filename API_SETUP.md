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

### 4. YouTube Data API v3 Setup

#### Step 1: Create a Google Cloud Project
1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Click "Create Project" or select an existing project
3. Give your project a name (e.g., "autoYoutube")
4. Note your Project ID

#### Step 2: Enable YouTube Data API v3
1. In the Google Cloud Console, navigate to "APIs & Services" > "Library"
2. Search for "YouTube Data API v3"
3. Click on it and press "Enable"

#### Step 3: Create Credentials

**Option A: OAuth 2.0 (Recommended for uploading videos)**
1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth client ID"
3. If prompted, configure the OAuth consent screen:
   - Choose "External" user type
   - Fill in required fields (App name, User support email, Developer contact)
   - Add scopes: `../auth/youtube.upload`, `../auth/youtube`
4. For Application type, choose "Desktop application"
5. Give it a name (e.g., "autoYoutube Client")
6. Download the JSON file and save it as `credentials/client_secrets.json`

**Option B: API Key (For read-only operations)**
1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "API key"
3. Copy the API key and add it to your `.env` file as `YOUTUBE_API_KEY`

#### YouTube API Environment Variables
Add to your `.env` file:
```
YOUTUBE_API_KEY=your_api_key_here
YOUTUBE_CLIENT_SECRETS_FILE=credentials/client_secrets.json
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

## YouTube API Authentication Flow

When you first run the upload script, it will:
1. Open a browser window for OAuth authentication
2. Ask you to sign in to your Google account
3. Request permission to manage your YouTube channel
4. Save the authentication token for future use

## Troubleshooting

### General APIs
- **Gemini API**: Make sure the API key is valid and has proper permissions
- **Unsplash API**: Check that your application has the necessary access
- **VOICEVOX**: Ensure the application is running and accessible on the specified URL

### YouTube API Issues
- **"The request cannot be completed because you have exceeded your quota"**
  - YouTube API has daily quotas. Wait 24 hours or request quota increase.

- **"Access blocked: This app's request is invalid"**
  - Make sure your OAuth consent screen is properly configured
  - Add your email to test users if the app is in testing mode

- **"Client secrets file not found"**
  - Ensure the `credentials/client_secrets.json` file exists
  - Check the file path in your `.env` file

### API Quotas
- YouTube Data API v3 has a default quota of 10,000 units per day
- Video uploads cost 1600 units each
- Check your quota usage in Google Cloud Console > APIs & Services > Quotas

## Security Notes
- Never commit your `client_secrets.json` or `.env` files to version control
- Keep your API keys secure and rotate them regularly
- Use environment variables for all sensitive configuration

## Additional Resources
- [YouTube Data API Documentation](https://developers.google.com/youtube/v3)
- [Google Cloud Console](https://console.cloud.google.com/)
- [OAuth 2.0 Scopes for YouTube](https://developers.google.com/youtube/v3/guides/auth/server-side-web-apps#scope)