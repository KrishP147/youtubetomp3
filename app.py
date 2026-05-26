import os
import re
import uuid
from flask import Flask, request, jsonify, send_file, render_template
import yt_dlp
from concurrent.futures import ThreadPoolExecutor, as_completed

app = Flask(__name__)

DOWNLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'downloads')
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


def sanitize_filename(name):
    cleaned = re.sub(r'[\\/*?:"<>|]', '', name).strip()
    return cleaned if cleaned else 'Unknown'


def search_and_download_song(title, artist):
    display_name = sanitize_filename(f"{title}, {artist}" if artist else title)
    final_path = os.path.join(DOWNLOAD_DIR, f'{display_name}.mp3')

    if os.path.exists(final_path):
        return {'title': title, 'artist': artist, 'filename': f'{display_name}.mp3', 'status': 'success'}

    file_id = str(uuid.uuid4())[:8]
    output_template = os.path.join(DOWNLOAD_DIR, f'{file_id}.%(ext)s')
    query = f"{title} {artist}".strip()

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': output_template,
        'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
        'quiet': True,
        'no_warnings': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([f'ytsearch1:{query}'])

        for f in os.listdir(DOWNLOAD_DIR):
            if f.startswith(file_id) and f.endswith('.mp3'):
                os.rename(os.path.join(DOWNLOAD_DIR, f), final_path)
                return {'title': title, 'artist': artist, 'filename': f'{display_name}.mp3', 'status': 'success'}

        return {'title': title, 'artist': artist, 'status': 'error', 'error': 'File not found after download'}
    except Exception as e:
        return {'title': title, 'artist': artist, 'status': 'error', 'error': str(e)}


def download_media(url, output_format='mp3'):
    url = url.strip()
    if not url:
        return None

    output_format = (output_format or 'mp3').lower()
    if output_format not in {'mp3', 'mp4'}:
        return {'url': url, 'status': 'error', 'error': 'Unsupported format. Use mp3 or mp4.'}

    file_id = str(uuid.uuid4())[:8]
    output_template = os.path.join(DOWNLOAD_DIR, f'{file_id}_%(title)s.%(ext)s')

    if output_format == 'mp3':
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': output_template,
            'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
            'quiet': True,
            'no_warnings': True,
        }
    else:
        ydl_opts = {
            'format': 'bestvideo+bestaudio/best',
            'merge_output_format': 'mp4',
            'outtmpl': output_template,
            'postprocessors': [{'key': 'FFmpegVideoConvertor', 'preferedformat': 'mp4'}],
            'quiet': True,
            'no_warnings': True,
        }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get('title', 'Unknown')
            for f in os.listdir(DOWNLOAD_DIR):
                if f.startswith(file_id) and f.endswith(f'.{output_format}'):
                    return {'url': url, 'title': title, 'filename': f, 'status': 'success'}
            return {'url': url, 'status': 'error', 'error': 'File not found after download'}
    except Exception as e:
        return {'url': url, 'status': 'error', 'error': str(e)}


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/parse-screenshot', methods=['POST'])
def parse_screenshot():
    if 'image' not in request.files:
        return jsonify({'error': 'No image provided'}), 400

    try:
        from PIL import Image, ImageEnhance, ImageOps, ImageStat
        import pytesseract
    except ImportError as e:
        return jsonify({'error': f'Missing dependency: {e}. Run: pip install pytesseract Pillow', 'raw': ''}), 500

    try:
        img = Image.open(request.files['image'].stream).convert('RGB')
        gray = img.convert('L')
        avg_brightness = ImageStat.Stat(gray).mean[0]

        if avg_brightness < 128:
            img = ImageOps.invert(img)

        img = img.convert('L')
        img = ImageEnhance.Contrast(img).enhance(1.5)

        raw = pytesseract.image_to_string(img, config='--psm 6')
        return jsonify({'raw': raw})
    except Exception as e:
        return jsonify({'error': str(e), 'raw': ''}), 500


@app.route('/spotify-convert', methods=['POST'])
def spotify_convert():
    data = request.get_json() or {}
    songs = data.get('songs', [])

    if not songs:
        return jsonify({'error': 'No songs provided'}), 400

    results = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(search_and_download_song, s.get('title', ''), s.get('artist', '')): s
            for s in songs if s.get('title')
        }
        for future in as_completed(futures):
            result = future.result()
            if result:
                results.append(result)

    return jsonify({'results': results})


@app.route('/convert', methods=['POST'])
def convert():
    data = request.get_json() or {}
    raw = data.get('urls', '')
    output_format = (data.get('format', 'mp3') or 'mp3').lower()
    if output_format not in {'mp3', 'mp4'}:
        return jsonify({'error': 'Unsupported format. Use mp3 or mp4.'}), 400

    urls = [u.strip() for u in raw.split('\n') if u.strip()]

    if not urls:
        return jsonify({'error': 'No URLs provided'}), 400

    results = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(download_media, url, output_format): url for url in urls}
        for future in as_completed(futures):
            result = future.result()
            if result:
                results.append(result)

    return jsonify({'results': results})


@app.route('/download/<path:filename>')
def download_file(filename):
    filepath = os.path.join(DOWNLOAD_DIR, filename)
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True)
    return jsonify({'error': 'File not found'}), 404


if __name__ == '__main__':
    app.run(debug=True, port=5000)
