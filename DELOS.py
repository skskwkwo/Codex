#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DELOS - local server and API gateway."""
from __future__ import annotations
import argparse, asyncio, json, logging, mimetypes, os, secrets, threading, time, urllib.parse, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
VERSION='1.1.0'; HOST=os.getenv('DELOS_HOST','127.0.0.1'); PORT=int(os.getenv('DELOS_PORT','8765'))
BASE_DIR=Path(__file__).resolve().parent; DATA_DIR=BASE_DIR/'data'; LOG_DIR=BASE_DIR/'logs'
for d in (DATA_DIR,LOG_DIR): d.mkdir(parents=True,exist_ok=True)
logging.basicConfig(level=logging.INFO,format='%(asctime)s [%(levelname)s] %(message)s',handlers=[logging.FileHandler(LOG_DIR/'delos.log',encoding='utf-8'),logging.StreamHandler()]); log=logging.getLogger('DELOS')
def now_iso(): return time.strftime('%Y-%m-%dT%H:%M:%S')
def uid(prefix='id'): return f'{prefix}-{secrets.token_hex(6)}'
def read_json(path,default):
    try: return json.loads(path.read_text(encoding='utf-8')) if path.exists() else default
    except (OSError,json.JSONDecodeError): return default
def write_json(path,value):
    tmp=path.with_suffix(path.suffix+'.tmp'); tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8'); tmp.replace(path)
class Store:
    def __init__(self): self.conversations=DATA_DIR/'conversations.json'; self.config=DATA_DIR/'config.json'
    def convs(self):
        v=read_json(self.conversations,[]); return v if isinstance(v,list) else []
    def save_convs(self,v): write_json(self.conversations,v)
    def cfg(self):
        v=read_json(self.config,{}); return v if isinstance(v,dict) else {}
class AI:
    def __init__(self): self.gemini_key=os.getenv('GEMINI_API_KEY',''); self.ollama_host=os.getenv('OLLAMA_HOST','http://127.0.0.1:11434').rstrip('/')
    @staticmethod
    def request(url,payload=None,timeout=30):
        data=None if payload is None else json.dumps(payload).encode(); req=urllib.request.Request(url,data=data,headers={'Content-Type':'application/json','User-Agent':'DELOS/1.1'})
        with urllib.request.urlopen(req,timeout=timeout) as r: return json.loads(r.read().decode('utf-8'))
    async def gemini(self,prompt,model,max_tokens,temperature):
        if not self.gemini_key: return {'success':False,'text':'','error':'Gemini API 키가 설정되지 않았습니다.'}
        model='gemini-2.5-pro' if model=='gemini-2.5-pro' else 'gemini-2.5-flash'; url=f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={urllib.parse.quote(self.gemini_key)}'
        payload={'contents':[{'role':'user','parts':[{'text':prompt}]}],'systemInstruction':{'parts':[{'text':'당신은 DELOS입니다. 친절하고 지적인 AI 어시스턴트로 한국어로 응답합니다.'}]},'generationConfig':{'temperature':temperature,'maxOutputTokens':max_tokens}}
        try:
            r=await asyncio.to_thread(self.request,url,payload,60); parts=r.get('candidates',[{}])[0].get('content',{}).get('parts',[]); return {'success':True,'text':''.join(p.get('text','') for p in parts),'model':model}
        except Exception as e: log.exception('Gemini request failed'); return {'success':False,'text':'','error':str(e)}
    async def ollama(self,prompt,model,max_tokens,temperature):
        payload={'model':model or 'llama3','prompt':prompt,'stream':False,'options':{'temperature':temperature,'num_predict':max_tokens}}
        try:
            r=await asyncio.to_thread(self.request,self.ollama_host+'/api/generate',payload,120); return {'success':True,'text':r.get('response',''),'model':model or 'llama3'}
        except Exception as e: return {'success':False,'text':'','error':str(e)}
    async def models(self):
        try: return (await asyncio.to_thread(self.request,self.ollama_host+'/api/tags',None,5)).get('models',[])
        except Exception: return []
    async def ddg(self,q):
        if not q.strip(): return {'success':True,'query':q,'results':[]}
        url='https://api.duckduckgo.com/?'+urllib.parse.urlencode({'q':q,'format':'json','no_html':1,'skip_disambig':1})
        try:
            d=await asyncio.to_thread(self.request,url,None,15); out=[]
            if d.get('AbstractText'): out.append({'title':d.get('Heading','요약'),'url':d.get('AbstractURL',''),'snippet':d['AbstractText']})
            for t in d.get('RelatedTopics',[]):
                if t.get('Text'): out.append({'title':t['Text'].split(' - ')[0],'url':t.get('FirstURL',''),'snippet':t['Text']})
                for s in t.get('Topics',[]):
                    if s.get('Text'): out.append({'title':s['Text'].split(' - ')[0],'url':s.get('FirstURL',''),'snippet':s['Text']})
            return {'success':True,'query':q,'results':out[:10]}
        except Exception as e: return {'success':False,'query':q,'results':[],'error':str(e)}
    async def wiki(self,q):
        url='https://ko.wikipedia.org/w/api.php?'+urllib.parse.urlencode({'action':'query','list':'search','srsearch':q,'format':'json','srlimit':5,'origin':'*'})
        try:
            d=await asyncio.to_thread(self.request,url,None,15); out=[]
            for x in d.get('query',{}).get('search',[]):
                title=x.get('title',''); out.append({'title':title,'url':'https://ko.wikipedia.org/wiki/'+urllib.parse.quote(title),'snippet':x.get('snippet','').replace('<span class="searchmatch">','').replace('</span>','')})
            return {'success':True,'query':q,'results':out}
        except Exception as e: return {'success':False,'query':q,'results':[],'error':str(e)}
    async def crawl(self,target,max_chars=8000):
        p=urllib.parse.urlparse(target)
        if p.scheme not in ('http','https') or not p.netloc: return {'success':False,'text':'','error':'http/https URL만 허용됩니다.'}
        proxy='https://api.allorigins.win/get?'+urllib.parse.urlencode({'url':target})
        try:
            d=await asyncio.to_thread(self.request,proxy,None,20); import re; text=re.sub(r'<script[\s\S]*?</script>',' ',d.get('contents',''),flags=re.I); text=re.sub(r'<style[\s\S]*?</style>',' ',text,flags=re.I); text=re.sub(r'<[^>]+>',' ',text); text=re.sub(r'\s+',' ',text).strip(); return {'success':True,'url':target,'text':text[:max_chars],'length':len(text)}
        except Exception as e: return {'success':False,'text':'','error':str(e)}
def run(coro): return asyncio.run(coro)
class Handler(BaseHTTPRequestHandler):
    server_version='DELOS/1.1'
    def log_message(self,fmt,*args): log.info('%s - %s',self.address_string(),fmt%args)
    def send_json(self,data,status=200):
        raw=json.dumps(data,ensure_ascii=False).encode(); self.send_response(status); self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Access-Control-Allow-Origin','*'); self.send_header('Access-Control-Allow-Methods','GET,POST,PUT,DELETE,OPTIONS'); self.send_header('Access-Control-Allow-Headers','Content-Type, Authorization'); self.send_header('Cache-Control','no-store'); self.send_header('Content-Length',str(len(raw))); self.end_headers(); self.wfile.write(raw)
    def send_file(self,path):
        try:
            r=path.resolve()
            if BASE_DIR not in r.parents and r!=BASE_DIR: return self.send_json({'error':'Forbidden'},403)
            if not r.is_file(): return self.send_json({'error':'Not found'},404)
            raw=r.read_bytes(); ct=mimetypes.guess_type(str(r))[0] or 'application/octet-stream'; ct += '; charset=utf-8' if ct.startswith('text/') or r.suffix in ('.js','.json') else ''
            self.send_response(200); self.send_header('Content-Type',ct); self.send_header('Cache-Control','no-cache'); self.send_header('Content-Length',str(len(raw))); self.end_headers(); self.wfile.write(raw)
        except OSError as e: self.send_json({'error':str(e)},500)
    def body(self):
        try:
            n=int(self.headers.get('Content-Length','0'))
            if n<=0 or n>2000000: return {}
            v=json.loads(self.rfile.read(n).decode()); return v if isinstance(v,dict) else {}
        except (ValueError,json.JSONDecodeError,UnicodeDecodeError): return {}
    def do_OPTIONS(self): self.send_response(204); self.send_header('Access-Control-Allow-Origin','*'); self.send_header('Access-Control-Allow-Methods','GET,POST,PUT,DELETE,OPTIONS'); self.send_header('Access-Control-Allow-Headers','Content-Type, Authorization'); self.end_headers()
    def do_GET(self):
        p=urllib.parse.urlparse(self.path); path=p.path; ai,store=self.server.ai,self.server.store
        if path=='/api/health': return self.send_json({'status':'ok','app':'DELOS','version':VERSION,'has_gemini':bool(ai.gemini_key),'ollama_host':ai.ollama_host,'time':now_iso()})
        if path=='/api/ollama/models': return self.send_json({'success':True,'models':run(ai.models())})
        if path=='/api/conversations':
            user=urllib.parse.parse_qs(p.query).get('user',['default'])[0]; return self.send_json({'conversations':[c for c in store.convs() if c.get('user','default')==user]})
        if path.startswith('/api/conversations/'):
            cid=path.rsplit('/',1)[-1]; c=next((x for x in store.convs() if x.get('id')==cid),None); return self.send_json({'conversation':c} if c else {'error':'Not found'},200 if c else 404)
        return self.send_file(BASE_DIR/(urllib.parse.unquote(path.lstrip('/')) or 'DELOS.html'))
    def do_POST(self):
        path=urllib.parse.urlparse(self.path).path; b,ai,store=self.body(),self.server.ai,self.server.store
        if path=='/api/chat':
            prompt=str(b.get('prompt') or b.get('message') or '').strip()
            if not prompt: return self.send_json({'success':False,'error':'prompt가 비어 있습니다.'},400)
            if b.get('api_key'): ai.gemini_key=str(b['api_key']).strip()
            model=str(b.get('model','gemini-2.5-flash')); mt=int(b.get('max_tokens',8192)); temp=float(b.get('temperature',0.9)); r=run(ai.ollama(prompt,model,mt,temp)) if ('ollama' in model or b.get('ollama')) else run(ai.gemini(prompt,model,mt,temp)); return self.send_json(r,200 if r.get('success') else 502)
        if path=='/api/search/duckduckgo': return self.send_json(run(ai.ddg(str(b.get('query','')))))
        if path=='/api/search/wiki': return self.send_json(run(ai.wiki(str(b.get('query','')))))
        if path=='/api/research':
            q=str(b.get('query','')); d,w=run(ai.ddg(q)),run(ai.wiki(q)); return self.send_json({'success':d.get('success') or w.get('success'),'query':q,'duckduckgo':d.get('results',[]),'wikipedia':w.get('results',[])})
        if path=='/api/crawl': return self.send_json(run(ai.crawl(str(b.get('url','')))))
        if path=='/api/conversations':
            c={'id':uid('conv'),'title':b.get('title','새 대화'),'messages':b.get('messages',[]),'model':b.get('model','gemini-2.5-flash'),'user':b.get('user','default'),'created_at':now_iso(),'updated_at':now_iso()}; items=store.convs(); items.insert(0,c); store.save_convs(items); return self.send_json({'success':True,'conversation':c})
        if path=='/api/config':
            cfg=store.cfg(); cfg.update(b); write_json(store.config,cfg); return self.send_json({'success':True,'config':cfg})
        if path=='/api/ollama/host':
            host=str(b.get('host',ai.ollama_host)).strip().rstrip('/'); p=urllib.parse.urlparse(host)
            if p.scheme not in ('http','https') or not p.netloc: return self.send_json({'success':False,'error':'올바른 HTTP(S) 호스트가 아닙니다.'},400)
            ai.ollama_host=host; return self.send_json({'success':True,'ollama_host':host})
        return self.send_json({'error':'Not found'},404)
    def do_PUT(self):
        path=urllib.parse.urlparse(self.path).path
        if not path.startswith('/api/conversations/'): return self.send_json({'error':'Not found'},404)
        cid=path.rsplit('/',1)[-1]; b=self.body(); items=self.server.store.convs()
        for c in items:
            if c.get('id')==cid: c.update(b); c['updated_at']=now_iso(); self.server.store.save_convs(items); return self.send_json({'success':True,'conversation':c})
        return self.send_json({'error':'Not found'},404)
    def do_DELETE(self):
        path=urllib.parse.urlparse(self.path).path
        if path.startswith('/api/conversations/'):
            cid=path.rsplit('/',1)[-1]; self.server.store.save_convs([c for c in self.server.store.convs() if c.get('id')!=cid]); return self.send_json({'success':True})
        return self.send_json({'error':'Not found'},404)
class Server(ThreadingHTTPServer):
    allow_reuse_address=True; daemon_threads=True
    def __init__(self,addr): super().__init__(addr,Handler); self.store=Store(); self.ai=AI()
def main():
    ap=argparse.ArgumentParser(description='DELOS local server'); ap.add_argument('--host',default=HOST); ap.add_argument('--port',type=int,default=PORT); ap.add_argument('--no-browser',action='store_true'); a=ap.parse_args(); s=Server((a.host,a.port)); url=f'http://{a.host}:{a.port}/'; print(f'DELOS {VERSION} -> {url}')
    if not a.no_browser: import webbrowser; threading.Timer(1.0,lambda:webbrowser.open(url)).start()
    try: s.serve_forever()
    except KeyboardInterrupt: pass
    finally: s.server_close()
if __name__=='__main__': main()
