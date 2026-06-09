#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DELOS · Cosmic Intelligence - Main Server
우주적 지성 · Gemini · Ollama · 덕덕고 · 리서치 · 크롤링
DELOSchat 폴더 진입점 · 로컬 호스트 서버
"""

import os
import sys
import json
import time
import asyncio
import logging
import hashlib
import secrets
import argparse
import threading
import webbrowser
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import socketserver

# ============================================
# CONFIGURATION
# ============================================

VERSION = "1.0.0"
APP_NAME = "DELOS"
APP_SUBTITLE = "Cosmic Intelligence"
DEFAULT_PORT = 8765
DEFAULT_HOST = "127.0.0.1"
BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "logs"
DATA_DIR = BASE_DIR / "data"
CACHE_DIR = BASE_DIR / "cache"
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR
ENTRY_FILE = STATIC_DIR / "DELOS.html"

# Brand palette
BRAND_COLORS = {
    "red": "#ff3b6b",
    "purple": "#a855f7",
    "lime": "#b8ff7c",
    "white": "#ffffff",
    "bg": "#0a0014"
}

# Setup directories
for d in [LOG_DIR, DATA_DIR, CACHE_DIR]:
    d.mkdir(exist_ok=True)

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / "delos.log", encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
log = logging.getLogger("DELOS")

# ============================================
# UTILITIES
# ============================================

def now_iso() -> str:
    return datetime.now().isoformat(timespec='seconds')

def uid(prefix: str = "id") -> str:
    return f"{prefix}-{secrets.token_hex(6)}"

def sha256(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

def safe_read(path: Path, default: str = "") -> str:
    try:
        if path.exists():
            return path.read_text(encoding='utf-8')
    except Exception as e:
        log.warning(f"read failed {path}: {e}")
    return default

def safe_write(path: Path, data: str) -> bool:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(data, encoding='utf-8')
        return True
    except Exception as e:
        log.error(f"write failed {path}: {e}")
        return False

def safe_json(path: Path, default=None):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding='utf-8'))
    except Exception as e:
        log.warning(f"json read failed {path}: {e}")
    return default if default is not None else {}

def safe_json_write(path: Path, data: Any) -> bool:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        return True
    except Exception as e:
        log.error(f"json write failed {path}: {e}")
        return False

# ============================================
# DATA STORE
# ============================================

class DataStore:
    """DELOS 데이터 저장소"""

    def __init__(self):
        self.users_file = DATA_DIR / "users.json"
        self.convs_file = DATA_DIR / "conversations.json"
        self.config_file = DATA_DIR / "config.json"
        self.analytics_file = DATA_DIR / "analytics.json"
        self.cache_index = CACHE_DIR / "index.json"

    def load_users(self) -> List[Dict]:
        return safe_json(self.users_file, [])

    def save_users(self, users: List[Dict]) -> bool:
        return safe_json_write(self.users_file, users)

    def load_conversations(self) -> List[Dict]:
        return safe_json(self.convs_file, [])

    def save_conversations(self, convs: List[Dict]) -> bool:
        return safe_json_write(self.convs_file, convs)

    def load_config(self) -> Dict:
        return safe_json(self.config_file, {
            "version": VERSION,
            "created_at": now_iso(),
            "max_tokens": 8192,
            "temperature": 0.9,
            "ollama_host": "http://localhost:11434",
            "theme": "cosmos"
        })

    def save_config(self, cfg: Dict) -> bool:
        return safe_json_write(self.config_file, cfg)

    def log_event(self, event: str, data: Dict) -> None:
        events = safe_json(self.analytics_file, [])
        events.append({
            "id": uid("evt"),
            "event": event,
            "data": data,
            "timestamp": now_iso()
        })
        # keep only last 1000 events
        if len(events) > 1000:
            events = events[-1000:]
        safe_json_write(self.analytics_file, events)


# ============================================
# AI HANDLER
# ============================================

class AIHandler:
    """제미나이 · Ollama · 덕덕고 등 AI 통합"""

    def __init__(self, store: DataStore):
        self.store = store
        self.gemini_key = os.environ.get("GEMINI_API_KEY", "")
        self.ollama_host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        self.session_history: Dict[str, List[Dict]] = {}

    def set_gemini_key(self, key: str):
        self.gemini_key = key.strip()

    def set_ollama_host(self, host: str):
        self.ollama_host = host.strip()

    async def gemini_chat(self, prompt: str, model: str = "gemini-2.5-flash",
                          max_tokens: int = 8192, temperature: float = 0.9,
                          system_prompt: Optional[str] = None) -> Dict:
        """제미나이 API 호출"""
        if not self.gemini_key:
            return {"error": "Gemini API 키가 설정되지 않았습니다.", "text": ""}
        try:
            import urllib.request
            import urllib.error
            model_path = "gemini-2.5-pro" if "pro" in model else "gemini-2.5-flash"
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_path}:generateContent?key={self.gemini_key}"
            sys_p = system_prompt or "당신은 DELOS입니다. 친절하고 지적인 AI 어시스턴트로 한국어로 응답합니다."
            payload = {
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "systemInstruction": {"parts": [{"text": sys_p}]},
                "generationConfig": {
                    "temperature": temperature,
                    "maxOutputTokens": max_tokens,
                    "topP": 0.95
                }
            }
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read().decode('utf-8'))
            text = ""
            candidates = result.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                text = "".join(p.get("text", "") for p in parts)
            return {"text": text, "model": model_path, "success": True}
        except Exception as e:
            log.exception("gemini error")
            return {"error": str(e), "text": "", "success": False}

    async def ollama_chat(self, prompt: str, model: str = "llama3",
                          max_tokens: int = 8192, temperature: float = 0.9) -> Dict:
        """Ollama API 호출"""
        try:
            import urllib.request
            import urllib.error
            url = f"{self.ollama_host}/api/generate"
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": temperature, "num_predict": max_tokens}
            }
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=120) as resp:
                result = json.loads(resp.read().decode('utf-8'))
            return {
                "text": result.get("response", ""),
                "model": model,
                "success": True,
                "eval_count": result.get("eval_count", 0),
                "total_duration": result.get("total_duration", 0)
            }
        except Exception as e:
            log.exception("ollama error")
            return {"error": str(e), "text": "", "success": False}

    async def ollama_list(self) -> List[Dict]:
        """Ollama 모델 목록"""
        try:
            import urllib.request
            url = f"{self.ollama_host}/api/tags"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=5) as resp:
                result = json.loads(resp.read().decode('utf-8'))
            return result.get("models", [])
        except Exception as e:
            log.warning(f"ollama list error: {e}")
            return []

    async def duckduckgo_search(self, query: str, max_results: int = 10) -> Dict:
        """덕덕고 검색"""
        try:
            import urllib.request
            import urllib.parse
            url = "https://api.duckduckgo.com/?" + urllib.parse.urlencode({
                "q": query,
                "format": "json",
                "no_html": 1,
                "skip_disambig": 1
            })
            req = urllib.request.Request(url, headers={'User-Agent': 'DELOS/1.0'})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode('utf-8'))
            results = []
            if data.get("AbstractText"):
                results.append({
                    "title": data.get("Heading", "요약"),
                    "url": data.get("AbstractURL", ""),
                    "snippet": data.get("AbstractText", ""),
                    "source": "abstract"
                })
            for t in data.get("RelatedTopics", [])[:max_results]:
                if t.get("Text"):
                    results.append({
                        "title": t.get("Text", "").split(" - ")[0],
                        "url": t.get("FirstURL", ""),
                        "snippet": t.get("Text", ""),
                        "source": "related"
                    })
            return {"results": results, "query": query, "success": True}
        except Exception as e:
            log.exception("ddg error")
            return {"error": str(e), "results": [], "success": False}

    async def wiki_search(self, query: str, max_results: int = 5) -> Dict:
        """위키백과 검색"""
        try:
            import urllib.request
            import urllib.parse
            url = "https://ko.wikipedia.org/w/api.php?" + urllib.parse.urlencode({
                "action": "query",
                "list": "search",
                "srsearch": query,
                "format": "json",
                "srlimit": max_results,
                "origin": "*"
            })
            req = urllib.request.Request(url, headers={'User-Agent': 'DELOS/1.0'})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode('utf-8'))
            results = []
            for r in data.get("query", {}).get("search", []):
                snippet = r.get("snippet", "").replace("<span class=\"searchmatch\">", "").replace("</span>", "")
                results.append({
                    "title": r.get("title", ""),
                    "url": f"https://ko.wikipedia.org/wiki/{urllib.parse.quote(r.get('title', ''))}",
                    "snippet": snippet
                })
            return {"results": results, "query": query, "success": True}
        except Exception as e:
            log.exception("wiki error")
            return {"error": str(e), "results": [], "success": False}

    async def web_research(self, query: str) -> Dict:
        """웹 리서치 (덕덕고 + 위키 통합)"""
        ddg = await self.duckduckgo_search(query, 5)
        wiki = await self.wiki_search(query, 5)
        return {
            "query": query,
            "duckduckgo": ddg.get("results", []),
            "wikipedia": wiki.get("results", []),
            "success": True
        }

    async def web_crawl(self, url: str, max_chars: int = 8000) -> Dict:
        """웹 크롤링 (AllOrigins 프록시)"""
        try:
            import urllib.request
            import urllib.parse
            proxy = "https://api.allorigins.win/get?" + urllib.parse.urlencode({"url": url})
            req = urllib.request.Request(proxy, headers={'User-Agent': 'DELOS/1.0'})
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode('utf-8'))
            html = data.get("contents", "")
            import re
            text = re.sub(r'<script[\s\S]*?</script>', ' ', html, flags=re.IGNORECASE)
            text = re.sub(r'<style[\s\S]*?</style>', ' ', text, flags=re.IGNORECASE)
            text = re.sub(r'<[^>]+>', ' ', text)
            text = re.sub(r'\s+', ' ', text).strip()
            return {
                "url": url,
                "text": text[:max_chars],
                "length": len(text),
                "success": True
            }
        except Exception as e:
            log.exception("crawl error")
            return {"error": str(e), "text": "", "success": False}


# ============================================
# HTTP SERVER
# ============================================

class DELOSHandler(BaseHTTPRequestHandler):
    """DELOS HTTP 요청 핸들러"""

    server_version = "DELOS/1.0"

    def log_message(self, format, *args):
        # use our logger instead of stderr
        log.debug(format % args)

    def _set_headers(self, status=200, content_type="application/json", extra: Optional[Dict] = None):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.send_header('Cache-Control', 'no-store')
        if extra:
            for k, v in extra.items():
                self.send_header(k, v)

    def _send_json(self, data: Any, status: int = 200):
        body = json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8')
        self._set_headers(status)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path, status: int = 200):
        if not path.exists():
            self._send_json({"error": "Not found", "path": str(path)}, 404)
            return
        try:
            content = path.read_bytes()
            ext = path.suffix.lower()
            ctypes = {
                '.html': 'text/html; charset=utf-8',
                '.css': 'text/css; charset=utf-8',
                '.js': 'application/javascript; charset=utf-8',
                '.json': 'application/json; charset=utf-8',
                '.svg': 'image/svg+xml',
                '.png': 'image/png',
                '.jpg': 'image/jpeg',
                '.ico': 'image/x-icon',
                '.py': 'text/plain; charset=utf-8',
                '.md': 'text/plain; charset=utf-8'
            }
            ct = ctypes.get(ext, 'application/octet-stream')
            self._set_headers(status, ct)
            self.send_header('Content-Length', str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _read_body(self) -> Dict:
        try:
            length = int(self.headers.get('Content-Length', 0))
            if length == 0:
                return {}
            raw = self.rfile.read(length)
            if not raw:
                return {}
            text = raw.decode('utf-8', errors='replace')
            return json.loads(text) if text.strip() else {}
        except Exception as e:
            log.warning(f"read body error: {e}")
            return {}

    def do_OPTIONS(self):
        self._set_headers(204)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        ai: AIHandler = self.server.ai
        store: DataStore = self.server.store

        # root
        if path == '/' or path == '/index.html':
            self._send_file(ENTRY_FILE)
            return
        if path == '/favicon.ico':
            ico = BASE_DIR / "favicon.ico"
            if ico.exists():
                self._send_file(ico)
            else:
                self._set_headers(204)
                self.end_headers()
            return

        # static
        if path.startswith('/static/'):
            rel = path[len('/static/'):]
            self._send_file(STATIC_DIR / rel)
            return

        # api
        if path == '/api/health':
            self._send_json({
                "status": "ok",
                "app": APP_NAME,
                "version": VERSION,
                "uptime": time.time() - self.server.start_time,
                "ollama_host": ai.ollama_host,
                "has_gemini": bool(ai.gemini_key),
                "time": now_iso()
            })
            return
        if path == '/api/info':
            self._send_json({
                "name": APP_NAME,
                "subtitle": APP_SUBTITLE,
                "version": VERSION,
                "colors": BRAND_COLORS,
                "features": ["chat", "duckduckgo", "web_research", "web_crawl", "ollama", "gemini", "streaming", "persona"]
            })
            return
        if path == '/api/ollama/models':
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                models = loop.run_until_complete(ai.ollama_list())
                loop.close()
                self._send_json({"models": models, "success": True})
            except Exception as e:
                self._send_json({"error": str(e), "models": []}, 500)
            return
        if path == '/api/conversations':
            qs = parse_qs(parsed.query)
            user = qs.get('user', ['default'])[0]
            convs = store.load_conversations()
            user_convs = [c for c in convs if c.get('user') == user]
            self._send_json({"conversations": user_convs})
            return
        if path.startswith('/api/conversations/'):
            cid = path.split('/')[-1]
            convs = store.load_conversations()
            conv = next((c for c in convs if c.get('id') == cid), None)
            if conv:
                self._send_json({"conversation": conv})
            else:
                self._send_json({"error": "Not found"}, 404)
            return

        # SPA fallback
        self._send_file(ENTRY_FILE)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        body = self._read_body()
        ai: AIHandler = self.server.ai
        store: DataStore = self.server.store

        if path == '/api/chat':
            prompt = body.get('prompt') or body.get('message') or ''
            model = body.get('model', 'gemini-2.5-flash')
            max_tokens = int(body.get('max_tokens', 8192))
            temperature = float(body.get('temperature', 0.9))
            session_id = body.get('session_id', 'default')
            api_key = body.get('api_key') or ai.gemini_key
            if api_key: ai.set_gemini_key(api_key)
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                if 'ollama' in model or body.get('ollama'):
                    result = loop.run_until_complete(ai.ollama_chat(prompt, model, max_tokens, temperature))
                else:
                    result = loop.run_until_complete(ai.gemini_chat(prompt, model, max_tokens, temperature))
                loop.close()
                self._send_json(result)
            except Exception as e:
                log.exception("chat error")
                self._send_json({"error": str(e), "text": "", "success": False}, 500)
            return
        if path == '/api/search/duckduckgo':
            q = body.get('query', '')
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(ai.duckduckgo_search(q, 10))
                loop.close()
                self._send_json(result)
            except Exception as e:
                self._send_json({"error": str(e), "results": []}, 500)
            return
        if path == '/api/search/wiki':
            q = body.get('query', '')
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(ai.wiki_search(q, 5))
                loop.close()
                self._send_json(result)
            except Exception as e:
                self._send_json({"error": str(e), "results": []}, 500)
            return
        if path == '/api/research':
            q = body.get('query', '')
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(ai.web_research(q))
                loop.close()
                self._send_json(result)
            except Exception as e:
                self._send_json({"error": str(e)}, 500)
            return
        if path == '/api/crawl':
            url = body.get('url', '')
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(ai.web_crawl(url))
                loop.close()
                self._send_json(result)
            except Exception as e:
                self._send_json({"error": str(e), "text": ""}, 500)
            return
        if path == '/api/conversations':
            conv = {
                "id": uid("conv"),
                "title": body.get("title", "새 대화"),
                "messages": body.get("messages", []),
                "model": body.get("model", "gemini-2.5-flash"),
                "user": body.get("user", "default"),
                "created_at": now_iso(),
                "updated_at": now_iso()
            }
            convs = store.load_conversations()
            convs.insert(0, conv)
            store.save_conversations(convs)
            self._send_json({"conversation": conv, "success": True})
            return
        if path == '/api/config':
            cfg = store.load_config()
            cfg.update(body)
            store.save_config(cfg)
            self._send_json({"config": cfg, "success": True})
            return
        if path == '/api/ollama/host':
            host = body.get('host', 'http://localhost:11434')
            ai.set_ollama_host(host)
            self._send_json({"ollama_host": ai.ollama_host, "success": True})
            return
        if path == '/api/event':
            event = body.get('event', 'unknown')
            data = body.get('data', {})
            store.log_event(event, data)
            self._send_json({"success": True})
            return

        self._send_json({"error": "Not found", "path": path}, 404)

    def do_PUT(self):
        parsed = urlparse(self.path)
        path = parsed.path
        body = self._read_body()
        store: DataStore = self.server.store

        if path.startswith('/api/conversations/'):
            cid = path.split('/')[-1]
            convs = store.load_conversations()
            for c in convs:
                if c.get('id') == cid:
                    c.update(body)
                    c['updated_at'] = now_iso()
                    store.save_conversations(convs)
                    self._send_json({"conversation": c, "success": True})
                    return
            self._send_json({"error": "Not found"}, 404)
            return
        if path == '/api/config':
            cfg = store.load_config()
            cfg.update(body)
            store.save_config(cfg)
            self._send_json({"config": cfg, "success": True})
            return
        self._send_json({"error": "Not found"}, 404)

    def do_DELETE(self):
        parsed = urlparse(self.path)
        path = parsed.path
        store: DataStore = self.server.store

        if path.startswith('/api/conversations/'):
            cid = path.split('/')[-1]
            convs = store.load_conversations()
            convs = [c for c in convs if c.get('id') != cid]
            store.save_conversations(convs)
            self._send_json({"success": True})
            return
        self._send_json({"error": "Not found"}, 404)


class DELOSServer(HTTPServer):
    """DELOS 메인 서버"""
    def __init__(self, addr, handler):
        super().__init__(addr, handler)
        self.store = DataStore()
        self.ai = AIHandler(self.store)
        self.start_time = time.time()


# ============================================
# MAIN ENTRY POINT
# ============================================

def print_banner(host: str, port: int):
    """시작 배너 출력"""
    banner = f"""
  ✦  DELOS · Cosmic Intelligence  ✦
  v{VERSION}
  ▸ Host:      http://{host}:{port}
  ▸ Entry:     http://{host}:{port}/
  ▸ API:       http://{host}:{port}/api/
  ▸ Logs:      {LOG_DIR}
  ▸ Data:      {DATA_DIR}
  우주적 지성과 함께하는 차세대 대화
  빨강 · 보라 · 연두 · 흰색 · 글래스모피즘 · RGB
"""
    print(banner)


def main():
    parser = argparse.ArgumentParser(description='DELOS · Cosmic Intelligence Server')
    parser.add_argument('--host', default=os.environ.get('DELOS_HOST', DEFAULT_HOST), help='호스트')
    parser.add_argument('--port', type=int, default=int(os.environ.get('DELOS_PORT', DEFAULT_PORT)), help='포트')
    parser.add_argument('--no-browser', action='store_true', help='브라우저 열지 않기')
    parser.add_argument('--dev', action='store_true', help='개발 모드')
    args = parser.parse_args()

    host = args.host
    port = args.port

    # Create server with extended attributes
    class _DELOSServer(DELOSServer):
        allow_reuse_address = True

    try:
        server = _DELOSServer((host, port), DELOSHandler)
    except OSError as e:
        log.error(f"포트 {port}에 바인딩 실패: {e}")
        # 다른 포트 시도
        for try_port in range(port + 1, port + 10):
            try:
                server = _DELOSServer((host, try_port), DELOSHandler)
                port = try_port
                log.info(f"대체 포트 {port} 사용")
                break
            except OSError:
                continue
        else:
            log.error("사용 가능한 포트 없음")
            sys.exit(1)

    print_banner(host, port)

    # Open browser
    if not args.no_browser:
        def _open_browser():
            time.sleep(1.5)
            url = f'http://{host}:{port}/'
            try:
                webbrowser.open(url)
                log.info(f"브라우저 열림: {url}")
            except Exception as e:
                log.warning(f"브라우저 열기 실패: {e}")
        threading.Thread(target=_open_browser, daemon=True).start()

    log.info(f"DELOS 시작 · {host}:{port}")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("DELOS 종료")
        server.shutdown()
        server.server_close()


if __name__ == '__main__':
    main()



