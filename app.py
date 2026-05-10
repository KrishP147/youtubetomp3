import os
import json
import uuid
from flask import Flask, request, jsonify, send_file, render_template
import yt_dlp
from concurrent.futures import ThreadPoolExecutor, as_completed

app = Flask(__name__)

DOWNLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'downloads')
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


def download_to_mp3(url):
    url = url.strip()
    if not url:
        return None

    file_id = str(uuid.uuid4())[:8]
    output_template = os.path.join(DOWNLOAD_DIR, f'{file_id}_%(title)s.%(ext)s')

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': output_template,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': True,
        'no_warnings': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get('title', 'Unknown')
            filename = None
            for f in os.listdir(DOWNLOAD_DIR):
                if f.startswith(file_id) and f.endswith('.mp3'):
                    filename = f
                    break
            if filename:
                return {'url': url, 'title': title, 'filename': filename, 'status': 'success'}
            return {'url': url, 'status': 'error', 'error': 'File not found after download'}
    except Exception as e:
        return {'url': url, 'status': 'error', 'error': str(e)}


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/convert', methods=['POST'])
def convert():
    data = request.get_json()
    raw = (data or {}).get('urls', '')
    urls = [u.strip() for u in raw.split('\n') if u.strip()]

    if not urls:
        return jsonify({'error': 'No URLs provided'}), 400

    results = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(download_to_mp3, url): url for url in urls}
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
