from flask import Flask, request, jsonify
from flask_cors import CORS
import yt_dlp
import requests
import re

app = Flask(__name__)
CORS(app)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9"
}

def resolve_url(url):
    try:
        resp = requests.get(url, allow_redirects=True, timeout=12, headers=HEADERS)
        return resp.url, resp.text
    except Exception:
        return url, ""

@app.route('/', methods=['GET'])
def home():
    return jsonify({"status": "Backend is running"})

@app.route('/download', methods=['GET'])
def download():
    raw_url = request.args.get('url', '').strip()
    if not raw_url:
        return jsonify({"error": "No URL provided"}), 400

    final_url, html_text = resolve_url(raw_url)

    ydl_opts = {
        'format': 'best[ext=mp4]/best',
        'quiet': True,
        'no_warnings': True,
        'http_headers': HEADERS
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(final_url, download=False)
            video_url = info.get('url')
            if not video_url and 'entries' in info:
                video_url = info['entries'][0].get('url')
            if video_url:
                return jsonify({"download_url": video_url, "title": info.get('title', 'video')})
    except Exception:
        pass

    # Fallback for Pinterest MP4 streams
    if "pinterest" in final_url and html_text:
        mp4_matches = re.findall(r'https://v1\.pinimg\.com/videos/[^"\'\\]+\.mp4', html_text)
        if mp4_matches:
            return jsonify({"download_url": mp4_matches[0], "title": "Pinterest Video"})

    return jsonify({"error": "Could not extract video"}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
