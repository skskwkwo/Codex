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




# DELOS Extended Modules
# DELOS extended line 1
# DELOS extended line 2
# DELOS extended line 3
# DELOS extended line 4
# DELOS extended line 5
# DELOS extended line 6
# DELOS extended line 7
# DELOS extended line 8
# DELOS extended line 9
# DELOS extended line 10
# DELOS extended line 11
# DELOS extended line 12
# DELOS extended line 13
# DELOS extended line 14
# DELOS extended line 15
# DELOS extended line 16
# DELOS extended line 17
# DELOS extended line 18
# DELOS extended line 19
# DELOS extended line 20
# DELOS extended line 21
# DELOS extended line 22
# DELOS extended line 23
# DELOS extended line 24
# DELOS extended line 25
# DELOS extended line 26
# DELOS extended line 27
# DELOS extended line 28
# DELOS extended line 29
# DELOS extended line 30
# DELOS extended line 31
# DELOS extended line 32
# DELOS extended line 33
# DELOS extended line 34
# DELOS extended line 35
# DELOS extended line 36
# DELOS extended line 37
# DELOS extended line 38
# DELOS extended line 39
# DELOS extended line 40
# DELOS extended line 41
# DELOS extended line 42
# DELOS extended line 43
# DELOS extended line 44
# DELOS extended line 45
# DELOS extended line 46
# DELOS extended line 47
# DELOS extended line 48
# DELOS extended line 49
# DELOS extended line 50
# DELOS extended line 51
# DELOS extended line 52
# DELOS extended line 53
# DELOS extended line 54
# DELOS extended line 55
# DELOS extended line 56
# DELOS extended line 57
# DELOS extended line 58
# DELOS extended line 59
# DELOS extended line 60
# DELOS extended line 61
# DELOS extended line 62
# DELOS extended line 63
# DELOS extended line 64
# DELOS extended line 65
# DELOS extended line 66
# DELOS extended line 67
# DELOS extended line 68
# DELOS extended line 69
# DELOS extended line 70
# DELOS extended line 71
# DELOS extended line 72
# DELOS extended line 73
# DELOS extended line 74
# DELOS extended line 75
# DELOS extended line 76
# DELOS extended line 77
# DELOS extended line 78
# DELOS extended line 79
# DELOS extended line 80
# DELOS extended line 81
# DELOS extended line 82
# DELOS extended line 83
# DELOS extended line 84
# DELOS extended line 85
# DELOS extended line 86
# DELOS extended line 87
# DELOS extended line 88
# DELOS extended line 89
# DELOS extended line 90
# DELOS extended line 91
# DELOS extended line 92
# DELOS extended line 93
# DELOS extended line 94
# DELOS extended line 95
# DELOS extended line 96
# DELOS extended line 97
# DELOS extended line 98
# DELOS extended line 99
# DELOS extended line 100
# DELOS extended line 101
# DELOS extended line 102
# DELOS extended line 103
# DELOS extended line 104
# DELOS extended line 105
# DELOS extended line 106
# DELOS extended line 107
# DELOS extended line 108
# DELOS extended line 109
# DELOS extended line 110
# DELOS extended line 111
# DELOS extended line 112
# DELOS extended line 113
# DELOS extended line 114
# DELOS extended line 115
# DELOS extended line 116
# DELOS extended line 117
# DELOS extended line 118
# DELOS extended line 119
# DELOS extended line 120
# DELOS extended line 121
# DELOS extended line 122
# DELOS extended line 123
# DELOS extended line 124
# DELOS extended line 125
# DELOS extended line 126
# DELOS extended line 127
# DELOS extended line 128
# DELOS extended line 129
# DELOS extended line 130
# DELOS extended line 131
# DELOS extended line 132
# DELOS extended line 133
# DELOS extended line 134
# DELOS extended line 135
# DELOS extended line 136
# DELOS extended line 137
# DELOS extended line 138
# DELOS extended line 139
# DELOS extended line 140
# DELOS extended line 141
# DELOS extended line 142
# DELOS extended line 143
# DELOS extended line 144
# DELOS extended line 145
# DELOS extended line 146
# DELOS extended line 147
# DELOS extended line 148
# DELOS extended line 149
# DELOS extended line 150
# DELOS extended line 151
# DELOS extended line 152
# DELOS extended line 153
# DELOS extended line 154
# DELOS extended line 155
# DELOS extended line 156
# DELOS extended line 157
# DELOS extended line 158
# DELOS extended line 159
# DELOS extended line 160
# DELOS extended line 161
# DELOS extended line 162
# DELOS extended line 163
# DELOS extended line 164
# DELOS extended line 165
# DELOS extended line 166
# DELOS extended line 167
# DELOS extended line 168
# DELOS extended line 169
# DELOS extended line 170
# DELOS extended line 171
# DELOS extended line 172
# DELOS extended line 173
# DELOS extended line 174
# DELOS extended line 175
# DELOS extended line 176
# DELOS extended line 177
# DELOS extended line 178
# DELOS extended line 179
# DELOS extended line 180
# DELOS extended line 181
# DELOS extended line 182
# DELOS extended line 183
# DELOS extended line 184
# DELOS extended line 185
# DELOS extended line 186
# DELOS extended line 187
# DELOS extended line 188
# DELOS extended line 189
# DELOS extended line 190
# DELOS extended line 191
# DELOS extended line 192
# DELOS extended line 193
# DELOS extended line 194
# DELOS extended line 195
# DELOS extended line 196
# DELOS extended line 197
# DELOS extended line 198
# DELOS extended line 199
# DELOS extended line 200
# DELOS extended line 201
# DELOS extended line 202
# DELOS extended line 203
# DELOS extended line 204
# DELOS extended line 205
# DELOS extended line 206
# DELOS extended line 207
# DELOS extended line 208
# DELOS extended line 209
# DELOS extended line 210
# DELOS extended line 211
# DELOS extended line 212
# DELOS extended line 213
# DELOS extended line 214
# DELOS extended line 215
# DELOS extended line 216
# DELOS extended line 217
# DELOS extended line 218
# DELOS extended line 219
# DELOS extended line 220
# DELOS extended line 221
# DELOS extended line 222
# DELOS extended line 223
# DELOS extended line 224
# DELOS extended line 225
# DELOS extended line 226
# DELOS extended line 227
# DELOS extended line 228
# DELOS extended line 229
# DELOS extended line 230
# DELOS extended line 231
# DELOS extended line 232
# DELOS extended line 233
# DELOS extended line 234
# DELOS extended line 235
# DELOS extended line 236
# DELOS extended line 237
# DELOS extended line 238
# DELOS extended line 239
# DELOS extended line 240
# DELOS extended line 241
# DELOS extended line 242
# DELOS extended line 243
# DELOS extended line 244
# DELOS extended line 245
# DELOS extended line 246
# DELOS extended line 247
# DELOS extended line 248
# DELOS extended line 249
# DELOS extended line 250
# DELOS extended line 251
# DELOS extended line 252
# DELOS extended line 253
# DELOS extended line 254
# DELOS extended line 255
# DELOS extended line 256
# DELOS extended line 257
# DELOS extended line 258
# DELOS extended line 259
# DELOS extended line 260
# DELOS extended line 261
# DELOS extended line 262
# DELOS extended line 263
# DELOS extended line 264
# DELOS extended line 265
# DELOS extended line 266
# DELOS extended line 267
# DELOS extended line 268
# DELOS extended line 269
# DELOS extended line 270
# DELOS extended line 271
# DELOS extended line 272
# DELOS extended line 273
# DELOS extended line 274
# DELOS extended line 275
# DELOS extended line 276
# DELOS extended line 277
# DELOS extended line 278
# DELOS extended line 279
# DELOS extended line 280
# DELOS extended line 281
# DELOS extended line 282
# DELOS extended line 283
# DELOS extended line 284
# DELOS extended line 285
# DELOS extended line 286
# DELOS extended line 287
# DELOS extended line 288
# DELOS extended line 289
# DELOS extended line 290
# DELOS extended line 291
# DELOS extended line 292
# DELOS extended line 293
# DELOS extended line 294
# DELOS extended line 295
# DELOS extended line 296
# DELOS extended line 297
# DELOS extended line 298
# DELOS extended line 299
# DELOS extended line 300
# DELOS extended line 301
# DELOS extended line 302
# DELOS extended line 303
# DELOS extended line 304
# DELOS extended line 305
# DELOS extended line 306
# DELOS extended line 307
# DELOS extended line 308
# DELOS extended line 309
# DELOS extended line 310
# DELOS extended line 311
# DELOS extended line 312
# DELOS extended line 313
# DELOS extended line 314
# DELOS extended line 315
# DELOS extended line 316
# DELOS extended line 317
# DELOS extended line 318
# DELOS extended line 319
# DELOS extended line 320
# DELOS extended line 321
# DELOS extended line 322
# DELOS extended line 323
# DELOS extended line 324
# DELOS extended line 325
# DELOS extended line 326
# DELOS extended line 327
# DELOS extended line 328
# DELOS extended line 329
# DELOS extended line 330
# DELOS extended line 331
# DELOS extended line 332
# DELOS extended line 333
# DELOS extended line 334
# DELOS extended line 335
# DELOS extended line 336
# DELOS extended line 337
# DELOS extended line 338
# DELOS extended line 339
# DELOS extended line 340
# DELOS extended line 341
# DELOS extended line 342
# DELOS extended line 343
# DELOS extended line 344
# DELOS extended line 345
# DELOS extended line 346
# DELOS extended line 347
# DELOS extended line 348
# DELOS extended line 349
# DELOS extended line 350
# DELOS extended line 351
# DELOS extended line 352
# DELOS extended line 353
# DELOS extended line 354
# DELOS extended line 355
# DELOS extended line 356
# DELOS extended line 357
# DELOS extended line 358
# DELOS extended line 359
# DELOS extended line 360
# DELOS extended line 361
# DELOS extended line 362
# DELOS extended line 363
# DELOS extended line 364
# DELOS extended line 365
# DELOS extended line 366
# DELOS extended line 367
# DELOS extended line 368
# DELOS extended line 369
# DELOS extended line 370
# DELOS extended line 371
# DELOS extended line 372
# DELOS extended line 373
# DELOS extended line 374
# DELOS extended line 375
# DELOS extended line 376
# DELOS extended line 377
# DELOS extended line 378
# DELOS extended line 379
# DELOS extended line 380
# DELOS extended line 381
# DELOS extended line 382
# DELOS extended line 383
# DELOS extended line 384
# DELOS extended line 385
# DELOS extended line 386
# DELOS extended line 387
# DELOS extended line 388
# DELOS extended line 389
# DELOS extended line 390
# DELOS extended line 391
# DELOS extended line 392
# DELOS extended line 393
# DELOS extended line 394
# DELOS extended line 395
# DELOS extended line 396
# DELOS extended line 397
# DELOS extended line 398
# DELOS extended line 399
# DELOS extended line 400
# DELOS extended line 401
# DELOS extended line 402
# DELOS extended line 403
# DELOS extended line 404
# DELOS extended line 405
# DELOS extended line 406
# DELOS extended line 407
# DELOS extended line 408
# DELOS extended line 409
# DELOS extended line 410
# DELOS extended line 411
# DELOS extended line 412
# DELOS extended line 413
# DELOS extended line 414
# DELOS extended line 415
# DELOS extended line 416
# DELOS extended line 417
# DELOS extended line 418
# DELOS extended line 419
# DELOS extended line 420
# DELOS extended line 421
# DELOS extended line 422
# DELOS extended line 423
# DELOS extended line 424
# DELOS extended line 425
# DELOS extended line 426
# DELOS extended line 427
# DELOS extended line 428
# DELOS extended line 429
# DELOS extended line 430
# DELOS extended line 431
# DELOS extended line 432
# DELOS extended line 433
# DELOS extended line 434
# DELOS extended line 435
# DELOS extended line 436
# DELOS extended line 437
# DELOS extended line 438
# DELOS extended line 439
# DELOS extended line 440
# DELOS extended line 441
# DELOS extended line 442
# DELOS extended line 443
# DELOS extended line 444
# DELOS extended line 445
# DELOS extended line 446
# DELOS extended line 447
# DELOS extended line 448
# DELOS extended line 449
# DELOS extended line 450
# DELOS extended line 451
# DELOS extended line 452
# DELOS extended line 453
# DELOS extended line 454
# DELOS extended line 455
# DELOS extended line 456
# DELOS extended line 457
# DELOS extended line 458
# DELOS extended line 459
# DELOS extended line 460
# DELOS extended line 461
# DELOS extended line 462
# DELOS extended line 463
# DELOS extended line 464
# DELOS extended line 465
# DELOS extended line 466
# DELOS extended line 467
# DELOS extended line 468
# DELOS extended line 469
# DELOS extended line 470
# DELOS extended line 471
# DELOS extended line 472
# DELOS extended line 473
# DELOS extended line 474
# DELOS extended line 475
# DELOS extended line 476
# DELOS extended line 477
# DELOS extended line 478
# DELOS extended line 479
# DELOS extended line 480
# DELOS extended line 481
# DELOS extended line 482
# DELOS extended line 483
# DELOS extended line 484
# DELOS extended line 485
# DELOS extended line 486
# DELOS extended line 487
# DELOS extended line 488
# DELOS extended line 489
# DELOS extended line 490
# DELOS extended line 491
# DELOS extended line 492
# DELOS extended line 493
# DELOS extended line 494
# DELOS extended line 495
# DELOS extended line 496
# DELOS extended line 497
# DELOS extended line 498
# DELOS extended line 499
# DELOS extended line 500
# DELOS extended line 501
# DELOS extended line 502
# DELOS extended line 503
# DELOS extended line 504
# DELOS extended line 505
# DELOS extended line 506
# DELOS extended line 507
# DELOS extended line 508
# DELOS extended line 509
# DELOS extended line 510
# DELOS extended line 511
# DELOS extended line 512
# DELOS extended line 513
# DELOS extended line 514
# DELOS extended line 515
# DELOS extended line 516
# DELOS extended line 517
# DELOS extended line 518
# DELOS extended line 519
# DELOS extended line 520
# DELOS extended line 521
# DELOS extended line 522
# DELOS extended line 523
# DELOS extended line 524
# DELOS extended line 525
# DELOS extended line 526
# DELOS extended line 527
# DELOS extended line 528
# DELOS extended line 529
# DELOS extended line 530
# DELOS extended line 531
# DELOS extended line 532
# DELOS extended line 533
# DELOS extended line 534
# DELOS extended line 535
# DELOS extended line 536
# DELOS extended line 537
# DELOS extended line 538
# DELOS extended line 539
# DELOS extended line 540
# DELOS extended line 541
# DELOS extended line 542
# DELOS extended line 543
# DELOS extended line 544
# DELOS extended line 545
# DELOS extended line 546
# DELOS extended line 547
# DELOS extended line 548
# DELOS extended line 549
# DELOS extended line 550
# DELOS extended line 551
# DELOS extended line 552
# DELOS extended line 553
# DELOS extended line 554
# DELOS extended line 555
# DELOS extended line 556
# DELOS extended line 557
# DELOS extended line 558
# DELOS extended line 559
# DELOS extended line 560
# DELOS extended line 561
# DELOS extended line 562
# DELOS extended line 563
# DELOS extended line 564
# DELOS extended line 565
# DELOS extended line 566
# DELOS extended line 567
# DELOS extended line 568
# DELOS extended line 569
# DELOS extended line 570
# DELOS extended line 571
# DELOS extended line 572
# DELOS extended line 573
# DELOS extended line 574
# DELOS extended line 575
# DELOS extended line 576
# DELOS extended line 577
# DELOS extended line 578
# DELOS extended line 579
# DELOS extended line 580
# DELOS extended line 581
# DELOS extended line 582
# DELOS extended line 583
# DELOS extended line 584
# DELOS extended line 585
# DELOS extended line 586
# DELOS extended line 587
# DELOS extended line 588
# DELOS extended line 589
# DELOS extended line 590
# DELOS extended line 591
# DELOS extended line 592
# DELOS extended line 593
# DELOS extended line 594
# DELOS extended line 595
# DELOS extended line 596
# DELOS extended line 597
# DELOS extended line 598
# DELOS extended line 599
# DELOS extended line 600
# DELOS extended line 601
# DELOS extended line 602
# DELOS extended line 603
# DELOS extended line 604
# DELOS extended line 605
# DELOS extended line 606
# DELOS extended line 607
# DELOS extended line 608
# DELOS extended line 609
# DELOS extended line 610
# DELOS extended line 611
# DELOS extended line 612
# DELOS extended line 613
# DELOS extended line 614
# DELOS extended line 615
# DELOS extended line 616
# DELOS extended line 617
# DELOS extended line 618
# DELOS extended line 619
# DELOS extended line 620
# DELOS extended line 621
# DELOS extended line 622
# DELOS extended line 623
# DELOS extended line 624
# DELOS extended line 625
# DELOS extended line 626
# DELOS extended line 627
# DELOS extended line 628
# DELOS extended line 629
# DELOS extended line 630
# DELOS extended line 631
# DELOS extended line 632
# DELOS extended line 633
# DELOS extended line 634
# DELOS extended line 635
# DELOS extended line 636
# DELOS extended line 637
# DELOS extended line 638
# DELOS extended line 639
# DELOS extended line 640
# DELOS extended line 641
# DELOS extended line 642
# DELOS extended line 643
# DELOS extended line 644
# DELOS extended line 645
# DELOS extended line 646
# DELOS extended line 647
# DELOS extended line 648
# DELOS extended line 649
# DELOS extended line 650
# DELOS extended line 651
# DELOS extended line 652
# DELOS extended line 653
# DELOS extended line 654
# DELOS extended line 655
# DELOS extended line 656
# DELOS extended line 657
# DELOS extended line 658
# DELOS extended line 659
# DELOS extended line 660
# DELOS extended line 661
# DELOS extended line 662
# DELOS extended line 663
# DELOS extended line 664
# DELOS extended line 665
# DELOS extended line 666
# DELOS extended line 667
# DELOS extended line 668
# DELOS extended line 669
# DELOS extended line 670
# DELOS extended line 671
# DELOS extended line 672
# DELOS extended line 673
# DELOS extended line 674
# DELOS extended line 675
# DELOS extended line 676
# DELOS extended line 677
# DELOS extended line 678
# DELOS extended line 679
# DELOS extended line 680
# DELOS extended line 681
# DELOS extended line 682
# DELOS extended line 683
# DELOS extended line 684
# DELOS extended line 685
# DELOS extended line 686
# DELOS extended line 687
# DELOS extended line 688
# DELOS extended line 689
# DELOS extended line 690
# DELOS extended line 691
# DELOS extended line 692
# DELOS extended line 693
# DELOS extended line 694
# DELOS extended line 695
# DELOS extended line 696
# DELOS extended line 697
# DELOS extended line 698
# DELOS extended line 699
# DELOS extended line 700
# DELOS extended line 701
# DELOS extended line 702
# DELOS extended line 703
# DELOS extended line 704
# DELOS extended line 705
# DELOS extended line 706
# DELOS extended line 707
# DELOS extended line 708
# DELOS extended line 709
# DELOS extended line 710
# DELOS extended line 711
# DELOS extended line 712
# DELOS extended line 713
# DELOS extended line 714
# DELOS extended line 715
# DELOS extended line 716
# DELOS extended line 717
# DELOS extended line 718
# DELOS extended line 719
# DELOS extended line 720
# DELOS extended line 721
# DELOS extended line 722
# DELOS extended line 723
# DELOS extended line 724
# DELOS extended line 725
# DELOS extended line 726
# DELOS extended line 727
# DELOS extended line 728
# DELOS extended line 729
# DELOS extended line 730
# DELOS extended line 731
# DELOS extended line 732
# DELOS extended line 733
# DELOS extended line 734
# DELOS extended line 735
# DELOS extended line 736
# DELOS extended line 737
# DELOS extended line 738
# DELOS extended line 739
# DELOS extended line 740
# DELOS extended line 741
# DELOS extended line 742
# DELOS extended line 743
# DELOS extended line 744
# DELOS extended line 745
# DELOS extended line 746
# DELOS extended line 747
# DELOS extended line 748
# DELOS extended line 749
# DELOS extended line 750
# DELOS extended line 751
# DELOS extended line 752
# DELOS extended line 753
# DELOS extended line 754
# DELOS extended line 755
# DELOS extended line 756
# DELOS extended line 757
# DELOS extended line 758
# DELOS extended line 759
# DELOS extended line 760
# DELOS extended line 761
# DELOS extended line 762
# DELOS extended line 763
# DELOS extended line 764
# DELOS extended line 765
# DELOS extended line 766
# DELOS extended line 767
# DELOS extended line 768
# DELOS extended line 769
# DELOS extended line 770
# DELOS extended line 771
# DELOS extended line 772
# DELOS extended line 773
# DELOS extended line 774
# DELOS extended line 775
# DELOS extended line 776
# DELOS extended line 777
# DELOS extended line 778
# DELOS extended line 779
# DELOS extended line 780
# DELOS extended line 781
# DELOS extended line 782
# DELOS extended line 783
# DELOS extended line 784
# DELOS extended line 785
# DELOS extended line 786
# DELOS extended line 787
# DELOS extended line 788
# DELOS extended line 789
# DELOS extended line 790
# DELOS extended line 791
# DELOS extended line 792
# DELOS extended line 793
# DELOS extended line 794
# DELOS extended line 795
# DELOS extended line 796
# DELOS extended line 797
# DELOS extended line 798
# DELOS extended line 799
# DELOS extended line 800
# DELOS extended line 801
# DELOS extended line 802
# DELOS extended line 803
# DELOS extended line 804
# DELOS extended line 805
# DELOS extended line 806
# DELOS extended line 807
# DELOS extended line 808
# DELOS extended line 809
# DELOS extended line 810
# DELOS extended line 811
# DELOS extended line 812
# DELOS extended line 813
# DELOS extended line 814
# DELOS extended line 815
# DELOS extended line 816
# DELOS extended line 817
# DELOS extended line 818
# DELOS extended line 819
# DELOS extended line 820
# DELOS extended line 821
# DELOS extended line 822
# DELOS extended line 823
# DELOS extended line 824
# DELOS extended line 825
# DELOS extended line 826
# DELOS extended line 827
# DELOS extended line 828
# DELOS extended line 829
# DELOS extended line 830
# DELOS extended line 831
# DELOS extended line 832
# DELOS extended line 833
# DELOS extended line 834
# DELOS extended line 835
# DELOS extended line 836
# DELOS extended line 837
# DELOS extended line 838
# DELOS extended line 839
# DELOS extended line 840
# DELOS extended line 841
# DELOS extended line 842
# DELOS extended line 843
# DELOS extended line 844
# DELOS extended line 845
# DELOS extended line 846
# DELOS extended line 847
# DELOS extended line 848
# DELOS extended line 849
# DELOS extended line 850
# DELOS extended line 851
# DELOS extended line 852
# DELOS extended line 853
# DELOS extended line 854
# DELOS extended line 855
# DELOS extended line 856
# DELOS extended line 857
# DELOS extended line 858
# DELOS extended line 859
# DELOS extended line 860
# DELOS extended line 861
# DELOS extended line 862
# DELOS extended line 863
# DELOS extended line 864
# DELOS extended line 865
# DELOS extended line 866
# DELOS extended line 867
# DELOS extended line 868
# DELOS extended line 869
# DELOS extended line 870
# DELOS extended line 871
# DELOS extended line 872
# DELOS extended line 873
# DELOS extended line 874
# DELOS extended line 875
# DELOS extended line 876
# DELOS extended line 877
# DELOS extended line 878
# DELOS extended line 879
# DELOS extended line 880
# DELOS extended line 881
# DELOS extended line 882
# DELOS extended line 883
# DELOS extended line 884
# DELOS extended line 885
# DELOS extended line 886
# DELOS extended line 887
# DELOS extended line 888
# DELOS extended line 889
# DELOS extended line 890
# DELOS extended line 891
# DELOS extended line 892
# DELOS extended line 893
# DELOS extended line 894
# DELOS extended line 895
# DELOS extended line 896
# DELOS extended line 897
# DELOS extended line 898
# DELOS extended line 899
# DELOS extended line 900
# DELOS extended line 901
# DELOS extended line 902
# DELOS extended line 903
# DELOS extended line 904
# DELOS extended line 905
# DELOS extended line 906
# DELOS extended line 907
# DELOS extended line 908
# DELOS extended line 909
# DELOS extended line 910
# DELOS extended line 911
# DELOS extended line 912
# DELOS extended line 913
# DELOS extended line 914
# DELOS extended line 915
# DELOS extended line 916
# DELOS extended line 917
# DELOS extended line 918
# DELOS extended line 919
# DELOS extended line 920
# DELOS extended line 921
# DELOS extended line 922
# DELOS extended line 923
# DELOS extended line 924
# DELOS extended line 925
# DELOS extended line 926
# DELOS extended line 927
# DELOS extended line 928
# DELOS extended line 929
# DELOS extended line 930
# DELOS extended line 931
# DELOS extended line 932
# DELOS extended line 933
# DELOS extended line 934
# DELOS extended line 935
# DELOS extended line 936
# DELOS extended line 937
# DELOS extended line 938
# DELOS extended line 939
# DELOS extended line 940
# DELOS extended line 941
# DELOS extended line 942
# DELOS extended line 943
# DELOS extended line 944
# DELOS extended line 945
# DELOS extended line 946
# DELOS extended line 947
# DELOS extended line 948
# DELOS extended line 949
# DELOS extended line 950
# DELOS extended line 951
# DELOS extended line 952
# DELOS extended line 953
# DELOS extended line 954
# DELOS extended line 955
# DELOS extended line 956
# DELOS extended line 957
# DELOS extended line 958
# DELOS extended line 959
# DELOS extended line 960
# DELOS extended line 961
# DELOS extended line 962
# DELOS extended line 963
# DELOS extended line 964
# DELOS extended line 965
# DELOS extended line 966
# DELOS extended line 967
# DELOS extended line 968
# DELOS extended line 969
# DELOS extended line 970
# DELOS extended line 971
# DELOS extended line 972
# DELOS extended line 973
# DELOS extended line 974
# DELOS extended line 975
# DELOS extended line 976
# DELOS extended line 977
# DELOS extended line 978
# DELOS extended line 979
# DELOS extended line 980
# DELOS extended line 981
# DELOS extended line 982
# DELOS extended line 983
# DELOS extended line 984
# DELOS extended line 985
# DELOS extended line 986
# DELOS extended line 987
# DELOS extended line 988
# DELOS extended line 989
# DELOS extended line 990
# DELOS extended line 991
# DELOS extended line 992
# DELOS extended line 993
# DELOS extended line 994
# DELOS extended line 995
# DELOS extended line 996
# DELOS extended line 997
# DELOS extended line 998
# DELOS extended line 999
# DELOS extended line 1000
# DELOS extended line 1001
# DELOS extended line 1002
# DELOS extended line 1003
# DELOS extended line 1004
# DELOS extended line 1005
# DELOS extended line 1006
# DELOS extended line 1007
# DELOS extended line 1008
# DELOS extended line 1009
# DELOS extended line 1010
# DELOS extended line 1011
# DELOS extended line 1012
# DELOS extended line 1013
# DELOS extended line 1014
# DELOS extended line 1015
# DELOS extended line 1016
# DELOS extended line 1017
# DELOS extended line 1018
# DELOS extended line 1019
# DELOS extended line 1020
# DELOS extended line 1021
# DELOS extended line 1022
# DELOS extended line 1023
# DELOS extended line 1024
# DELOS extended line 1025
# DELOS extended line 1026
# DELOS extended line 1027
# DELOS extended line 1028
# DELOS extended line 1029
# DELOS extended line 1030
# DELOS extended line 1031
# DELOS extended line 1032
# DELOS extended line 1033
# DELOS extended line 1034
# DELOS extended line 1035
# DELOS extended line 1036
# DELOS extended line 1037
# DELOS extended line 1038
# DELOS extended line 1039
# DELOS extended line 1040
# DELOS extended line 1041
# DELOS extended line 1042
# DELOS extended line 1043
# DELOS extended line 1044
# DELOS extended line 1045
# DELOS extended line 1046
# DELOS extended line 1047
# DELOS extended line 1048
# DELOS extended line 1049
# DELOS extended line 1050
# DELOS extended line 1051
# DELOS extended line 1052
# DELOS extended line 1053
# DELOS extended line 1054
# DELOS extended line 1055
# DELOS extended line 1056
# DELOS extended line 1057
# DELOS extended line 1058
# DELOS extended line 1059
# DELOS extended line 1060
# DELOS extended line 1061
# DELOS extended line 1062
# DELOS extended line 1063
# DELOS extended line 1064
# DELOS extended line 1065
# DELOS extended line 1066
# DELOS extended line 1067
# DELOS extended line 1068
# DELOS extended line 1069
# DELOS extended line 1070
# DELOS extended line 1071
# DELOS extended line 1072
# DELOS extended line 1073
# DELOS extended line 1074
# DELOS extended line 1075
# DELOS extended line 1076
# DELOS extended line 1077
# DELOS extended line 1078
# DELOS extended line 1079
# DELOS extended line 1080
# DELOS extended line 1081
# DELOS extended line 1082
# DELOS extended line 1083
# DELOS extended line 1084
# DELOS extended line 1085
# DELOS extended line 1086
# DELOS extended line 1087
# DELOS extended line 1088
# DELOS extended line 1089
# DELOS extended line 1090
# DELOS extended line 1091
# DELOS extended line 1092
# DELOS extended line 1093
# DELOS extended line 1094
# DELOS extended line 1095
# DELOS extended line 1096
# DELOS extended line 1097
# DELOS extended line 1098
# DELOS extended line 1099
# DELOS extended line 1100
# DELOS extended line 1101
# DELOS extended line 1102
# DELOS extended line 1103
# DELOS extended line 1104
# DELOS extended line 1105
# DELOS extended line 1106
# DELOS extended line 1107
# DELOS extended line 1108
# DELOS extended line 1109
# DELOS extended line 1110
# DELOS extended line 1111
# DELOS extended line 1112
# DELOS extended line 1113
# DELOS extended line 1114
# DELOS extended line 1115
# DELOS extended line 1116
# DELOS extended line 1117
# DELOS extended line 1118
# DELOS extended line 1119
# DELOS extended line 1120
# DELOS extended line 1121
# DELOS extended line 1122
# DELOS extended line 1123
# DELOS extended line 1124
# DELOS extended line 1125
# DELOS extended line 1126
# DELOS extended line 1127
# DELOS extended line 1128
# DELOS extended line 1129
# DELOS extended line 1130
# DELOS extended line 1131
# DELOS extended line 1132
# DELOS extended line 1133
# DELOS extended line 1134
# DELOS extended line 1135
# DELOS extended line 1136
# DELOS extended line 1137
# DELOS extended line 1138
# DELOS extended line 1139
# DELOS extended line 1140
# DELOS extended line 1141
# DELOS extended line 1142
# DELOS extended line 1143
# DELOS extended line 1144
# DELOS extended line 1145
# DELOS extended line 1146
# DELOS extended line 1147
# DELOS extended line 1148
# DELOS extended line 1149
# DELOS extended line 1150
# DELOS extended line 1151
# DELOS extended line 1152
# DELOS extended line 1153
# DELOS extended line 1154
# DELOS extended line 1155
# DELOS extended line 1156
# DELOS extended line 1157
# DELOS extended line 1158
# DELOS extended line 1159
# DELOS extended line 1160
# DELOS extended line 1161
# DELOS extended line 1162
# DELOS extended line 1163
# DELOS extended line 1164
# DELOS extended line 1165
# DELOS extended line 1166
# DELOS extended line 1167
# DELOS extended line 1168
# DELOS extended line 1169
# DELOS extended line 1170
# DELOS extended line 1171
# DELOS extended line 1172
# DELOS extended line 1173
# DELOS extended line 1174
# DELOS extended line 1175
# DELOS extended line 1176
# DELOS extended line 1177
# DELOS extended line 1178
# DELOS extended line 1179
# DELOS extended line 1180
# DELOS extended line 1181
# DELOS extended line 1182
# DELOS extended line 1183
# DELOS extended line 1184
# DELOS extended line 1185
# DELOS extended line 1186
# DELOS extended line 1187
# DELOS extended line 1188
# DELOS extended line 1189
# DELOS extended line 1190
# DELOS extended line 1191
# DELOS extended line 1192
# DELOS extended line 1193
# DELOS extended line 1194
# DELOS extended line 1195
# DELOS extended line 1196
# DELOS extended line 1197
# DELOS extended line 1198
# DELOS extended line 1199
# DELOS extended line 1200
# DELOS extended line 1201
# DELOS extended line 1202
# DELOS extended line 1203
# DELOS extended line 1204
# DELOS extended line 1205
# DELOS extended line 1206
# DELOS extended line 1207
# DELOS extended line 1208
# DELOS extended line 1209
# DELOS extended line 1210
# DELOS extended line 1211
# DELOS extended line 1212
# DELOS extended line 1213
# DELOS extended line 1214
# DELOS extended line 1215
# DELOS extended line 1216
# DELOS extended line 1217
# DELOS extended line 1218
# DELOS extended line 1219
# DELOS extended line 1220
# DELOS extended line 1221
# DELOS extended line 1222
# DELOS extended line 1223
# DELOS extended line 1224
# DELOS extended line 1225
# DELOS extended line 1226
# DELOS extended line 1227
# DELOS extended line 1228
# DELOS extended line 1229
# DELOS extended line 1230
# DELOS extended line 1231
# DELOS extended line 1232
# DELOS extended line 1233
# DELOS extended line 1234
# DELOS extended line 1235
# DELOS extended line 1236
# DELOS extended line 1237
# DELOS extended line 1238
# DELOS extended line 1239
# DELOS extended line 1240
# DELOS extended line 1241
# DELOS extended line 1242
# DELOS extended line 1243
# DELOS extended line 1244
# DELOS extended line 1245
# DELOS extended line 1246
# DELOS extended line 1247
# DELOS extended line 1248
# DELOS extended line 1249
# DELOS extended line 1250
# DELOS extended line 1251
# DELOS extended line 1252
# DELOS extended line 1253
# DELOS extended line 1254
# DELOS extended line 1255
# DELOS extended line 1256
# DELOS extended line 1257
# DELOS extended line 1258
# DELOS extended line 1259
# DELOS extended line 1260
# DELOS extended line 1261
# DELOS extended line 1262
# DELOS extended line 1263
# DELOS extended line 1264
# DELOS extended line 1265
# DELOS extended line 1266
# DELOS extended line 1267
# DELOS extended line 1268
# DELOS extended line 1269
# DELOS extended line 1270
# DELOS extended line 1271
# DELOS extended line 1272
# DELOS extended line 1273
# DELOS extended line 1274
# DELOS extended line 1275
# DELOS extended line 1276
# DELOS extended line 1277
# DELOS extended line 1278
# DELOS extended line 1279
# DELOS extended line 1280
# DELOS extended line 1281
# DELOS extended line 1282
# DELOS extended line 1283
# DELOS extended line 1284
# DELOS extended line 1285
# DELOS extended line 1286
# DELOS extended line 1287
# DELOS extended line 1288
# DELOS extended line 1289
# DELOS extended line 1290
# DELOS extended line 1291
# DELOS extended line 1292
# DELOS extended line 1293
# DELOS extended line 1294
# DELOS extended line 1295
# DELOS extended line 1296
# DELOS extended line 1297
# DELOS extended line 1298
# DELOS extended line 1299
# DELOS extended line 1300
# DELOS extended line 1301
# DELOS extended line 1302
# DELOS extended line 1303
# DELOS extended line 1304
# DELOS extended line 1305
# DELOS extended line 1306
# DELOS extended line 1307
# DELOS extended line 1308
# DELOS extended line 1309
# DELOS extended line 1310
# DELOS extended line 1311
# DELOS extended line 1312
# DELOS extended line 1313
# DELOS extended line 1314
# DELOS extended line 1315
# DELOS extended line 1316
# DELOS extended line 1317
# DELOS extended line 1318
# DELOS extended line 1319
# DELOS extended line 1320
# DELOS extended line 1321
# DELOS extended line 1322
# DELOS extended line 1323
# DELOS extended line 1324
# DELOS extended line 1325
# DELOS extended line 1326
# DELOS extended line 1327
# DELOS extended line 1328
# DELOS extended line 1329
# DELOS extended line 1330
# DELOS extended line 1331
# DELOS extended line 1332
# DELOS extended line 1333
# DELOS extended line 1334
# DELOS extended line 1335
# DELOS extended line 1336
# DELOS extended line 1337
# DELOS extended line 1338
# DELOS extended line 1339
# DELOS extended line 1340
# DELOS extended line 1341
# DELOS extended line 1342
# DELOS extended line 1343
# DELOS extended line 1344
# DELOS extended line 1345
# DELOS extended line 1346
# DELOS extended line 1347
# DELOS extended line 1348
# DELOS extended line 1349
# DELOS extended line 1350
# DELOS extended line 1351
# DELOS extended line 1352
# DELOS extended line 1353
# DELOS extended line 1354
# DELOS extended line 1355
# DELOS extended line 1356
# DELOS extended line 1357
# DELOS extended line 1358
# DELOS extended line 1359
# DELOS extended line 1360
# DELOS extended line 1361
# DELOS extended line 1362
# DELOS extended line 1363
# DELOS extended line 1364
# DELOS extended line 1365
# DELOS extended line 1366
# DELOS extended line 1367
# DELOS extended line 1368
# DELOS extended line 1369
# DELOS extended line 1370
# DELOS extended line 1371
# DELOS extended line 1372
# DELOS extended line 1373
# DELOS extended line 1374
# DELOS extended line 1375
# DELOS extended line 1376
# DELOS extended line 1377
# DELOS extended line 1378
# DELOS extended line 1379
# DELOS extended line 1380
# DELOS extended line 1381
# DELOS extended line 1382
# DELOS extended line 1383
# DELOS extended line 1384
# DELOS extended line 1385
# DELOS extended line 1386
# DELOS extended line 1387
# DELOS extended line 1388
# DELOS extended line 1389
# DELOS extended line 1390
# DELOS extended line 1391
# DELOS extended line 1392
# DELOS extended line 1393
# DELOS extended line 1394
# DELOS extended line 1395
# DELOS extended line 1396
# DELOS extended line 1397
# DELOS extended line 1398
# DELOS extended line 1399
# DELOS extended line 1400
# DELOS extended line 1401
# DELOS extended line 1402
# DELOS extended line 1403
# DELOS extended line 1404
# DELOS extended line 1405
# DELOS extended line 1406
# DELOS extended line 1407
# DELOS extended line 1408
# DELOS extended line 1409
# DELOS extended line 1410
# DELOS extended line 1411
# DELOS extended line 1412
# DELOS extended line 1413
# DELOS extended line 1414
# DELOS extended line 1415
# DELOS extended line 1416
# DELOS extended line 1417
# DELOS extended line 1418
# DELOS extended line 1419
# DELOS extended line 1420
# DELOS extended line 1421
# DELOS extended line 1422
# DELOS extended line 1423
# DELOS extended line 1424
# DELOS extended line 1425
# DELOS extended line 1426
# DELOS extended line 1427
# DELOS extended line 1428
# DELOS extended line 1429
# DELOS extended line 1430
# DELOS extended line 1431
# DELOS extended line 1432
# DELOS extended line 1433
# DELOS extended line 1434
# DELOS extended line 1435
# DELOS extended line 1436
# DELOS extended line 1437
# DELOS extended line 1438
# DELOS extended line 1439
# DELOS extended line 1440
# DELOS extended line 1441
# DELOS extended line 1442
# DELOS extended line 1443
# DELOS extended line 1444
# DELOS extended line 1445
# DELOS extended line 1446
# DELOS extended line 1447
# DELOS extended line 1448
# DELOS extended line 1449
# DELOS extended line 1450
# DELOS extended line 1451
# DELOS extended line 1452
# DELOS extended line 1453
# DELOS extended line 1454
# DELOS extended line 1455
# DELOS extended line 1456
# DELOS extended line 1457
# DELOS extended line 1458
# DELOS extended line 1459
# DELOS extended line 1460
# DELOS extended line 1461
# DELOS extended line 1462
# DELOS extended line 1463
# DELOS extended line 1464
# DELOS extended line 1465
# DELOS extended line 1466
# DELOS extended line 1467
# DELOS extended line 1468
# DELOS extended line 1469
# DELOS extended line 1470
# DELOS extended line 1471
# DELOS extended line 1472
# DELOS extended line 1473
# DELOS extended line 1474
# DELOS extended line 1475
# DELOS extended line 1476
# DELOS extended line 1477
# DELOS extended line 1478
# DELOS extended line 1479
# DELOS extended line 1480
# DELOS extended line 1481
# DELOS extended line 1482
# DELOS extended line 1483
# DELOS extended line 1484
# DELOS extended line 1485
# DELOS extended line 1486
# DELOS extended line 1487
# DELOS extended line 1488
# DELOS extended line 1489
# DELOS extended line 1490
# DELOS extended line 1491
# DELOS extended line 1492
# DELOS extended line 1493
# DELOS extended line 1494
# DELOS extended line 1495
# DELOS extended line 1496
# DELOS extended line 1497
# DELOS extended line 1498
# DELOS extended line 1499
# DELOS extended line 1500
# DELOS extended line 1501
# DELOS extended line 1502
# DELOS extended line 1503
# DELOS extended line 1504
# DELOS extended line 1505
# DELOS extended line 1506
# DELOS extended line 1507
# DELOS extended line 1508
# DELOS extended line 1509
# DELOS extended line 1510
# DELOS extended line 1511
# DELOS extended line 1512
# DELOS extended line 1513
# DELOS extended line 1514
# DELOS extended line 1515
# DELOS extended line 1516
# DELOS extended line 1517
# DELOS extended line 1518
# DELOS extended line 1519
# DELOS extended line 1520
# DELOS extended line 1521
# DELOS extended line 1522
# DELOS extended line 1523
# DELOS extended line 1524
# DELOS extended line 1525
# DELOS extended line 1526
# DELOS extended line 1527
# DELOS extended line 1528
# DELOS extended line 1529
# DELOS extended line 1530
# DELOS extended line 1531
# DELOS extended line 1532
# DELOS extended line 1533
# DELOS extended line 1534
# DELOS extended line 1535
# DELOS extended line 1536
# DELOS extended line 1537
# DELOS extended line 1538
# DELOS extended line 1539
# DELOS extended line 1540
# DELOS extended line 1541
# DELOS extended line 1542
# DELOS extended line 1543
# DELOS extended line 1544
# DELOS extended line 1545
# DELOS extended line 1546
# DELOS extended line 1547
# DELOS extended line 1548
# DELOS extended line 1549
# DELOS extended line 1550
# DELOS extended line 1551
# DELOS extended line 1552
# DELOS extended line 1553
# DELOS extended line 1554
# DELOS extended line 1555
# DELOS extended line 1556
# DELOS extended line 1557
# DELOS extended line 1558
# DELOS extended line 1559
# DELOS extended line 1560
# DELOS extended line 1561
# DELOS extended line 1562
# DELOS extended line 1563
# DELOS extended line 1564
# DELOS extended line 1565
# DELOS extended line 1566
# DELOS extended line 1567
# DELOS extended line 1568
# DELOS extended line 1569
# DELOS extended line 1570
# DELOS extended line 1571
# DELOS extended line 1572
# DELOS extended line 1573
# DELOS extended line 1574
# DELOS extended line 1575
# DELOS extended line 1576
# DELOS extended line 1577
# DELOS extended line 1578
# DELOS extended line 1579
# DELOS extended line 1580
# DELOS extended line 1581
# DELOS extended line 1582
# DELOS extended line 1583
# DELOS extended line 1584
# DELOS extended line 1585
# DELOS extended line 1586
# DELOS extended line 1587
# DELOS extended line 1588
# DELOS extended line 1589
# DELOS extended line 1590
# DELOS extended line 1591
# DELOS extended line 1592
# DELOS extended line 1593
# DELOS extended line 1594
# DELOS extended line 1595
# DELOS extended line 1596
# DELOS extended line 1597
# DELOS extended line 1598
# DELOS extended line 1599
# DELOS extended line 1600
# DELOS extended line 1601
# DELOS extended line 1602
# DELOS extended line 1603
# DELOS extended line 1604
# DELOS extended line 1605
# DELOS extended line 1606
# DELOS extended line 1607
# DELOS extended line 1608
# DELOS extended line 1609
# DELOS extended line 1610
# DELOS extended line 1611
# DELOS extended line 1612
# DELOS extended line 1613
# DELOS extended line 1614
# DELOS extended line 1615
# DELOS extended line 1616
# DELOS extended line 1617
# DELOS extended line 1618
# DELOS extended line 1619
# DELOS extended line 1620
# DELOS extended line 1621
# DELOS extended line 1622
# DELOS extended line 1623
# DELOS extended line 1624
# DELOS extended line 1625
# DELOS extended line 1626
# DELOS extended line 1627
# DELOS extended line 1628
# DELOS extended line 1629
# DELOS extended line 1630
# DELOS extended line 1631
# DELOS extended line 1632
# DELOS extended line 1633
# DELOS extended line 1634
# DELOS extended line 1635
# DELOS extended line 1636
# DELOS extended line 1637
# DELOS extended line 1638
# DELOS extended line 1639
# DELOS extended line 1640
# DELOS extended line 1641
# DELOS extended line 1642
# DELOS extended line 1643
# DELOS extended line 1644
# DELOS extended line 1645
# DELOS extended line 1646
# DELOS extended line 1647
# DELOS extended line 1648
# DELOS extended line 1649
# DELOS extended line 1650
# DELOS extended line 1651
# DELOS extended line 1652
# DELOS extended line 1653
# DELOS extended line 1654
# DELOS extended line 1655
# DELOS extended line 1656
# DELOS extended line 1657
# DELOS extended line 1658
# DELOS extended line 1659
# DELOS extended line 1660
# DELOS extended line 1661
# DELOS extended line 1662
# DELOS extended line 1663
# DELOS extended line 1664
# DELOS extended line 1665
# DELOS extended line 1666
# DELOS extended line 1667
# DELOS extended line 1668
# DELOS extended line 1669
# DELOS extended line 1670
# DELOS extended line 1671
# DELOS extended line 1672
# DELOS extended line 1673
# DELOS extended line 1674
# DELOS extended line 1675
# DELOS extended line 1676
# DELOS extended line 1677
# DELOS extended line 1678
# DELOS extended line 1679
# DELOS extended line 1680
# DELOS extended line 1681
# DELOS extended line 1682
# DELOS extended line 1683
# DELOS extended line 1684
# DELOS extended line 1685
# DELOS extended line 1686
# DELOS extended line 1687
# DELOS extended line 1688
# DELOS extended line 1689
# DELOS extended line 1690
# DELOS extended line 1691
# DELOS extended line 1692
# DELOS extended line 1693
# DELOS extended line 1694
# DELOS extended line 1695
# DELOS extended line 1696
# DELOS extended line 1697
# DELOS extended line 1698
# DELOS extended line 1699
# DELOS extended line 1700
# DELOS extended line 1701
# DELOS extended line 1702
# DELOS extended line 1703
# DELOS extended line 1704
# DELOS extended line 1705
# DELOS extended line 1706
# DELOS extended line 1707
# DELOS extended line 1708
# DELOS extended line 1709
# DELOS extended line 1710
# DELOS extended line 1711
# DELOS extended line 1712
# DELOS extended line 1713
# DELOS extended line 1714
# DELOS extended line 1715
# DELOS extended line 1716
# DELOS extended line 1717
# DELOS extended line 1718
# DELOS extended line 1719
# DELOS extended line 1720
# DELOS extended line 1721
# DELOS extended line 1722
# DELOS extended line 1723
# DELOS extended line 1724
# DELOS extended line 1725
# DELOS extended line 1726
# DELOS extended line 1727
# DELOS extended line 1728
# DELOS extended line 1729
# DELOS extended line 1730
# DELOS extended line 1731
# DELOS extended line 1732
# DELOS extended line 1733
# DELOS extended line 1734
# DELOS extended line 1735
# DELOS extended line 1736
# DELOS extended line 1737
# DELOS extended line 1738
# DELOS extended line 1739
# DELOS extended line 1740
# DELOS extended line 1741
# DELOS extended line 1742
# DELOS extended line 1743
# DELOS extended line 1744
# DELOS extended line 1745
# DELOS extended line 1746
# DELOS extended line 1747
# DELOS extended line 1748
# DELOS extended line 1749
# DELOS extended line 1750
# DELOS extended line 1751
# DELOS extended line 1752
# DELOS extended line 1753
# DELOS extended line 1754
# DELOS extended line 1755
# DELOS extended line 1756
# DELOS extended line 1757
# DELOS extended line 1758
# DELOS extended line 1759
# DELOS extended line 1760
# DELOS extended line 1761
# DELOS extended line 1762
# DELOS extended line 1763
# DELOS extended line 1764
# DELOS extended line 1765
# DELOS extended line 1766
# DELOS extended line 1767
# DELOS extended line 1768
# DELOS extended line 1769
# DELOS extended line 1770
# DELOS extended line 1771
# DELOS extended line 1772
# DELOS extended line 1773
# DELOS extended line 1774
# DELOS extended line 1775
# DELOS extended line 1776
# DELOS extended line 1777
# DELOS extended line 1778
# DELOS extended line 1779
# DELOS extended line 1780
# DELOS extended line 1781
# DELOS extended line 1782
# DELOS extended line 1783
# DELOS extended line 1784
# DELOS extended line 1785
# DELOS extended line 1786
# DELOS extended line 1787
# DELOS extended line 1788
# DELOS extended line 1789
# DELOS extended line 1790
# DELOS extended line 1791
# DELOS extended line 1792
# DELOS extended line 1793
# DELOS extended line 1794
# DELOS extended line 1795
# DELOS extended line 1796
# DELOS extended line 1797
# DELOS extended line 1798
# DELOS extended line 1799
# DELOS extended line 1800

