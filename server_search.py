#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DELOS 쨌 Gemini API Server
?곗＜??吏??쨌 ?쒕??섏씠 3.5 Flash 쨌 3.1 Pro ?곕룞 ?쒕쾭
"""
import os
import json
import time
import asyncio
import logging
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path
from typing import Optional, Dict, List, Any
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from concurrent.futures import ThreadPoolExecutor

VERSION = "1.0.0"
APP_NAME = "DELOS Gemini Server"
BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "logs"
DATA_DIR = BASE_DIR / "data"
LOG_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / "gemini.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
log = logging.getLogger("DELOS-Gemini")

GEMINI_MODELS = {
    "gemini-2.5-flash": {
        "name": "Gemini 3.5 Flash (2.5 Flash)",
        "endpoint": "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash",
        "max_tokens": 32768,
        "streaming": True,
        "tools": True
    },
    "gemini-2.5-pro": {
        "name": "Gemini 3.1 Pro (2.5 Pro)",
        "endpoint": "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro",
        "max_tokens": 32768,
        "streaming": True,
        "tools": True
    },
    "gemini-2.0-flash": {
        "name": "Gemini 2.0 Flash",
        "endpoint": "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash",
        "max_tokens": 8192,
        "streaming": True
    }
}

DEFAULT_PERSONA = "?뱀떊? DELOS?낅땲?? 媛먯젙?곸씠怨?移쒓렐?섎ŉ 吏?곸씤 AI ?댁떆?ㅽ꽩?몄엯?덈떎. ?ъ슜?먯? ?곕쑜?섍퀬 ?먯뿰?ㅻ윭????붾? ?섎늻硫???긽 ?꾩????섎뒗 ?뺣낫瑜??쒓났?⑸땲?? ?쒓뎅?대줈 ?묐떟?⑸땲??"

SAFETY_SETTINGS = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
]


class GeminiClient:
    def __init__(self, api_key: str = ""):
        self.api_key = api_key
        self.session_history: Dict[str, List[Dict]] = {}

    def set_key(self, key: str):
        self.api_key = key.strip()

    async def generate(self, prompt: str, model: str = "gemini-2.5-flash",
                      max_tokens: int = 8192, temperature: float = 0.9,
                      system_prompt: Optional[str] = None,
                      use_search: bool = False,
                      history: Optional[List[Dict]] = None) -> Dict:
        if not self.api_key:
            return {"error": "API ???놁쓬", "text": "", "success": False}
        cfg = GEMINI_MODELS.get(model, GEMINI_MODELS["gemini-2.5-flash"])
        url = f"{cfg['endpoint']}:generateContent?key={self.api_key}"
        contents = []
        if history:
            for h in history:
                role = "user" if h.get("role") == "user" else "model"
                contents.append({"role": role, "parts": [{"text": h.get("text", "")}]})
        contents.append({"role": "user", "parts": [{"text": prompt}]})
        payload = {
            "contents": contents,
            "systemInstruction": {"parts": [{"text": system_prompt or DEFAULT_PERSONA}]},
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": min(max_tokens, cfg["max_tokens"]),
                "topP": 0.95
            },
            "safetySettings": SAFETY_SETTINGS
        }
        if use_search and cfg.get("tools"):
            payload["tools"] = [{"googleSearch": {}}]
        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read().decode("utf-8"))
            text = ""
            candidates = result.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                text = "".join(p.get("text", "") for p in parts)
            return {
                "text": text,
                "model": model,
                "success": True,
                "usage": result.get("usageMetadata", {})
            }
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8", errors="replace")
            log.error(f"Gemini HTTP {e.code}: {error_body[:200]}")
            return {"error": f"HTTP {e.code}: {error_body[:200]}", "text": "", "success": False}
        except Exception as e:
            log.exception("gemini error")
            return {"error": str(e), "text": "", "success": False}

    async def stream_generate(self, prompt: str, model: str = "gemini-2.5-flash",
                             max_tokens: int = 8192, temperature: float = 0.9,
                             system_prompt: Optional[str] = None):
        cfg = GEMINI_MODELS.get(model, GEMINI_MODELS["gemini-2.5-flash"])
        url = f"{cfg['endpoint']}:streamGenerateContent?key={self.api_key}&alt=sse"
        contents = [{"role": "user", "parts": [{"text": prompt}]}]
        payload = {
            "contents": contents,
            "systemInstruction": {"parts": [{"text": system_prompt or DEFAULT_PERSONA}]},
            "generationConfig": {"temperature": temperature, "maxOutputTokens": min(max_tokens, cfg["max_tokens"])},
            "safetySettings": SAFETY_SETTINGS
        }
        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                for line in resp:
                    line = line.decode("utf-8", errors="replace").strip()
                    if line.startswith("data: "):
                        try:
                            chunk = json.loads(line[6:])
                            candidates = chunk.get("candidates", [])
                            for c in candidates:
                                parts = c.get("content", {}).get("parts", [])
                                for p in parts:
                                    if p.get("text"):
                                        yield p["text"]
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            log.exception("stream error")
            yield f"\n[Error: {e}]"


client = GeminiClient()


class GeminiHandler(BaseHTTPRequestHandler):
    server_version = "DELOS-Gemini/1.0"

    def log_message(self, fmt, *args):
        log.debug(fmt % args)

    def _send(self, data, status=200, ct="application/json"):
        body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", ct)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self):
        try:
            n = int(self.headers.get("Content-Length", 0))
            if n == 0:
                return {}
            return json.loads(self.rfile.read(n).decode("utf-8"))
        except Exception:
            return {}

    def do_OPTIONS(self):
        self._send({}, 204)

    def do_GET(self):
        from urllib.parse import urlparse
        path = urlparse(self.path).path
        if path == "/health":
            self._send({"status": "ok", "service": APP_NAME, "version": VERSION, "models": list(GEMINI_MODELS.keys())})
        elif path == "/models":
            self._send({"models": GEMINI_MODELS, "default": "gemini-2.5-flash"})
        else:
            self._send({"error": "Not found"}, 404)

    def do_POST(self):
        from urllib.parse import urlparse
        path = urlparse(self.path).path
        body = self._read_body()

        if path == "/generate":
            api_key = body.get("api_key") or client.api_key
            if api_key:
                client.set_key(api_key)
            loop = asyncio.new_event_loop()
            try:
                result = loop.run_until_complete(client.generate(
                    body.get("prompt", ""),
                    body.get("model", "gemini-2.5-flash"),
                    body.get("max_tokens", 8192),
                    body.get("temperature", 0.9),
                    body.get("system_prompt"),
                    body.get("use_search", False),
                    body.get("history")
                ))
            finally:
                loop.close()
            self._send(result)
        elif path == "/key":
            client.set_key(body.get("key", ""))
            self._send({"success": True, "has_key": bool(client.api_key)})
        else:
            self._send({"error": "Not found"}, 404)


class ThreadedServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


def run(host="127.0.0.1", port=8001):
    server = ThreadedServer((host, port), GeminiHandler)
    log.info(f"DELOS Gemini server on http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("shutting down")
        server.shutdown()


if __name__ == "__main__":
    import sys
    host = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8001
    run(host, port)
