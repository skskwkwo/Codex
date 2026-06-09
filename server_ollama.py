#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DELOS · Ollama Local Server Integration
우주적 지성 · Ollama 로컬 모델 연동
내 컴퓨터의 Ollama 서버 (http://localhost:11434) 와 통신
"""
import os
import sys
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

VERSION = "1.0.0"
APP_NAME = "DELOS Ollama Bridge"
BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "logs"
DATA_DIR = BASE_DIR / "data"
LOG_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / "ollama.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
log = logging.getLogger("DELOS-Ollama")

DEFAULT_HOST = "http://localhost:11434"
DEFAULT_TIMEOUT = 120


class OllamaClient:
    def __init__(self, host: str = DEFAULT_HOST):
        self.host = host
        self.timeout = DEFAULT_TIMEOUT

    def set_host(self, host: str):
        self.host = host.strip().rstrip("/")

    async def list_models(self) -> List[Dict]:
        try:
            url = f"{self.host}/api/tags"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return data.get("models", [])
        except Exception as e:
            log.warning(f"ollama list error: {e}")
            return []

    async def show_model(self, name: str) -> Dict:
        try:
            url = f"{self.host}/api/show"
            data = json.dumps({"name": name}).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            return {"error": str(e)}

    async def generate(self, prompt: str, model: str, options: Optional[Dict] = None,
                      system: Optional[str] = None, template: Optional[str] = None,
                      context: Optional[List] = None) -> Dict:
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False
        }
        if options:
            payload["options"] = options
        if system:
            payload["system"] = system
        if template:
            payload["template"] = template
        if context:
            payload["context"] = context
        try:
            url = f"{self.host}/api/generate"
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                result = json.loads(resp.read().decode("utf-8"))
            return {
                "text": result.get("response", ""),
                "model": model,
                "context": result.get("context"),
                "success": True,
                "total_duration": result.get("total_duration", 0),
                "eval_count": result.get("eval_count", 0),
                "eval_duration": result.get("eval_duration", 0)
            }
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            return {"error": f"HTTP {e.code}: {body[:200]}", "text": "", "success": False}
        except Exception as e:
            log.exception("ollama generate error")
            return {"error": str(e), "text": "", "success": False}

    async def chat(self, messages: List[Dict], model: str, options: Optional[Dict] = None) -> Dict:
        payload = {
            "model": model,
            "messages": messages,
            "stream": False
        }
        if options:
            payload["options"] = options
        try:
            url = f"{self.host}/api/chat"
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                result = json.loads(resp.read().decode("utf-8"))
            return {
                "message": result.get("message", {}),
                "model": model,
                "success": True,
                "total_duration": result.get("total_duration", 0),
                "eval_count": result.get("eval_count", 0)
            }
        except Exception as e:
            log.exception("ollama chat error")
            return {"error": str(e), "success": False}

    async def pull_model(self, name: str) -> Dict:
        try:
            url = f"{self.host}/api/pull"
            data = json.dumps({"name": name, "stream": False}).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=600) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            return {"error": str(e)}

    async def embeddings(self, prompt: str, model: str) -> Dict:
        try:
            url = f"{self.host}/api/embeddings"
            data = json.dumps({"model": model, "prompt": prompt}).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            return {"error": str(e)}


client = OllamaClient()


class OllamaHandler(BaseHTTPRequestHandler):
    server_version = "DELOS-Ollama/1.0"

    def log_message(self, fmt, *args):
        log.debug(fmt % args)

    def _send(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS, DELETE")
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
            self._send({"status": "ok", "service": APP_NAME, "ollama_host": client.host})
        elif path == "/models":
            loop = asyncio.new_event_loop()
            try:
                models = loop.run_until_complete(client.list_models())
            finally:
                loop.close()
            self._send({"models": models, "host": client.host})
        else:
            self._send({"error": "Not found"}, 404)

    def do_POST(self):
        from urllib.parse import urlparse
        path = urlparse(self.path).path
        body = self._read_body()
        loop = asyncio.new_event_loop()
        try:
            if path == "/host":
                client.set_host(body.get("host", DEFAULT_HOST))
                self._send({"success": True, "host": client.host})
            elif path == "/generate":
                result = loop.run_until_complete(client.generate(
                    body.get("prompt", ""),
                    body.get("model", "llama3"),
                    body.get("options"),
                    body.get("system"),
                    body.get("template"),
                    body.get("context")
                ))
                self._send(result)
            elif path == "/chat":
                result = loop.run_until_complete(client.chat(
                    body.get("messages", []),
                    body.get("model", "llama3"),
                    body.get("options")
                ))
                self._send(result)
            elif path == "/pull":
                result = loop.run_until_complete(client.pull_model(body.get("name", "")))
                self._send(result)
            elif path == "/embeddings":
                result = loop.run_until_complete(client.embeddings(
                    body.get("prompt", ""),
                    body.get("model", "llama3")
                ))
                self._send(result)
            else:
                self._send({"error": "Not found"}, 404)
        finally:
            loop.close()


class ThreadedServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


def run(host="127.0.0.1", port=8002):
    server = ThreadedServer((host, port), OllamaHandler)
    log.info(f"DELOS Ollama bridge on http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    h = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
    p = int(sys.argv[2]) if len(sys.argv) > 2 else 8002
    run(h, p)
