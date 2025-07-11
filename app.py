import os
import requests
import uuid
import shutil
import rarfile
rarfile.UNRAR_TOOL = "bsdtar"
import logging
import time
import hashlib
from flask import Flask, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

PUBLIC_DIR = 'public'
os.makedirs(PUBLIC_DIR, exist_ok=True)

def cleanup_old_files(ttl_seconds=3600):
    now = time.time()
    for entry in os.listdir(PUBLIC_DIR):
        entry_path = os.path.join(PUBLIC_DIR, entry)
        try:
            if os.path.getmtime(entry_path) < now - ttl_seconds:
                if os.path.isdir(entry_path):
                    shutil.rmtree(entry_path)
                else:
                    os.remove(entry_path)
        except Exception as e:
            logging.warning(f"Could not remove {entry_path}: {e}")

@app.before_request
def auto_cleanup():
    cleanup_old_files(ttl_seconds=3600)

def download_file(url, temp_path):
    response = requests.get(url, stream=True)
    response.raise_for_status()
    with open(temp_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    return temp_path

def process_files(rar_url):
    extract_id = str(uuid.uuid4())
    public_extract_path = os.path.join(PUBLIC_DIR, extract_id)
    os.makedirs(public_extract_path, exist_ok=True)
    import tempfile
    with tempfile.TemporaryDirectory() as temp_dir:
        rar_path = os.path.join(temp_dir, 'downloaded.rar')
        download_file(rar_url, rar_path)
        with rarfile.RarFile(rar_path) as rf:
            rf.extractall(public_extract_path)
            extracted_files = []
            for file in os.listdir(public_extract_path):
                file_path = os.path.join(public_extract_path, file)
                file_size = os.path.getsize(file_path)
                safe_name = secure_filename(file)
                file_id = hashlib.sha256(safe_name.encode()).hexdigest()[:16]
                extracted_files.append({
                    "name": file,
                    "path": file,
                    "size": file_size,
                    "file_id": file_id,
                    "download_url": f"/public/{extract_id}/{file_id}"
                })
    return extract_id, extracted_files

@app.route('/process', methods=['POST'])
def process_rar():
    rar_url = request.form.get('rar')
    if not rar_url:
        return jsonify({"error": "Missing 'rar' URL parameter"}), 400
    try:
        extract_id, files = process_files(rar_url)
        for f in files:
            f.pop('file_id', None)
        return jsonify({
            "extract_id": extract_id,
            "files": files,
            "total_files": len(files)
        })
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Failed to download file: {str(e)}"}), 400
    except rarfile.BadRarFile:
        return jsonify({"error": "Invalid or corrupted RAR file"}), 400
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@app.route('/public/<extract_id>/<file_id>', methods=['GET'])
def download_public_file_by_id(extract_id, file_id):
    public_extract_path = os.path.join(PUBLIC_DIR, extract_id)
    if not os.path.exists(public_extract_path):
        return jsonify({"error": "Extract ID not found"}), 404
    for file in os.listdir(public_extract_path):
        safe_name = secure_filename(file)
        fid = hashlib.sha256(safe_name.encode()).hexdigest()[:16]
        if fid == file_id:
            return send_from_directory(public_extract_path, safe_name, as_attachment=True)
    return jsonify({"error": "File not found"}), 404

@app.route('/')
def index():
    return "<h1>RAR File Extractor API</h1><p>POST /process (formData: rar=url) → JSON com links de download. GET /public/&lt;extract_id&gt;/&lt;file_id&gt; para baixar.</p>"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True) 