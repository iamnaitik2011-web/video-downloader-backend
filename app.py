from flask import Flask, request, jsonify
from flask_cors import CORS
import yt_dlp
import requests
import re
import json

app = Flask(__name__)
CORS(app)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.pinterest.com/"
}

def resolve_pinterest(url):
    session = requests.Session()
    try:
        resp = session.get(url, allow_redirects=True, timeout=15, headers=HEADERS)
        final_url = resp.url
        html = resp.text

        # Method 1: Unescape slashes and search all pinimg mp4 URLs
        clean_html = html.replace('\\/', '/')
        mp4_links = re.findall(r'https://v[0-9a-z]*\.pinimg\.com/videos/[^"\'\s<>]+\.mp4', clean_html)
        if mp4_links:
            # Prefer 720p / highest quality mp4
            for link in mp4_links:
                if '720p' in link or '1080p' in link:
                    return final_url, link
            return final_url, mp4_links[0]

        # Method 2: Extract Pin ID and call Pinterest PinResource API
        pin_match = re.search(r'/pin/(\d+)', final_url)
        if pin_match:
            pin_id = pin_match.group(1)
            api_url = f"https://www.pinterest.com/resource/PinResource/get/?data=%7B%22options%22%3A%7B%22id%22%3A%22{pin_id}%22%2C%22field_set_key%22%3A%22unauth_react_main_pin%22%7D%7D"
            api_resp = session.get(api_url, timeout=12, headers={**HEADERS, "X-Requested-With": "XMLHttpRequest"})
            api_text = api_resp.text.replace('\\/', '/')
            api_mp4s = re.findall(r'https://v[0-9a-z]*\.pinimg\.com/videos/[^"\'\s<>]+\.mp4', api_text)
            if api_mp4s:
                return final_url, api_mp4s[0]

        return final_url, None
    except Exception:
        return url, None

@app.route('/', methods=['GET'])
def home():
    return jsonify({"status": "Backend is running"})

@app.route('/download', methods=['GET'])
def download():
    raw_url = request.args.get('url', '').strip()
    if not raw_url:
        return jsonify({"error": "No URL provided"}), 400

    final_url = raw_url

    # Check Pinterest first
    if "pin.it" in raw_url or "pinterest." in raw_url:
        final_url, direct_mp4 = resolve_pinterest(raw_url)
        if direct_mp4:
            return jsonify({"download_url": direct_mp4, "title": "Pinterest Video"})

    # Fallback / Instagram via yt-dlp
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
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({"error": "Could not extract video"}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
