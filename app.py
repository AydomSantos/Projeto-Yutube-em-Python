from flask import Flask, render_template, request, send_file, jsonify
import os
import ssl
import requests
import re
import uuid
from dotenv import load_dotenv
import yt_dlp  

# Carregar variáveis de ambiente do arquivo .env
load_dotenv() 

# Adicionar tratamento para erros SSL
ssl._create_default_https_context = ssl._create_unverified_context

app = Flask(__name__)

# Configuration
DOWNLOAD_FOLDER = 'downloads'
ALLOWED_EXTENSIONS = {'mp4'}
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY') 

# Ensure download directory exists
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

def sanitize_filename(filename):
    """Remove invalid characters from filename"""
    return re.sub(r'[<>:"/\\|?*]', '', filename)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET', 'POST'])
def index():
    error = None
    if request.method == 'POST':
        url = request.form.get('url', '').strip()
        
        if not url:
            error = "Please enter a YouTube URL"
        else:
            try:
                # Validate YouTube URL
                if "youtube.com" not in url and "youtu.be" not in url:
                    raise ValueError("Invalid YouTube URL")
                
                # Extract video ID for logging purposes
                video_id = None
                if "youtube.com/watch" in url:
                    query_params = url.split("?")[1] if "?" in url else ""
                    params = query_params.split("&")
                    for param in params:
                        if param.startswith("v="):
                            video_id = param[2:]
                            break
                elif "youtu.be/" in url:
                    video_id = url.split("youtu.be/")[1].split("?")[0].split("&")[0]
                
                app.logger.info(f"Attempting to download video with ID: {video_id}")
                
                # Set up yt-dlp options
                ydl_opts = {
                    'format': 'best[ext=mp4]',
                    'outtmpl': os.path.join(DOWNLOAD_FOLDER, '%(title)s_%(id)s.%(ext)s'),
                    'restrictfilenames': True,
                    'noplaylist': True,
                    'quiet': False,
                    'no_warnings': False
                }
                
                # Download with yt-dlp
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    title = info.get('title', 'video')
                    video_id = info.get('id', 'unknown')
                    ext = info.get('ext', 'mp4')
                    
                    # Get the downloaded file path
                    sanitized_title = sanitize_filename(title)
                    downloaded_filename = f"{sanitized_title}_{video_id}.{ext}"
                    filepath = os.path.join(DOWNLOAD_FOLDER, downloaded_filename)
                    
                    # If the file doesn't exist with the expected name, try to find it
                    if not os.path.exists(filepath):
                        for file in os.listdir(DOWNLOAD_FOLDER):
                            if video_id in file and file.endswith(f".{ext}"):
                                filepath = os.path.join(DOWNLOAD_FOLDER, file)
                                break
                    
                    app.logger.info(f"Downloaded to: {filepath}")
                    
                    # Send file to user
                    return send_file(
                        filepath,
                        as_attachment=True,
                        download_name=f"{sanitized_title}.{ext}"
                    )
                
            except Exception as e:
                error = f"Error downloading video: {str(e)}"
                app.logger.error(f"Download error: {str(e)}")
    
    return render_template('index.html', error=error)

@app.route('/channel/<channel_id>', methods=['GET'])
def get_channel_info(channel_id):
    if not YOUTUBE_API_KEY: 
        return jsonify({"error": "YouTube API key not configured or not set in environment variables"}), 500
    
    try:
        response = requests.get(
            "https://www.googleapis.com/youtube/v3/channels",
            params={
                "part": "snippet,statistics",
                "id": channel_id,
                "key": YOUTUBE_API_KEY
            },
            timeout=10
        )
        response.raise_for_status()
        return jsonify(response.json())
    except requests.exceptions.RequestException as e:
        app.logger.error(f"API request failed: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500

if __name__ == '__main__':
    # Clean up old downloads on startup
    for filename in os.listdir(DOWNLOAD_FOLDER):
        filepath = os.path.join(DOWNLOAD_FOLDER, filename)
        try:
            if os.path.isfile(filepath) and allowed_file(filename):
                os.unlink(filepath)
        except Exception as e:
            app.logger.error(f"Error deleting file {filepath}: {str(e)}")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
