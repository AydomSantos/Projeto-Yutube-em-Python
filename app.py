from flask import Flask, render_template, request, send_file, jsonify, url_for
import os
import ssl
import requests
import re
import uuid
import time
import threading
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

# Dicionário para armazenar informações de progresso
download_progress = {}

def sanitize_filename(filename):
    """Remove invalid characters from filename"""
    return re.sub(r'[<>:"/\\|?*]', '', filename)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Função de callback para monitorar o progresso do download
def progress_hook(d):
    download_id = d.get('_download_id')
    if not download_id or download_id not in download_progress:
        return
    
    if d['status'] == 'downloading':
        total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
        downloaded_bytes = d.get('downloaded_bytes', 0)
        
        if total_bytes > 0:
            percent = int(downloaded_bytes / total_bytes * 100)
            speed = d.get('speed', 0)
            if speed:
                speed_str = f"{speed / 1024 / 1024:.2f} MB/s"
            else:
                speed_str = "Calculando..."
                
            download_progress[download_id].update({
                'percent': percent,
                'speed': speed_str,
                'status': 'downloading'
            })
    
    elif d['status'] == 'finished':
        download_progress[download_id].update({
            'percent': 100,
            'speed': '0 MB/s',
            'status': 'processing'
        })
    
    elif d['status'] == 'error':
        download_progress[download_id].update({
            'status': 'error',
            'error': d.get('error', 'Erro desconhecido')
        })

def download_video(url, download_id):
    max_retries = 3
    retry_count = 0
    last_error = None
    
    while retry_count < max_retries:
        try:
            # Atualizar status para mostrar tentativa
            download_progress[download_id].update({
                'status': 'trying',
                'percent': 0,
                'speed': '0 MB/s',
                'title': f'Tentativa {retry_count + 1}/{max_retries}...'
            })
            
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
            
            app.logger.info(f"Attempt {retry_count + 1}/{max_retries} to download video with ID: {video_id}")
            
            # Diferentes métodos de download baseados na tentativa atual
            if retry_count == 0:
                # Primeira tentativa: método requests com SSL desativado
                download_with_requests(url, download_id, video_id)
                return  # Se bem-sucedido, retorna
                
            elif retry_count == 1:
                # Segunda tentativa: método yt-dlp com opções SSL personalizadas
                download_with_ytdlp(url, download_id, video_id, ssl_verify=False)
                return  # Se bem-sucedido, retorna
                
            else:
                # Terceira tentativa: método yt-dlp com configurações padrão
                download_with_ytdlp(url, download_id, video_id, ssl_verify=True)
                return  # Se bem-sucedido, retorna
                
        except Exception as e:
            retry_count += 1
            last_error = str(e)
            app.logger.error(f"Download attempt {retry_count}/{max_retries} failed: {last_error}")
            time.sleep(2)  # Esperar antes da próxima tentativa
    
    # Se chegou aqui, todas as tentativas falharam
    app.logger.error(f"All download attempts failed: {last_error}")
    download_progress[download_id].update({
        'status': 'error',
        'error': f"Falha após {max_retries} tentativas: {last_error}"
    })

# Função para download usando requests
def download_with_requests(url, download_id, video_id):
    # Set up yt-dlp options apenas para extrair informações
    ydl_opts = {
        'format': 'best[ext=mp4]',
        'skip_download': True,
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        }
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        title = info.get('title', 'video')
        video_id = info.get('id', 'unknown')
        ext = 'mp4'
        
        # Obter a URL direta do vídeo
        if 'url' in info:
            direct_url = info['url']
        elif 'formats' in info and len(info['formats']) > 0:
            # Pegar o formato com melhor qualidade
            formats = [f for f in info['formats'] if f.get('ext') == 'mp4']
            if formats:
                direct_url = formats[-1]['url']
            else:
                direct_url = info['formats'][-1]['url']
        else:
            raise ValueError("Não foi possível obter a URL direta do vídeo")
        
        # Baixar usando requests
        sanitized_title = sanitize_filename(title)
        filename = f"{sanitized_title}_{video_id}.{ext}"
        filepath = os.path.join(DOWNLOAD_FOLDER, filename)
        
        # Configurar a sessão com opções SSL personalizadas
        session = requests.Session()
        session.verify = False  # Desativa verificação SSL
        
        # Suprimir avisos de SSL inseguro
        import warnings
        warnings.filterwarnings('ignore', message='Unverified HTTPS request')
        
        # Usar a sessão configurada para o download
        response = session.get(
            direct_url, 
            stream=True,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            },
            timeout=30  # Aumentar o timeout
        )
        total_size = int(response.headers.get('content-length', 0))
        
        with open(filepath, 'wb') as f:
            downloaded = 0
            start_time = time.time()
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    
                    # Calcular velocidade
                    elapsed = time.time() - start_time
                    if elapsed > 0:
                        speed = downloaded / elapsed / 1024 / 1024  # MB/s
                    else:
                        speed = 0
                    
                    # Atualizar progresso
                    if total_size > 0:
                        percent = int(downloaded / total_size * 100)
                        download_progress[download_id].update({
                            'percent': percent,
                            'speed': f"{speed:.2f} MB/s",
                            'status': 'downloading',
                            'title': title
                        })
        
        # Atualizar o progresso para concluído
        download_progress[download_id].update({
            'status': 'completed',
            'percent': 100,
            'filepath': filepath,
            'filename': sanitized_title + '.' + ext
        })

# Função para download usando yt-dlp
def download_with_ytdlp(url, download_id, video_id, ssl_verify=True):
    # Set up yt-dlp options
    ydl_opts = {
        'format': 'best[ext=mp4]',
        'outtmpl': os.path.join(DOWNLOAD_FOLDER, '%(title)s_%(id)s.%(ext)s'),
        'restrictfilenames': True,
        'noplaylist': True,
        'quiet': False,
        'no_warnings': False,
        'progress_hooks': [progress_hook],
        '_download_id': download_id,
        'nocheckcertificate': not ssl_verify,  # Inverter para corresponder ao parâmetro
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        }
    }
    
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
        
        # Atualizar o progresso para concluído
        download_progress[download_id].update({
            'status': 'completed',
            'percent': 100,
            'filepath': filepath,
            'filename': sanitized_title + '.' + ext
        })

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/download', methods=['POST'])
def start_download():
    url = request.form.get('url', '').strip()
    
    if not url:
        return jsonify({'error': 'URL não fornecida'}), 400
    
    try:
        # Validate YouTube URL
        if "youtube.com" not in url and "youtu.be" not in url:
            return jsonify({'error': 'URL do YouTube inválida'}), 400
        
        # Gerar ID único para este download
        download_id = str(uuid.uuid4())
        
        # Inicializar o progresso
        download_progress[download_id] = {
            'percent': 0,
            'speed': '0 MB/s',
            'status': 'starting',
            'title': 'Iniciando download...'
        }
        
        # Iniciar o download em uma thread separada
        thread = threading.Thread(target=download_video, args=(url, download_id))
        thread.daemon = True
        thread.start()
        
        return jsonify({'download_id': download_id})
    
    except Exception as e:
        app.logger.error(f"Error starting download: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/progress/<download_id>', methods=['GET'])
def get_progress(download_id):
    if download_id not in download_progress:
        return jsonify({'error': 'Download não encontrado'}), 404
    
    progress_data = download_progress[download_id]
    
    # Se o download estiver concluído, fornecer URL para download
    if progress_data.get('status') == 'completed':
        download_url = url_for('get_file', download_id=download_id)
        progress_data['download_url'] = download_url
    
    return jsonify(progress_data)

@app.route('/file/<download_id>', methods=['GET'])
def get_file(download_id):
    if download_id not in download_progress:
        return jsonify({'error': 'Download não encontrado'}), 404
    
    progress_data = download_progress[download_id]
    
    if progress_data.get('status') != 'completed':
        return jsonify({'error': 'Download ainda não concluído'}), 400
    
    filepath = progress_data.get('filepath')
    filename = progress_data.get('filename')
    
    if not filepath or not os.path.exists(filepath):
        return jsonify({'error': 'Arquivo não encontrado'}), 404
    
    # Enviar o arquivo para o usuário
    return send_file(
        filepath,
        as_attachment=True,
        download_name=filename
    )

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
