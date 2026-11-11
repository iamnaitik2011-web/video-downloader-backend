from flask import Flask, request, jsonify
from flask_cors import CORS
import yt_dlp
import re

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

    ydl_opts = {
        'format': 'best',
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            video_url = info.get('url')

            # Agar direct url na mile toh formats me se search karein
            if not video_url and 'formats' in info:
                for f in reversed(info['formats']):
                    if f.get('url'):
                        video_url = f.get('url')
                        # Direct MP4 milte hi break
                        if '.mp4' in video_url:
                            break

            # Agar URL m3u8 (HLS) nikla, toh Pinterest ka direct MP4 link banayein
            if video_url and '.m3u8' in video_url:
                # Pinterest hls URL ko direct 720p mp4 URL me convert karna:
                # /hls/.../xxx_720w.m3u8 -> /exp/.../xxx_720w.mp4
                mp4_url = re.sub(r'/hls/', '/exp/', video_url)
                mp4_url = re.sub(r'\.m3u8$', '.mp4', mp4_url)
                video_url = mp4_url

            if video_url:
                return jsonify({'download_url': video_url})
            else:
                return jsonify({'error': 'Video stream nahi mili'}), 404

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
