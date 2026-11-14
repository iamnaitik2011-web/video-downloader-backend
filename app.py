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
    "Accept-Language": "en-US,en;q=0.9"
}

def resolve_pinterest(url):
    session = requests.Session()
    try:
        resp = session.get(url, allow_redirects=True, timeout=15, headers={**HEADERS, "Referer": "https://www.pinterest.com/"})
        final_url = resp.url
        html = resp.text

        clean_html = html.replace('\\/', '/')
        mp4_links = re.findall(r'https://v[0-9a-z]*\.pinimg\.com/videos/[^"\'\s<>]+\.mp4', clean_html)
        if mp4_links:
            for link in mp4_links:
                if '720p' in link or '1080p' in link:
                    return final_url, link
            return final_url, mp4_links[0]

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

def resolve_instagram(url):
    # Clean tracking query parameters (?igsh=...)
    clean_url = url.split('?')[0].rstrip('/')
    shortcode_match = re.search(r'/(?:reel|reels|p|tv)/([A-Za-z0-9_-]+)', clean_url)
    if not shortcode_match:
        return None

    shortcode = shortcode_match.group(1)
    session = requests.Session()

    # Method 1: Instagram Embed Captioned Page (works without login on cloud IPs)
    try:
        embed_url = f"https://www.instagram.com/p/{shortcode}/embed/captioned/"
        resp = session.get(embed_url, timeout=15, headers={
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9"
        })
        text = resp.text.replace('\\/', '/').replace('\\u0026', '&')
        video_matches = re.findall(r'"video_url":"(https://[^"]+\.mp4[^"]*)"', text)
        if video_matches:
            return video_matches[0]
    except Exception:
        pass

    # Method 2: Instagram Public GraphQL Endpoint
    try:
        graphql_url = "https://www.instagram.com/api/graphql"
        payload = {
            "variables": json.dumps({"shortcode": shortcode}),
            "doc_id": "10015901848480474"
        }
        g_headers = {
            "User-Agent": HEADERS["User-Agent"],
            "Content-Type": "application/x-www-form-urlencoded",
            "X-IG-App-ID": "936619743392459",
            "X-ASBD-ID": "129477",
            "X-FB-LSD": "AVqbxe3J_YA"
        }
        g_resp = session.post(graphql_url, data=payload, headers=g_headers, timeout=15)
        g_text = g_resp.text.replace('\\/', '/').replace('\\u0026', '&')
        g_videos = re.findall(r'"video_url":"(https://[^"]+\.mp4[^"]*)"', g_text)
        if g_videos:
            return g_videos[0]
    except Exception:
        pass

    return None

@app.route('/', methods=['GET'])
def home():
    return jsonify({"status": "Backend is running"})

@app.route('/download', methods=['GET'])
def download():
    raw_url = request.args.get('url', '').strip()
    if not raw_url:
        return jsonify({"error": "No URL provided"}), 400

    final_url = raw_url

    # 1. Pinterest Handler
    if "pin.it" in raw_url or "pinterest." in raw_url:
        final_url, direct_mp4 = resolve_pinterest(raw_url)
        if direct_mp4:
            return jsonify({"download_url": direct_mp4, "title": "Pinterest Video"})

    # 2. Instagram Handler (Embed + GraphQL before yt-dlp)
    if "instagram.com" in raw_url:
        insta_mp4 = resolve_instagram(raw_url)
        if insta_mp4:
            return jsonify({"download_url": insta_mp4, "title": "Instagram Video"})

    # 3. Fallback via yt-dlp
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
