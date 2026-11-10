"""
Resource Link Hub - Backend REST API
Studi Kasus No. 9 - UTS Cloud Computing

Endpoint:
  GET    /links            -> daftar semua link materi
  POST   /links            -> tambah link baru  (JSON: {"title", "url", "category"})
  DELETE /links?index=X    -> hapus link pada index X
  GET    /health           -> dipakai Jenkins untuk Health Check

Data disimpan di file JSON di dalam Docker Named Volume (link-hub-data).
Hanya memakai standard library Python (tanpa framework).
"""

import json
import os
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

DATA_DIR = os.environ.get("DATA_DIR", "/var/lib/backend_data")
DATA_FILE = os.path.join(DATA_DIR, "links.json")
PORT = int(os.environ.get("PORT", "5000"))

lock = threading.Lock()


def load_links():
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def save_links(links):
    os.makedirs(DATA_DIR, exist_ok=True)
    tmp = DATA_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(links, f, ensure_ascii=False, indent=2)
    os.replace(tmp, DATA_FILE)  # tulis atomik supaya file tidak korup


class Handler(BaseHTTPRequestHandler):
    # ---------- helper ----------
    def send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):  # preflight CORS (kalau frontend diakses tanpa proxy)
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    # ---------- GET ----------
    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/health":
            return self.send_json(200, {"status": "ok"})
        if path == "/links":
            with lock:
                links = load_links()
            return self.send_json(200, {"count": len(links), "data": links})
        return self.send_json(404, {"error": f"Endpoint {path} tidak ditemukan"})

    # ---------- POST ----------
    def do_POST(self):
        path = urlparse(self.path).path
        if path != "/links":
            return self.send_json(404, {"error": f"Endpoint {path} tidak ditemukan"})

        try:
            length = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(length) or b"")
        except (ValueError, json.JSONDecodeError):
            return self.send_json(400, {"error": "Body harus berupa JSON yang valid"})

        if not isinstance(payload, dict):
            return self.send_json(400, {"error": "Body harus berupa objek JSON"})

        title = str(payload.get("title", "")).strip()
        url = str(payload.get("url", "")).strip()
        category = str(payload.get("category", "Lainnya")).strip() or "Lainnya"

        if not title or not url:
            return self.send_json(400, {"error": "Field 'title' dan 'url' wajib diisi"})
        if not url.startswith(("http://", "https://")):
            return self.send_json(400, {"error": "URL harus diawali http:// atau https://"})

        new_link = {
            "title": title,
            "url": url,
            "category": category,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        with lock:
            links = load_links()
            links.append(new_link)
            save_links(links)
        return self.send_json(201, {"message": "Link berhasil ditambahkan", "data": new_link})

    # ---------- DELETE ----------
    def do_DELETE(self):
        parsed = urlparse(self.path)
        if parsed.path != "/links":
            return self.send_json(404, {"error": f"Endpoint {parsed.path} tidak ditemukan"})

        query = parse_qs(parsed.query)
        if "index" not in query:
            return self.send_json(400, {"error": "Parameter 'index' wajib ada, contoh: /links?index=0"})
        try:
            index = int(query["index"][0])
        except ValueError:
            return self.send_json(400, {"error": "Parameter 'index' harus berupa angka"})

        with lock:
            links = load_links()
            if index < 0 or index >= len(links):
                return self.send_json(404, {"error": f"Link dengan index {index} tidak ditemukan"})
            removed = links.pop(index)
            save_links(links)
        return self.send_json(200, {"message": "Link berhasil dihapus", "data": removed})

    def log_message(self, fmt, *args):
        print(f"[{self.log_date_time_string()}] {self.address_string()} {fmt % args}", flush=True)


if __name__ == "__main__":
    os.makedirs(DATA_DIR, exist_ok=True)
    print(f"Link Hub API berjalan di port {PORT}, data: {DATA_FILE}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
