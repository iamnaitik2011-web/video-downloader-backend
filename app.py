from flask import Flask, request, jsonify
from flask_cors import CORS
import yt_dlp

app = Flask(__name__)
CORS(app)

@app.route('/')
def home():
    return "API is active!"

@app.route('/download', methods=['GET'])
def download():
    url = request.args.get('url')
    if not url:
        return jsonify({'error': 'URL missing'}), 400

    # Format ko flexible banaya taaki har tarah ke Pinterest/Insta formats pick ho sakein
    ydl_opts = {
        'format': 'bestvideo*+bestaudio/best',
        'quiet': True,
        'no_warnings': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            video_url = info.get('url')

            # Agar direct url na mile toh formats list me se best direct mp4/stream dhoondo
            if not video_url and 'formats' in info:
                for f in reversed(info['formats']):
                    if f.get('url') and (f.get('vcodec') != 'none' or f.get('ext') == 'mp4'):
                        video_url = f.get('url')
                        break

            if video_url:
                return jsonify({'download_url': video_url})
            else:
                return jsonify({'error': 'Format not supported'}), 404

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
