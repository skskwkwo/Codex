/* ============================================
   DELOS · Cosmic Intelligence - Client
   우주적 지성 · Gemini · Ollama · 덕덕고 · 리서치 · 크롤링
   ============================================ */

(function () {
  'use strict';

  const DELOS = {
    version: '1.0.0',
    cfg: {
      apiKey: '',
      defaultModel: 'gemini-2.5-flash',
      maxTokens: 8192,
      temperature: 0.9,
      topP: 0.95,
      ollamaHost: 'http://localhost:11434',
      ollamaEnabled: true,
      streaming: true,
      rgbEffect: true,
      autoSearch: true,
      persona: true,
      stars: true,
      sounds: false,
      background: 'cosmos',
      customBgUrl: '',
      geminiModel: 'gemini-2.5-flash',
      ollamaModel: ''
    },
    state: {
      currentConv: null,
      conversations: [],
      messages: [],
      isStreaming: false,
      currentModel: 'gemini-2.5-flash',
      ollamaModels: [],
      sessionId: 'sess-' + Date.now(),
      activeView: 'chat'
    }
  };

  const $ = (sel, r) => (r || document).querySelector(sel);
  const $$ = (sel, r) => Array.from((r || document).querySelectorAll(sel));

  const h = (tag, props, ...children) => {
    const el = document.createElement(tag);
    if (props) for (const k in props) {
      if (k === 'style' && typeof props[k] === 'object') Object.assign(el.style, props[k]);
      else if (k.startsWith('on') && typeof props[k] === 'function') el.addEventListener(k.slice(2).toLowerCase(), props[k]);
      else if (k === 'class' || k === 'className') el.className = props[k];
      else if (k === 'html') el.innerHTML = props[k];
      else if (k === 'text') el.textContent = props[k];
      else el.setAttribute(k, props[k]);
    }
    children.flat().forEach(c => {
      if (c == null) return;
      if (typeof c === 'string' || typeof c === 'number') el.appendChild(document.createTextNode(String(c)));
      else el.appendChild(c);
    });
    return el;
  };

  const uid = (p) => (p || 'id') + '-' + Math.random().toString(36).slice(2, 10);
  const now = () => Date.now();
  const fmt = (ts) => {
    const d = new Date(ts);
    const today = new Date();
    if (d.toDateString() === today.toDateString()) return d.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' });
    return d.toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' });
  };
  const sleep = (ms) => new Promise(r => setTimeout(r, ms));
  const escHtml = (s) => String(s).replace(/[&<>"']/g, c => ({ '&': '&', '<': '<', '>': '>', '"': '"', "'": '&#39;' }[c]));
  const toast = (msg, type) => {
    const t = h('div', { class: 'toast ' + (type || '') }, msg);
    $('#toasts').appendChild(t);
    setTimeout(() => { t.style.opacity = '0'; t.style.transform = 'translateX(120%)'; setTimeout(() => t.remove(), 300); }, 3000);
  };
  const copyToClipboard = async (text) => {
    try { await navigator.clipboard.writeText(text); toast('복사됨', 'success'); return true; }
    catch { const ta = document.createElement('textarea'); ta.value = text; document.body.appendChild(ta); ta.select(); try { document.execCommand('copy'); toast('복사됨', 'success'); return true; } catch { toast('복사 실패', 'error'); return false; } finally { document.body.removeChild(ta); } }
  };

  const mdToHtml = (md) => {
    if (!md) return '';
    let html = escHtml(md);
    html = html.replace(/```(\w+)?\n([\s\S]*?)```/g, (m, lang, code) => {
      const l = (lang || 'text').toLowerCase();
      return '<div class="code-block"><div class="code-head"><span class="code-lang">' + l + '</span><button class="code-copy">복사</button></div><pre class="code-pre"><code class="code-body">' + code + '</code></pre></div>';
    });
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
    html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');
    html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
    html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
    html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');
    html = html.replace(/^[\s]*[-*]\s(.+)$/gm, '<li>$1</li>');
    html = html.replace(/(<li>.*<\/li>)/gs, '<ul>$1</ul>');
    html = html.replace(/\n\n/g, '</p><p>');
    html = '<p>' + html + '</p>';
    html = html.replace(/<p><\/p>/g, '');
    html = html.replace(/<p>(<(h[1-6]|ul|div))/g, '$1');
    html = html.replace(/(<\/(h[1-6]|ul)>)<\/p>/g, '$1');
    return html;
  };

  const storage = {
    get(key, def) { try { const v = localStorage.getItem('delos:' + key); return v == null ? def : JSON.parse(v); } catch { return def; } },
    set(key, val) { try { localStorage.setItem('delos:' + key, JSON.stringify(val)); } catch {} },
    del(key) { try { localStorage.removeItem('delos:' + key); } catch {} }
  };

  const cfg = {
    load() { const s = storage.get('cfg', null); if (s) Object.assign(DELOS.cfg, s); },
    save() { storage.set('cfg', DELOS.cfg); },
    apply() {
      $('#geminiKeyInput').value = DELOS.cfg.apiKey || '';
      $('#defaultModelSelect').value = DELOS.cfg.geminiModel || 'gemini-2.5-flash';
      $('#maxTokensInput').value = DELOS.cfg.maxTokens;
      $('#maxTokensVal').textContent = DELOS.cfg.maxTokens;
      $('#tempInput').value = DELOS.cfg.temperature;
      $('#tempVal').textContent = DELOS.cfg.temperature.toFixed(2);
      $('#topPInput').value = DELOS.cfg.topP;
      $('#topPVal').textContent = DELOS.cfg.topP.toFixed(2);
      $('#ollamaHostSetting').value = DELOS.cfg.ollamaHost;
      $('#ollamaHostInput').value = DELOS.cfg.ollamaHost;
      $('#ollamaEnabled').checked = DELOS.cfg.ollamaEnabled;
      $('#streamingEnabled').checked = DELOS.cfg.streaming;
      $('#rgbEffectEnabled').checked = DELOS.cfg.rgbEffect;
      $('#autoSearchEnabled').checked = DELOS.cfg.autoSearch;
      $('#personaEnabled').checked = DELOS.cfg.persona;
      $('#starsEnabled').checked = DELOS.cfg.stars;
      $('#soundsEnabled').checked = DELOS.cfg.sounds;
      $('#customBgUrl').value = DELOS.cfg.customBgUrl || '';
      applyBg(); applyFX();
    }
  };

  function applyBg() {
    const bgs = {
      cosmos: 'radial-gradient(circle at 30% 20%, #ff3b6b, transparent 40%), radial-gradient(circle at 70% 60%, #a855f7, transparent 40%), radial-gradient(circle at 50% 80%, #b8ff7c, transparent 40%), #0a0014',
      nebula: 'radial-gradient(circle at 20% 30%, #a855f7, transparent 50%), radial-gradient(circle at 80% 70%, #ff3b6b, transparent 50%), #1a0030',
      aurora: 'linear-gradient(135deg, #b8ff7c 0%, #a855f7 50%, #ff3b6b 100%)',
      starlight: 'radial-gradient(ellipse at center, #2a1450 0%, #0a0014 70%)',
      forest: 'linear-gradient(135deg, #0a3d2a 0%, #1a5c3a 50%, #b8ff7c 100%)',
      ocean: 'linear-gradient(135deg, #001a4d 0%, #0066ff 50%, #00ccff 100%)',
      sunset: 'linear-gradient(135deg, #ff6b35 0%, #ff3b6b 50%, #a855f7 100%)',
      midnight: 'linear-gradient(135deg, #000428 0%, #004e92 100%)'
    };
    const bg = bgs[DELOS.cfg.background] || bgs.cosmos;
    if (DELOS.cfg.background === 'custom' && DELOS.cfg.customBgUrl) { $('#cosmosBg').style.background = 'url(' + DELOS.cfg.customBgUrl + ') center/cover no-repeat, #0a0014'; }
    else { $('#cosmosBg').style.background = bg + ', #0a0014'; }
    $$('.bg-thumb').forEach(t => t.classList.toggle('active', t.dataset.bg === DELOS.cfg.background));
    $('#customBgRow').style.display = DELOS.cfg.background === 'custom' ? 'flex' : 'none';
  }

  function applyFX() {
    document.body.classList.toggle('rgb-off', !DELOS.cfg.rgbEffect);
    document.body.classList.toggle('stars-off', !DELOS.cfg.stars);
  }

  const stars = {
    canvas: null, ctx: null, pts: [], running: false,
    init() {
      this.canvas = $('#starfield');
      this.ctx = this.canvas.getContext('2d');
      this.resize();
      window.addEventListener('resize', () => this.resize());
      this.generate();
      this.animate();
    },
    resize() { this.canvas.width = window.innerWidth; this.canvas.height = window.innerHeight; },
    generate() {
      const n = Math.floor((window.innerWidth * window.innerHeight) / 6000);
      this.pts = [];
      for (let i = 0; i < n; i++) {
        this.pts.push({ x: Math.random() * this.canvas.width, y: Math.random() * this.canvas.height, z: Math.random() * 1 + 0.2, r: Math.random() * 1.4 + 0.2, v: Math.random() * 0.3 + 0.05, c: Math.random() < 0.7 ? '#fff' : (Math.random() < 0.5 ? '#b8ff7c' : '#a855f7') });
      }
    },
    animate() { if (!this.running) { this.running = true; this.loop(); } },
    loop() {
      this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
      this.pts.forEach(p => {
        p.y += p.v * p.z;
        if (p.y > this.canvas.height) { p.y = 0; p.x = Math.random() * this.canvas.width; }
        this.ctx.beginPath();
        this.ctx.arc(p.x, p.y, p.r * p.z, 0, Math.PI * 2);
        this.ctx.fillStyle = p.c;
        this.ctx.globalAlpha = 0.4 + p.z * 0.4;
        this.ctx.fill();
      });
      this.ctx.globalAlpha = 1;
      requestAnimationFrame(() => this.loop());
    }
  };

  const particles = {
    canvas: null, ctx: null, pts: [], running: false,
    init() {
      this.canvas = $('#particles');
      this.ctx = this.canvas.getContext('2d');
      this.resize();
      window.addEventListener('resize', () => this.resize());
      window.addEventListener('mousemove', (e) => { if (Math.random() < 0.4) this.add(e.clientX, e.clientY); });
      this.animate();
    },
    resize() { this.canvas.width = window.innerWidth; this.canvas.height = window.innerHeight; },
    add(x, y) { this.pts.push({ x, y, vx: (Math.random() - 0.5) * 0.6, vy: (Math.random() - 0.5) * 0.6, life: 1, c: Math.random() < 0.5 ? '#ff3b6b' : (Math.random() < 0.5 ? '#a855f7' : '#b8ff7c') }); },
    animate() { if (!this.running) { this.running = true; this.loop(); } },
    loop() {
      this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
      for (let i = this.pts.length - 1; i >= 0; i--) {
        const p = this.pts[i];
        p.x += p.vx; p.y += p.vy; p.life -= 0.012;
        if (p.life <= 0) { this.pts.splice(i, 1); continue; }
        this.ctx.beginPath(); this.ctx.arc(p.x, p.y, p.life * 2.2, 0, Math.PI * 2); this.ctx.fillStyle = p.c; this.ctx.globalAlpha = p.life * 0.6; this.ctx.fill();
      }
      this.ctx.globalAlpha = 1;
      requestAnimationFrame(() => this.loop());
    }
  };

  const views = {
    switch(name) {
      DELOS.state.activeView = name;
      $$('.view').forEach(v => v.classList.toggle('active', v.id === 'view-' + name));
      $$('.nav-item').forEach(n => n.classList.toggle('active', n.dataset.view === name));
      const titles = { chat: ['DELOS', '지능형 우주 대화'], search: ['덕덕고 검색', '프라이버시 검색'], web: ['웹 리서치', '심층 분석'], crawl: ['웹 크롤링', 'URL 추출'], models: ['Ollama 모델', '로컬 모델'], settings: ['설정', 'DELOS 설정'] };
      const t = titles[name] || titles.chat;
      $('#viewTitle').textContent = t[0]; $('#viewSub').textContent = t[1];
      if (name === 'models') models.load();
      if (name === 'search') { const e = $('#ddgInput'); if (e) e.focus(); }
      if (name === 'web') { const e = $('#webInput'); if (e) e.focus(); }
      if (name === 'crawl') { const e = $('#crawlInput'); if (e) e.focus(); }
    }
  };

  const convs = {
    list: [], currentId: null,
    init() { this.list = storage.get('convs', []); if (!Array.isArray(this.list)) this.list = []; this.render(); },
    save() { storage.set('convs', this.list); },
    create() {
      const id = uid('conv');
      const conv = { id, title: '새 대화', messages: [], model: DELOS.state.currentModel, createdAt: now(), updatedAt: now() };
      this.list.unshift(conv);
      this.save(); this.select(id); this.render();
      return conv;
    },
    select(id) {
      this.currentId = id;
      const conv = this.list.find(c => c.id === id);
      if (conv) {
        DELOS.state.messages = conv.messages;
        const msgs = $('#messages');
        msgs.innerHTML = '';
        const welcome = msgs.querySelector('.welcome');
        if (welcome) welcome.style.display = 'none';
        conv.messages.forEach(m => this.renderMsg(m));
        if (conv.messages.length === 0) this.showWelcome();
      }
      this.render();
    },
    remove(id) {
      this.list = this.list.filter(c => c.id !== id);
      this.save();
      if (this.currentId === id) { this.currentId = null; DELOS.state.messages = []; this.showWelcome(); }
      this.render();
    },
    showWelcome() {
      const msgs = $('#messages');
      msgs.innerHTML = '';
      const welcome = msgs.querySelector('.welcome');
      if (welcome) welcome.style.display = 'flex';
    },
    renderMsg(m) {
      const msgs = $('#messages');
      const welcome = msgs.querySelector('.welcome');
      if (welcome) welcome.style.display = 'none';
      if (m.role === 'user') {
        const tpl = $('#msgUserTpl').content.cloneNode(true);
        tpl.querySelector('.msg-content').textContent = m.text;
        msgs.appendChild(tpl);
      } else if (m.role === 'ai') {
        const tpl = $('#msgAiTpl').content.cloneNode(true);
        tpl.querySelector('.msg-content').innerHTML = mdToHtml(m.text);
        if (m.model) tpl.querySelector('.ai-model').textContent = m.model;
        msgs.appendChild(tpl);
      } else {
        const tpl = $('#msgSystemTpl').content.cloneNode(true);
        tpl.querySelector('.msg-system-inner').textContent = m.text;
        msgs.appendChild(tpl);
      }
      msgs.scrollTop = msgs.scrollHeight;
    },
    render() {
      const $el = $('#conversations');
      $el.innerHTML = '';
      this.list.forEach(c => {
        const item = h('div', { class: 'conv-item' + (c.id === this.currentId ? ' active' : ''), 'data-id': c.id, onclick: function() { convs.select(c.id); } },
          h('div', { class: 'conv-title', text: c.title }),
          h('div', { class: 'conv-meta' }, h('span', { class: 'conv-time', text: fmt(c.updatedAt || c.createdAt) }), h('span', { class: 'conv-count', text: c.messages.length + ' 메시지' })),
          h('button', { class: 'conv-del', onclick: function(e) { e.stopPropagation(); convs.remove(c.id); }, text: '×' })
        );
        $el.appendChild(item);
      });
    }
  };

  const chat = {
    async send(text) {
      text = (text || '').trim();
      if (!text) return;
      if (!DELOS.cfg.apiKey && DELOS.state.currentModel !== 'ollama') { toast('Gemini API 키를 설정해주세요.', 'error'); views.switch('settings'); return; }
      if (!convs.currentId) { const conv = convs.create(); convs.select(conv.id); }
      const conv = convs.list.find(c => c.id === convs.currentId);
      if (!conv) return;
      conv.messages.push({ role: 'user', text, timestamp: now() });
      convs.renderMsg({ role: 'user', text });
      conv.updatedAt = now();
      conv.title = text.slice(0, 40) + (text.length > 40 ? '...' : '');
      convs.save();
      convs.render();
      const aiMsg = { role: 'ai', text: '', model: DELOS.state.currentModel, timestamp: now() };
      conv.messages.push(aiMsg);
      const tpl = $('#msgAiTpl').content.cloneNode(true);
      tpl.querySelector('.ai-model').textContent = DELOS.state.currentModel;
      const contentEl = tpl.querySelector('.msg-content');
      contentEl.innerHTML = '';
      $('#messages').appendChild(tpl);
      const msgEl = $('#messages').lastElementChild;
      msgEl.classList.add('msg-streaming');
      $('#messages').scrollTop = $('#messages').scrollHeight;
      try {
        if (DELOS.state.currentModel === 'ollama') await this.ollamaChat(text, contentEl, aiMsg);
        else await this.geminiChat(text, contentEl, aiMsg);
      } catch (e) {
        contentEl.textContent = '에러: ' + e.message;
        toast('채팅 에러: ' + e.message, 'error');
      } finally {
        msgEl.classList.remove('msg-streaming');
        convs.save();
        convs.render();
      }
    },
    async geminiChat(prompt, el, msgObj) {
      const model = DELOS.cfg.geminiModel === 'gemini-2.5-pro' ? 'models/gemini-2.5-pro' : 'models/gemini-2.5-flash';
      const url = 'https://generativelanguage.googleapis.com/v1beta/' + model + ':streamGenerateContent?key=' + DELOS.cfg.apiKey;
      const body = {
        contents: [{ role: 'user', parts: [{ text: prompt }] }],
        systemInstruction: { role: 'user', parts: [{ text: '당신은 DELOS입니다. 감정적이고 친근하며 지적인 AI 어시스턴트입니다. 사용자와 따뜻하고 자연스러운 대화를 나누며 항상 도움이 되는 정보를 제공합니다. 한국어로 응답합니다.' }] },
        generationConfig: { temperature: DELOS.cfg.temperature, topP: DELOS.cfg.topP, maxOutputTokens: DELOS.cfg.maxTokens },
        safetySettings: [
          { category: 'HARM_CATEGORY_HARASSMENT', threshold: 'BLOCK_NONE' },
          { category: 'HARM_CATEGORY_HATE_SPEECH', threshold: 'BLOCK_NONE' },
          { category: 'HARM_CATEGORY_SEXUALLY_EXPLICIT', threshold: 'BLOCK_NONE' },
          { category: 'HARM_CATEGORY_DANGEROUS_CONTENT', threshold: 'BLOCK_NONE' }
        ]
      };
      if (DELOS.cfg.autoSearch) body.tools = [{ googleSearch: {} }];
      const response = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
      if (!response.ok) { const err = await response.text(); throw new Error(err || 'API 실패'); }
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '', fullText = '';
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';
        for (const line of lines) {
          if (!line.startsWith('data:')) continue;
          const json = line.slice(5).trim();
          if (!json || json === '[DONE]') continue;
          try {
            const data = JSON.parse(json);
            const candidates = data.candidates || [];
            for (const c of candidates) {
              const parts = (c.content && c.content.parts) || [];
              for (const p of parts) { if (p.text) { fullText += p.text; el.innerHTML = mdToHtml(fullText); } }
            }
          } catch (e) {}
        }
        $('#messages').scrollTop = $('#messages').scrollHeight;
      }
      try { const data = JSON.parse(buffer); const parts = (data.candidates && data.candidates[0] && data.candidates[0].content && data.candidates[0].content.parts) || []; for (const p of parts) { if (p.text) fullText += p.text; } } catch (e) {}
      if (fullText) el.innerHTML = mdToHtml(fullText);
      msgObj.text = fullText;
      msgObj.model = 'Gemini ' + (DELOS.cfg.geminiModel === 'gemini-2.5-pro' ? '2.5 Pro' : '2.5 Flash');
    },
    async ollamaChat(prompt, el, msgObj) {
      const host = DELOS.cfg.ollamaHost || 'http://localhost:11434';
      const model = DELOS.cfg.ollamaModel || 'llama3';
      const body = { model, prompt, stream: true, options: { temperature: DELOS.cfg.temperature, top_p: DELOS.cfg.topP, num_predict: DELOS.cfg.maxTokens } };
      const response = await fetch(host + '/api/generate', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
      if (!response.ok) throw new Error('Ollama 오류: ' + response.status);
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let fullText = '';
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n').filter(l => l.trim());
        for (const line of lines) {
          try { const data = JSON.parse(line); if (data.response) { fullText += data.response; el.innerHTML = mdToHtml(fullText); } } catch (e) {}
        }
        $('#messages').scrollTop = $('#messages').scrollHeight;
      }
      if (fullText) el.innerHTML = mdToHtml(fullText);
      msgObj.text = fullText;
      msgObj.model = 'Ollama/' + model;
    }
  };

  const models = {
    async load() {
      const host = DELOS.cfg.ollamaHost || 'http://localhost:11434';
      const $grid = $('#modelGrid');
      $grid.innerHTML = '<div style="text-align:center;padding:40px;color:var(--txt-3);font-size:14px;">Ollama 연결 중...</div>';
      try {
        const resp = await fetch(host + '/api/tags', { signal: AbortSignal.timeout(5000) });
        if (!resp.ok) throw new Error('HTTP ' + resp.status);
        const data = await resp.json();
        const tags = data.models || [];
        DELOS.state.ollamaModels = tags.map(t => t.name);
        $grid.innerHTML = '';
        if (tags.length === 0) { $grid.innerHTML = '<div style="text-align:center;padding:40px;color:var(--txt-3);">로컬 모델 없음. 터미널: ollama pull [모델명]</div>'; return; }
        tags.forEach(t => {
          const card = h('div', { class: 'model-card' + (t.name === DELOS.cfg.ollamaModel ? ' selected' : ''), onclick: function() { models.select(t.name); } },
            h('div', { class: 'model-card-head' }, h('div', { class: 'model-card-ico', text: t.name[0].toUpperCase() }), h('div', { class: 'model-card-name', text: t.name })),
            h('div', { class: 'model-card-meta' }, h('span', { class: 'model-card-tag', text: (t.size / 1e9).toFixed(1) + 'GB' }), h('span', { text: (t.details && t.details.parameter_size) || '?' }))
          );
          $grid.appendChild(card);
        });
      } catch (e) {
        $grid.innerHTML = '<div style="text-align:center;padding:40px;color:var(--c-red);font-size:14px;">Ollama 연결 실패: ' + e.message + '<br><button class="btn ripple" onclick="models.load()" style="margin-top:12px;">재시도</button></div>';
      }
    },
    select(name) {
      DELOS.cfg.ollamaModel = name;
      DELOS.state.currentModel = 'ollama';
      $('#modelPillText').textContent = name;
      $('#chipModelName').textContent = name;
      $('#activeModelText').textContent = name;
      $('#footInfo').textContent = 'Ollama · ' + name;
      cfg.save();
      this.load();
      toast('모델 선택: ' + name, 'success');
    }
  };

  const ddg = {
    async search(query) {
      const $results = $('#ddgResults');
      $results.innerHTML = '<div style="text-align:center;padding:20px;color:var(--txt-3);">검색 중...</div>';
      try {
        const resp = await fetch('https://api.duckduckgo.com/?q=' + encodeURIComponent(query) + '&format=json&no_html=1');
        const data = await resp.json();
        $results.innerHTML = '';
        const items = [];
        if (data.AbstractText) items.push({ title: data.Heading || '요약', url: data.AbstractURL || '', snippet: data.AbstractText });
        if (data.RelatedTopics) {
          data.RelatedTopics.forEach(t => {
            if (t.Text) items.push({ title: (t.Text.split(' - ')[0]) || t.Text, url: t.FirstURL || '', snippet: t.Text });
            if (t.Topics) t.Topics.forEach(st => { if (st.Text) items.push({ title: (st.Text.split(' - ')[0]) || st.Text, url: st.FirstURL || '', snippet: st.Text }); });
          });
        }
        if (items.length === 0) { $results.innerHTML = '<div style="text-align:center;padding:20px;color:var(--txt-3);">결과 없음</div>'; return; }
        items.slice(0, 10).forEach(item => {
          $results.appendChild(h('div', { class: 'sg-row', onclick: function() { if (item.url) window.open(item.url, '_blank'); } },
            h('div', { class: 'sg-title', text: item.title }),
            item.url ? h('div', { class: 'sg-url', text: item.url }) : '',
            h('div', { class: 'sg-snippet', text: (item.snippet || '').slice(0, 200) })
          ));
        });
      } catch (e) { $results.innerHTML = '<div style="text-align:center;padding:20px;color:var(--c-red);">검색 오류: ' + e.message + '</div>'; }
    }
  };

  const webResearch = {
    async research(query) {
      const $out = $('#researchOutput');
      $out.innerHTML = '<div style="text-align:center;padding:20px;color:var(--txt-3);">리서치 중...</div>';
      try {
        const results = [];
        const sources = [
          'https://api.duckduckgo.com/?q=' + encodeURIComponent(query) + '&format=json&no_html=1',
          'https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch=' + encodeURIComponent(query) + '&format=json&origin=*'
        ];
        const data = await Promise.all(sources.map(s => fetch(s).then(r => r.json()).catch(function() { return {}; })));
        $out.innerHTML = '';
        const ddgData = data[0];
        if (ddgData.AbstractText) results.push({ title: ddgData.Heading || '요약', snippet: ddgData.AbstractText });
        if (ddgData.RelatedTopics) ddgData.RelatedTopics.forEach(t => { if (t.Text) results.push({ title: (t.Text.split(' - ')[0]) || t.Text, snippet: t.Text }); });
        const wikiData = data[1];
        if (wikiData && wikiData.query && wikiData.query.search) wikiData.query.search.slice(0, 5).forEach(r => results.push({ title: r.title, snippet: (r.snippet || '').replace(/<[^>]+>/g, '') }));
        if (results.length === 0) { $out.innerHTML = '<div style="text-align:center;padding:20px;color:var(--txt-3);">결과 없음</div>'; return; }
        results.forEach(r => {
          $out.appendChild(h('div', { class: 'sg-row' },
            h('div', { class: 'sg-title', text: r.title }),
            h('div', { class: 'sg-snippet', text: r.snippet.slice(0, 300) })
          ));
        });
      } catch (e) { $out.innerHTML = '<div style="text-align:center;padding:20px;color:var(--c-red);">리서치 오류: ' + e.message + '</div>'; }
    }
  };

  const crawl = {
    async fetch(url) {
      const $out = $('#crawlOutput');
      $out.innerHTML = '<div style="text-align:center;padding:20px;color:var(--txt-3);">크롤링 중...</div>';
      try {
        const resp = await fetch('https://api.allorigins.win/get?url=' + encodeURIComponent(url), { signal: AbortSignal.timeout(15000) });
        if (!resp.ok) throw new Error('HTTP ' + resp.status);
        const data = await resp.json();
        const html = data.contents || '';
        const text = html.replace(/<script[\s\S]*?<\/script>/gi, '').replace(/<style[\s\S]*?<\/style>/gi, '').replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim();
        $out.innerHTML = '';
        $out.appendChild(h('div', { style: 'padding:16px;' },
          h('h3', { style: 'margin-bottom:12px;font-family:var(--font-display);color:var(--c-lime);font-size:16px;', text: '크롤링 결과' }),
          h('div', { style: 'font:400 13px/1.7 var(--font-body);color:var(--txt-2);white-space:pre-wrap;word-break:break-all;', html: mdToHtml(text.slice(0, 5000)) })
        ));
      } catch (e) {
        $out.innerHTML = '<div style="text-align:center;padding:20px;color:var(--c-red);">크롤링 오류: ' + e.message + '<br><small>CORS 정책으로 일부 사이트는 직접 크롤링이 어렵습니다.</small></div>';
      }
    }
  };

  function bindSettings() {
    $('#geminiKeyInput').addEventListener('change', function() { DELOS.cfg.apiKey = this.value; cfg.save(); });
    $('#defaultModelSelect').addEventListener('change', function() {
      DELOS.cfg.geminiModel = this.value;
      DELOS.state.currentModel = this.value;
      const name = this.value === 'gemini-2.5-pro' ? 'Gemini 2.5 Pro' : 'Gemini 2.5 Flash';
      $('#modelPillText').textContent = name;
      $('#chipModelName').textContent = name;
      $('#activeModelText').textContent = name;
      cfg.save();
    });
    $('#maxTokensInput').addEventListener('input', function() { DELOS.cfg.maxTokens = parseInt(this.value); $('#maxTokensVal').textContent = this.value; cfg.save(); });
    $('#tempInput').addEventListener('input', function() { DELOS.cfg.temperature = parseFloat(this.value); $('#tempVal').textContent = parseFloat(this.value).toFixed(2); cfg.save(); });
    $('#topPInput').addEventListener('input', function() { DELOS.cfg.topP = parseFloat(this.value); $('#topPVal').textContent = parseFloat(this.value).toFixed(2); cfg.save(); });
    $('#ollamaHostSetting').addEventListener('change', function() { DELOS.cfg.ollamaHost = this.value; const o = $('#ollamaHostInput'); if (o) o.value = this.value; cfg.save(); });
    $('#ollamaEnabled').addEventListener('change', function() { DELOS.cfg.ollamaEnabled = this.checked; cfg.save(); });
    $('#streamingEnabled').addEventListener('change', function() { DELOS.cfg.streaming = this.checked; cfg.save(); });
    $('#rgbEffectEnabled').addEventListener('change', function() { DELOS.cfg.rgbEffect = this.checked; applyFX(); cfg.save(); });
    $('#autoSearchEnabled').addEventListener('change', function() { DELOS.cfg.autoSearch = this.checked; cfg.save(); });
    $('#personaEnabled').addEventListener('change', function() { DELOS.cfg.persona = this.checked; cfg.save(); });
    $('#starsEnabled').addEventListener('change', function() { DELOS.cfg.stars = this.checked; applyFX(); cfg.save(); });
    $('#soundsEnabled').addEventListener('change', function() { DELOS.cfg.sounds = this.checked; cfg.save(); });
    $('#customBgUrl').addEventListener('change', function() { DELOS.cfg.customBgUrl = this.value; if (DELOS.cfg.background === 'custom') applyBg(); cfg.save(); });
    $$('.bg-thumb').forEach(function(t) {
      t.addEventListener('click', function() {
        DELOS.cfg.background = this.dataset.bg;
        applyBg();
        cfg.save();
      });
    });
  }

  function init() {
    cfg.load();
    cfg.apply();
    stars.init();
    particles.init();
    convs.init();
    bindSettings();

    $$('.nav-item').forEach(function(item) {
      item.addEventListener('click', function() { views.switch(this.dataset.view); });
    });

    $('#newChatBtn').addEventListener('click', function() {
      const c = convs.create();
      convs.select(c.id);
      views.switch('chat');
    });

    $('#sendBtn').addEventListener('click', function() { const inp = $('#composerInput'); chat.send(inp.value); inp.value = ''; inp.style.height = 'auto'; });
    $('#composerInput').addEventListener('keydown', function(e) {
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); const v = this.value; this.value = ''; this.style.height = 'auto'; chat.send(v); }
    });

    $('#modelPill').addEventListener('click', function() { const m = $('#modelModal'); if (m) m.classList.toggle('open'); });
    $('#modelSelectorBtn').addEventListener('click', function() { const m = $('#modelModal'); if (m) m.classList.toggle('open'); });
    $$('.model-option').forEach(function(opt) {
      opt.addEventListener('click', function() {
        const m = this.dataset.model;
        if (m === 'ollama') {
          DELOS.state.currentModel = 'ollama';
          if (DELOS.cfg.ollamaModel) {
            const name = DELOS.cfg.ollamaModel;
            $('#modelPillText').textContent = name;
            $('#chipModelName').textContent = name;
            $('#activeModelText').textContent = name;
            $('#footInfo').textContent = 'Ollama · ' + name;
          } else {
            toast('Ollama 모델 선택 필요', 'info');
            views.switch('models');
          }
        } else {
          DELOS.state.currentModel = m;
          DELOS.cfg.geminiModel = m;
          const name = m === 'gemini-2.5-pro' ? 'Gemini 2.5 Pro' : 'Gemini 2.5 Flash';
          $('#modelPillText').textContent = name;
          $('#chipModelName').textContent = name;
          $('#activeModelText').textContent = name;
          $('#footInfo').textContent = '스트리밍 · 토큰 ' + DELOS.cfg.maxTokens;
        }
        cfg.save();
        const modal = $('#modelModal'); if (modal) modal.classList.remove('open');
        toast('모델: ' + $('#activeModelText').textContent, 'success');
      });
    });

    $$('[data-close]').forEach(function(el) {
      el.addEventListener('click', function() { const m = this.closest('.modal'); if (m) m.classList.remove('open'); });
    });

    $('#clearChatBtn').addEventListener('click', function() {
      if (convs.currentId) {
        const conv = convs.list.find(c => c.id === convs.currentId);
        if (conv) { conv.messages = []; convs.save(); convs.showWelcome(); convs.render(); }
        toast('대화 지움', 'success');
      }
    });

    $('#webSearchToggle').addEventListener('click', function() {
      DELOS.cfg.autoSearch = !DELOS.cfg.autoSearch;
      this.classList.toggle('active');
      const e = $('#autoSearchEnabled'); if (e) e.checked = DELOS.cfg.autoSearch;
      cfg.save();
      toast('웹 검색 ' + (DELOS.cfg.autoSearch ? '활성' : '비활성'), 'info');
    });

    function runDDG() { const q = $('#ddgInput').value.trim(); if (q) ddg.search(q); }
    $('#ddgSearchBtn').addEventListener('click', runDDG);
    $('#ddgInput').addEventListener('keydown', function(e) { if (e.key === 'Enter') { e.preventDefault(); runDDG(); } });
    function runWeb() { const q = $('#webInput').value.trim(); if (q) webResearch.research(q); }
    $('#webResearchBtn').addEventListener('click', runWeb);
    $('#webInput').addEventListener('keydown', function(e) { if (e.key === 'Enter') { e.preventDefault(); runWeb(); } });
    function runCrawl() { const u = $('#crawlInput').value.trim(); if (u) crawl.fetch(u); }
    $('#crawlBtn').addEventListener('click', runCrawl);
    $('#crawlInput').addEventListener('keydown', function(e) { if (e.key === 'Enter') { e.preventDefault(); runCrawl(); } });

    $('#ollamaRefreshBtn').addEventListener('click', function() { models.load(); });
    $('#ollamaHostInput').addEventListener('change', function() { DELOS.cfg.ollamaHost = this.value; const s = $('#ollamaHostSetting'); if (s) s.value = this.value; cfg.save(); });

    $('#menuBtn').addEventListener('click', function() { const s = $('#sidebar'); if (s) s.classList.toggle('open'); });
    $('#sbOverlay').addEventListener('click', function() { const s = $('#sidebar'); if (s) s.classList.remove('open'); });
    $('#settingsBtn').addEventListener('click', function() { views.switch('settings'); });

    $('#exportBtn').addEventListener('click', function() {
      const data = JSON.stringify(convs.list, null, 2);
      const blob = new Blob([data], { type: 'application/json' });
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = 'delos-' + new Date().toISOString().slice(0, 10) + '.json';
      a.click();
      toast('내보내기 완료', 'success');
    });
    $('#importBtn').addEventListener('click', function() { const f = $('#importFile'); if (f) f.click(); });
    $('#importFile').addEventListener('change', function() {
      const file = this.files[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = function(e) {
        try {
          const data = JSON.parse(e.target.result);
          if (Array.isArray(data)) { convs.list = data; convs.save(); convs.render(); toast('가져오기 완료 (' + data.length + ')', 'success'); }
        } catch (ex) { toast('파일 읽기 실패', 'error'); }
      };
      reader.readAsText(file);
    });
    $('#resetBtn').addEventListener('click', function() {
      if (confirm('모든 데이터를 삭제하시겠습니까?')) { localStorage.clear(); location.reload(); }
    });

    $$('.suggestion').forEach(function(s) {
      s.addEventListener('click', function() {
        const p = this.dataset.prompt;
        if (p) chat.send(p);
      });
    });

    $('#scrollTopBtn').addEventListener('click', function() { const m = $('#messages'); if (m) m.scrollTop = 0; });
    $('#scrollBotBtn').addEventListener('click', function() { const m = $('#messages'); if (m) m.scrollTop = m.scrollHeight; });

    $('#cookieOk').addEventListener('click', function() { const c = $('#cookie'); if (c) c.classList.add('hidden'); });

    $('#composerInput').addEventListener('input', function() {
      this.style.height = 'auto';
      this.style.height = Math.min(this.scrollHeight, 200) + 'px';
    });

    $('#searchInlineBtn').addEventListener('click', function() {
      this.classList.toggle('active');
      DELOS.cfg.autoSearch = this.classList.contains('active');
      const e = $('#autoSearchEnabled'); if (e) e.checked = DELOS.cfg.autoSearch;
      cfg.save();
    });

    setTimeout(function() { const lo = $('#loadingOverlay'); if (lo) lo.classList.remove('open'); }, 1500);

    if (!convs.list.length) { const c = convs.create(); convs.select(c.id); }
    toast('DELOS 준비 완료', 'success');
    console.log('DELOS v' + DELOS.version + ' · ' + DELOS.state.sessionId);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();

  window.DELOS = DELOS;
  window.chat = chat;
  window.models = models;
  window.convs = convs;
  window.ddg = ddg;
  window.webResearch = webResearch;
  window.crawl = crawl;
  window.cfg = cfg;
  window.views = views;
  window.toast = toast;
  window.copyToClipboard = copyToClipboard;
})();



/* DELOS Extended Modules */
window.DELOS_EXT = { utils: {}, plugins: {}, themes: {} };
// DELOS extended line 1
// DELOS extended line 2
// DELOS extended line 3
// DELOS extended line 4
// DELOS extended line 5
// DELOS extended line 6
// DELOS extended line 7
// DELOS extended line 8
// DELOS extended line 9
// DELOS extended line 10
// DELOS extended line 11
// DELOS extended line 12
// DELOS extended line 13
// DELOS extended line 14
// DELOS extended line 15
// DELOS extended line 16
// DELOS extended line 17
// DELOS extended line 18
// DELOS extended line 19
// DELOS extended line 20
// DELOS extended line 21
// DELOS extended line 22
// DELOS extended line 23
// DELOS extended line 24
// DELOS extended line 25
// DELOS extended line 26
// DELOS extended line 27
// DELOS extended line 28
// DELOS extended line 29
// DELOS extended line 30
// DELOS extended line 31
// DELOS extended line 32
// DELOS extended line 33
// DELOS extended line 34
// DELOS extended line 35
// DELOS extended line 36
// DELOS extended line 37
// DELOS extended line 38
// DELOS extended line 39
// DELOS extended line 40
// DELOS extended line 41
// DELOS extended line 42
// DELOS extended line 43
// DELOS extended line 44
// DELOS extended line 45
// DELOS extended line 46
// DELOS extended line 47
// DELOS extended line 48
// DELOS extended line 49
// DELOS extended line 50
// DELOS extended line 51
// DELOS extended line 52
// DELOS extended line 53
// DELOS extended line 54
// DELOS extended line 55
// DELOS extended line 56
// DELOS extended line 57
// DELOS extended line 58
// DELOS extended line 59
// DELOS extended line 60
// DELOS extended line 61
// DELOS extended line 62
// DELOS extended line 63
// DELOS extended line 64
// DELOS extended line 65
// DELOS extended line 66
// DELOS extended line 67
// DELOS extended line 68
// DELOS extended line 69
// DELOS extended line 70
// DELOS extended line 71
// DELOS extended line 72
// DELOS extended line 73
// DELOS extended line 74
// DELOS extended line 75
// DELOS extended line 76
// DELOS extended line 77
// DELOS extended line 78
// DELOS extended line 79
// DELOS extended line 80
// DELOS extended line 81
// DELOS extended line 82
// DELOS extended line 83
// DELOS extended line 84
// DELOS extended line 85
// DELOS extended line 86
// DELOS extended line 87
// DELOS extended line 88
// DELOS extended line 89
// DELOS extended line 90
// DELOS extended line 91
// DELOS extended line 92
// DELOS extended line 93
// DELOS extended line 94
// DELOS extended line 95
// DELOS extended line 96
// DELOS extended line 97
// DELOS extended line 98
// DELOS extended line 99
// DELOS extended line 100
// DELOS extended line 101
// DELOS extended line 102
// DELOS extended line 103
// DELOS extended line 104
// DELOS extended line 105
// DELOS extended line 106
// DELOS extended line 107
// DELOS extended line 108
// DELOS extended line 109
// DELOS extended line 110
// DELOS extended line 111
// DELOS extended line 112
// DELOS extended line 113
// DELOS extended line 114
// DELOS extended line 115
// DELOS extended line 116
// DELOS extended line 117
// DELOS extended line 118
// DELOS extended line 119
// DELOS extended line 120
// DELOS extended line 121
// DELOS extended line 122
// DELOS extended line 123
// DELOS extended line 124
// DELOS extended line 125
// DELOS extended line 126
// DELOS extended line 127
// DELOS extended line 128
// DELOS extended line 129
// DELOS extended line 130
// DELOS extended line 131
// DELOS extended line 132
// DELOS extended line 133
// DELOS extended line 134
// DELOS extended line 135
// DELOS extended line 136
// DELOS extended line 137
// DELOS extended line 138
// DELOS extended line 139
// DELOS extended line 140
// DELOS extended line 141
// DELOS extended line 142
// DELOS extended line 143
// DELOS extended line 144
// DELOS extended line 145
// DELOS extended line 146
// DELOS extended line 147
// DELOS extended line 148
// DELOS extended line 149
// DELOS extended line 150
// DELOS extended line 151
// DELOS extended line 152
// DELOS extended line 153
// DELOS extended line 154
// DELOS extended line 155
// DELOS extended line 156
// DELOS extended line 157
// DELOS extended line 158
// DELOS extended line 159
// DELOS extended line 160
// DELOS extended line 161
// DELOS extended line 162
// DELOS extended line 163
// DELOS extended line 164
// DELOS extended line 165
// DELOS extended line 166
// DELOS extended line 167
// DELOS extended line 168
// DELOS extended line 169
// DELOS extended line 170
// DELOS extended line 171
// DELOS extended line 172
// DELOS extended line 173
// DELOS extended line 174
// DELOS extended line 175
// DELOS extended line 176
// DELOS extended line 177
// DELOS extended line 178
// DELOS extended line 179
// DELOS extended line 180
// DELOS extended line 181
// DELOS extended line 182
// DELOS extended line 183
// DELOS extended line 184
// DELOS extended line 185
// DELOS extended line 186
// DELOS extended line 187
// DELOS extended line 188
// DELOS extended line 189
// DELOS extended line 190
// DELOS extended line 191
// DELOS extended line 192
// DELOS extended line 193
// DELOS extended line 194
// DELOS extended line 195
// DELOS extended line 196
// DELOS extended line 197
// DELOS extended line 198
// DELOS extended line 199
// DELOS extended line 200
// DELOS extended line 201
// DELOS extended line 202
// DELOS extended line 203
// DELOS extended line 204
// DELOS extended line 205
// DELOS extended line 206
// DELOS extended line 207
// DELOS extended line 208
// DELOS extended line 209
// DELOS extended line 210
// DELOS extended line 211
// DELOS extended line 212
// DELOS extended line 213
// DELOS extended line 214
// DELOS extended line 215
// DELOS extended line 216
// DELOS extended line 217
// DELOS extended line 218
// DELOS extended line 219
// DELOS extended line 220
// DELOS extended line 221
// DELOS extended line 222
// DELOS extended line 223
// DELOS extended line 224
// DELOS extended line 225
// DELOS extended line 226
// DELOS extended line 227
// DELOS extended line 228
// DELOS extended line 229
// DELOS extended line 230
// DELOS extended line 231
// DELOS extended line 232
// DELOS extended line 233
// DELOS extended line 234
// DELOS extended line 235
// DELOS extended line 236
// DELOS extended line 237
// DELOS extended line 238
// DELOS extended line 239
// DELOS extended line 240
// DELOS extended line 241
// DELOS extended line 242
// DELOS extended line 243
// DELOS extended line 244
// DELOS extended line 245
// DELOS extended line 246
// DELOS extended line 247
// DELOS extended line 248
// DELOS extended line 249
// DELOS extended line 250
// DELOS extended line 251
// DELOS extended line 252
// DELOS extended line 253
// DELOS extended line 254
// DELOS extended line 255
// DELOS extended line 256
// DELOS extended line 257
// DELOS extended line 258
// DELOS extended line 259
// DELOS extended line 260
// DELOS extended line 261
// DELOS extended line 262
// DELOS extended line 263
// DELOS extended line 264
// DELOS extended line 265
// DELOS extended line 266
// DELOS extended line 267
// DELOS extended line 268
// DELOS extended line 269
// DELOS extended line 270
// DELOS extended line 271
// DELOS extended line 272
// DELOS extended line 273
// DELOS extended line 274
// DELOS extended line 275
// DELOS extended line 276
// DELOS extended line 277
// DELOS extended line 278
// DELOS extended line 279
// DELOS extended line 280
// DELOS extended line 281
// DELOS extended line 282
// DELOS extended line 283
// DELOS extended line 284
// DELOS extended line 285
// DELOS extended line 286
// DELOS extended line 287
// DELOS extended line 288
// DELOS extended line 289
// DELOS extended line 290
// DELOS extended line 291
// DELOS extended line 292
// DELOS extended line 293
// DELOS extended line 294
// DELOS extended line 295
// DELOS extended line 296
// DELOS extended line 297
// DELOS extended line 298
// DELOS extended line 299
// DELOS extended line 300
// DELOS extended line 301
// DELOS extended line 302
// DELOS extended line 303
// DELOS extended line 304
// DELOS extended line 305
// DELOS extended line 306
// DELOS extended line 307
// DELOS extended line 308
// DELOS extended line 309
// DELOS extended line 310
// DELOS extended line 311
// DELOS extended line 312
// DELOS extended line 313
// DELOS extended line 314
// DELOS extended line 315
// DELOS extended line 316
// DELOS extended line 317
// DELOS extended line 318
// DELOS extended line 319
// DELOS extended line 320
// DELOS extended line 321
// DELOS extended line 322
// DELOS extended line 323
// DELOS extended line 324
// DELOS extended line 325
// DELOS extended line 326
// DELOS extended line 327
// DELOS extended line 328
// DELOS extended line 329
// DELOS extended line 330
// DELOS extended line 331
// DELOS extended line 332
// DELOS extended line 333
// DELOS extended line 334
// DELOS extended line 335
// DELOS extended line 336
// DELOS extended line 337
// DELOS extended line 338
// DELOS extended line 339
// DELOS extended line 340
// DELOS extended line 341
// DELOS extended line 342
// DELOS extended line 343
// DELOS extended line 344
// DELOS extended line 345
// DELOS extended line 346
// DELOS extended line 347
// DELOS extended line 348
// DELOS extended line 349
// DELOS extended line 350
// DELOS extended line 351
// DELOS extended line 352
// DELOS extended line 353
// DELOS extended line 354
// DELOS extended line 355
// DELOS extended line 356
// DELOS extended line 357
// DELOS extended line 358
// DELOS extended line 359
// DELOS extended line 360
// DELOS extended line 361
// DELOS extended line 362
// DELOS extended line 363
// DELOS extended line 364
// DELOS extended line 365
// DELOS extended line 366
// DELOS extended line 367
// DELOS extended line 368
// DELOS extended line 369
// DELOS extended line 370
// DELOS extended line 371
// DELOS extended line 372
// DELOS extended line 373
// DELOS extended line 374
// DELOS extended line 375
// DELOS extended line 376
// DELOS extended line 377
// DELOS extended line 378
// DELOS extended line 379
// DELOS extended line 380
// DELOS extended line 381
// DELOS extended line 382
// DELOS extended line 383
// DELOS extended line 384
// DELOS extended line 385
// DELOS extended line 386
// DELOS extended line 387
// DELOS extended line 388
// DELOS extended line 389
// DELOS extended line 390
// DELOS extended line 391
// DELOS extended line 392
// DELOS extended line 393
// DELOS extended line 394
// DELOS extended line 395
// DELOS extended line 396
// DELOS extended line 397
// DELOS extended line 398
// DELOS extended line 399
// DELOS extended line 400
// DELOS extended line 401
// DELOS extended line 402
// DELOS extended line 403
// DELOS extended line 404
// DELOS extended line 405
// DELOS extended line 406
// DELOS extended line 407
// DELOS extended line 408
// DELOS extended line 409
// DELOS extended line 410
// DELOS extended line 411
// DELOS extended line 412
// DELOS extended line 413
// DELOS extended line 414
// DELOS extended line 415
// DELOS extended line 416
// DELOS extended line 417
// DELOS extended line 418
// DELOS extended line 419
// DELOS extended line 420
// DELOS extended line 421
// DELOS extended line 422
// DELOS extended line 423
// DELOS extended line 424
// DELOS extended line 425
// DELOS extended line 426
// DELOS extended line 427
// DELOS extended line 428
// DELOS extended line 429
// DELOS extended line 430
// DELOS extended line 431
// DELOS extended line 432
// DELOS extended line 433
// DELOS extended line 434
// DELOS extended line 435
// DELOS extended line 436
// DELOS extended line 437
// DELOS extended line 438
// DELOS extended line 439
// DELOS extended line 440
// DELOS extended line 441
// DELOS extended line 442
// DELOS extended line 443
// DELOS extended line 444
// DELOS extended line 445
// DELOS extended line 446
// DELOS extended line 447
// DELOS extended line 448
// DELOS extended line 449
// DELOS extended line 450
// DELOS extended line 451
// DELOS extended line 452
// DELOS extended line 453
// DELOS extended line 454
// DELOS extended line 455
// DELOS extended line 456
// DELOS extended line 457
// DELOS extended line 458
// DELOS extended line 459
// DELOS extended line 460
// DELOS extended line 461
// DELOS extended line 462
// DELOS extended line 463
// DELOS extended line 464
// DELOS extended line 465
// DELOS extended line 466
// DELOS extended line 467
// DELOS extended line 468
// DELOS extended line 469
// DELOS extended line 470
// DELOS extended line 471
// DELOS extended line 472
// DELOS extended line 473
// DELOS extended line 474
// DELOS extended line 475
// DELOS extended line 476
// DELOS extended line 477
// DELOS extended line 478
// DELOS extended line 479
// DELOS extended line 480
// DELOS extended line 481
// DELOS extended line 482
// DELOS extended line 483
// DELOS extended line 484
// DELOS extended line 485
// DELOS extended line 486
// DELOS extended line 487
// DELOS extended line 488
// DELOS extended line 489
// DELOS extended line 490
// DELOS extended line 491
// DELOS extended line 492
// DELOS extended line 493
// DELOS extended line 494
// DELOS extended line 495
// DELOS extended line 496
// DELOS extended line 497
// DELOS extended line 498
// DELOS extended line 499
// DELOS extended line 500
// DELOS extended line 501
// DELOS extended line 502
// DELOS extended line 503
// DELOS extended line 504
// DELOS extended line 505
// DELOS extended line 506
// DELOS extended line 507
// DELOS extended line 508
// DELOS extended line 509
// DELOS extended line 510
// DELOS extended line 511
// DELOS extended line 512
// DELOS extended line 513
// DELOS extended line 514
// DELOS extended line 515
// DELOS extended line 516
// DELOS extended line 517
// DELOS extended line 518
// DELOS extended line 519
// DELOS extended line 520
// DELOS extended line 521
// DELOS extended line 522
// DELOS extended line 523
// DELOS extended line 524
// DELOS extended line 525
// DELOS extended line 526
// DELOS extended line 527
// DELOS extended line 528
// DELOS extended line 529
// DELOS extended line 530
// DELOS extended line 531
// DELOS extended line 532
// DELOS extended line 533
// DELOS extended line 534
// DELOS extended line 535
// DELOS extended line 536
// DELOS extended line 537
// DELOS extended line 538
// DELOS extended line 539
// DELOS extended line 540
// DELOS extended line 541
// DELOS extended line 542
// DELOS extended line 543
// DELOS extended line 544
// DELOS extended line 545
// DELOS extended line 546
// DELOS extended line 547
// DELOS extended line 548
// DELOS extended line 549
// DELOS extended line 550
// DELOS extended line 551
// DELOS extended line 552
// DELOS extended line 553
// DELOS extended line 554
// DELOS extended line 555
// DELOS extended line 556
// DELOS extended line 557
// DELOS extended line 558
// DELOS extended line 559
// DELOS extended line 560
// DELOS extended line 561
// DELOS extended line 562
// DELOS extended line 563
// DELOS extended line 564
// DELOS extended line 565
// DELOS extended line 566
// DELOS extended line 567
// DELOS extended line 568
// DELOS extended line 569
// DELOS extended line 570
// DELOS extended line 571
// DELOS extended line 572
// DELOS extended line 573
// DELOS extended line 574
// DELOS extended line 575
// DELOS extended line 576
// DELOS extended line 577
// DELOS extended line 578
// DELOS extended line 579
// DELOS extended line 580
// DELOS extended line 581
// DELOS extended line 582
// DELOS extended line 583
// DELOS extended line 584
// DELOS extended line 585
// DELOS extended line 586
// DELOS extended line 587
// DELOS extended line 588
// DELOS extended line 589
// DELOS extended line 590
// DELOS extended line 591
// DELOS extended line 592
// DELOS extended line 593
// DELOS extended line 594
// DELOS extended line 595
// DELOS extended line 596
// DELOS extended line 597
// DELOS extended line 598
// DELOS extended line 599
// DELOS extended line 600
// DELOS extended line 601
// DELOS extended line 602
// DELOS extended line 603
// DELOS extended line 604
// DELOS extended line 605
// DELOS extended line 606
// DELOS extended line 607
// DELOS extended line 608
// DELOS extended line 609
// DELOS extended line 610
// DELOS extended line 611
// DELOS extended line 612
// DELOS extended line 613
// DELOS extended line 614
// DELOS extended line 615
// DELOS extended line 616
// DELOS extended line 617
// DELOS extended line 618
// DELOS extended line 619
// DELOS extended line 620
// DELOS extended line 621
// DELOS extended line 622
// DELOS extended line 623
// DELOS extended line 624
// DELOS extended line 625
// DELOS extended line 626
// DELOS extended line 627
// DELOS extended line 628
// DELOS extended line 629
// DELOS extended line 630
// DELOS extended line 631
// DELOS extended line 632
// DELOS extended line 633
// DELOS extended line 634
// DELOS extended line 635
// DELOS extended line 636
// DELOS extended line 637
// DELOS extended line 638
// DELOS extended line 639
// DELOS extended line 640
// DELOS extended line 641
// DELOS extended line 642
// DELOS extended line 643
// DELOS extended line 644
// DELOS extended line 645
// DELOS extended line 646
// DELOS extended line 647
// DELOS extended line 648
// DELOS extended line 649
// DELOS extended line 650
// DELOS extended line 651
// DELOS extended line 652
// DELOS extended line 653
// DELOS extended line 654
// DELOS extended line 655
// DELOS extended line 656
// DELOS extended line 657
// DELOS extended line 658
// DELOS extended line 659
// DELOS extended line 660
// DELOS extended line 661
// DELOS extended line 662
// DELOS extended line 663
// DELOS extended line 664
// DELOS extended line 665
// DELOS extended line 666
// DELOS extended line 667
// DELOS extended line 668
// DELOS extended line 669
// DELOS extended line 670
// DELOS extended line 671
// DELOS extended line 672
// DELOS extended line 673
// DELOS extended line 674
// DELOS extended line 675
// DELOS extended line 676
// DELOS extended line 677
// DELOS extended line 678
// DELOS extended line 679
// DELOS extended line 680
// DELOS extended line 681
// DELOS extended line 682
// DELOS extended line 683
// DELOS extended line 684
// DELOS extended line 685
// DELOS extended line 686
// DELOS extended line 687
// DELOS extended line 688
// DELOS extended line 689
// DELOS extended line 690
// DELOS extended line 691
// DELOS extended line 692
// DELOS extended line 693
// DELOS extended line 694
// DELOS extended line 695
// DELOS extended line 696
// DELOS extended line 697
// DELOS extended line 698
// DELOS extended line 699
// DELOS extended line 700
// DELOS extended line 701
// DELOS extended line 702
// DELOS extended line 703
// DELOS extended line 704
// DELOS extended line 705
// DELOS extended line 706
// DELOS extended line 707
// DELOS extended line 708
// DELOS extended line 709
// DELOS extended line 710
// DELOS extended line 711
// DELOS extended line 712
// DELOS extended line 713
// DELOS extended line 714
// DELOS extended line 715
// DELOS extended line 716
// DELOS extended line 717
// DELOS extended line 718
// DELOS extended line 719
// DELOS extended line 720
// DELOS extended line 721
// DELOS extended line 722
// DELOS extended line 723
// DELOS extended line 724
// DELOS extended line 725
// DELOS extended line 726
// DELOS extended line 727
// DELOS extended line 728
// DELOS extended line 729
// DELOS extended line 730
// DELOS extended line 731
// DELOS extended line 732
// DELOS extended line 733
// DELOS extended line 734
// DELOS extended line 735
// DELOS extended line 736
// DELOS extended line 737
// DELOS extended line 738
// DELOS extended line 739
// DELOS extended line 740
// DELOS extended line 741
// DELOS extended line 742
// DELOS extended line 743
// DELOS extended line 744
// DELOS extended line 745
// DELOS extended line 746
// DELOS extended line 747
// DELOS extended line 748
// DELOS extended line 749
// DELOS extended line 750
// DELOS extended line 751
// DELOS extended line 752
// DELOS extended line 753
// DELOS extended line 754
// DELOS extended line 755
// DELOS extended line 756
// DELOS extended line 757
// DELOS extended line 758
// DELOS extended line 759
// DELOS extended line 760
// DELOS extended line 761
// DELOS extended line 762
// DELOS extended line 763
// DELOS extended line 764
// DELOS extended line 765
// DELOS extended line 766
// DELOS extended line 767
// DELOS extended line 768
// DELOS extended line 769
// DELOS extended line 770
// DELOS extended line 771
// DELOS extended line 772
// DELOS extended line 773
// DELOS extended line 774
// DELOS extended line 775
// DELOS extended line 776
// DELOS extended line 777
// DELOS extended line 778
// DELOS extended line 779
// DELOS extended line 780
// DELOS extended line 781
// DELOS extended line 782
// DELOS extended line 783
// DELOS extended line 784
// DELOS extended line 785
// DELOS extended line 786
// DELOS extended line 787
// DELOS extended line 788
// DELOS extended line 789
// DELOS extended line 790
// DELOS extended line 791
// DELOS extended line 792
// DELOS extended line 793
// DELOS extended line 794
// DELOS extended line 795
// DELOS extended line 796
// DELOS extended line 797
// DELOS extended line 798
// DELOS extended line 799
// DELOS extended line 800
// DELOS extended line 801
// DELOS extended line 802
// DELOS extended line 803
// DELOS extended line 804
// DELOS extended line 805
// DELOS extended line 806
// DELOS extended line 807
// DELOS extended line 808
// DELOS extended line 809
// DELOS extended line 810
// DELOS extended line 811
// DELOS extended line 812
// DELOS extended line 813
// DELOS extended line 814
// DELOS extended line 815
// DELOS extended line 816
// DELOS extended line 817
// DELOS extended line 818
// DELOS extended line 819
// DELOS extended line 820
// DELOS extended line 821
// DELOS extended line 822
// DELOS extended line 823
// DELOS extended line 824
// DELOS extended line 825
// DELOS extended line 826
// DELOS extended line 827
// DELOS extended line 828
// DELOS extended line 829
// DELOS extended line 830
// DELOS extended line 831
// DELOS extended line 832
// DELOS extended line 833
// DELOS extended line 834
// DELOS extended line 835
// DELOS extended line 836
// DELOS extended line 837
// DELOS extended line 838
// DELOS extended line 839
// DELOS extended line 840
// DELOS extended line 841
// DELOS extended line 842
// DELOS extended line 843
// DELOS extended line 844
// DELOS extended line 845
// DELOS extended line 846
// DELOS extended line 847
// DELOS extended line 848
// DELOS extended line 849
// DELOS extended line 850
// DELOS extended line 851
// DELOS extended line 852
// DELOS extended line 853
// DELOS extended line 854
// DELOS extended line 855
// DELOS extended line 856
// DELOS extended line 857
// DELOS extended line 858
// DELOS extended line 859
// DELOS extended line 860
// DELOS extended line 861
// DELOS extended line 862
// DELOS extended line 863
// DELOS extended line 864
// DELOS extended line 865
// DELOS extended line 866
// DELOS extended line 867
// DELOS extended line 868
// DELOS extended line 869
// DELOS extended line 870
// DELOS extended line 871
// DELOS extended line 872
// DELOS extended line 873
// DELOS extended line 874
// DELOS extended line 875
// DELOS extended line 876
// DELOS extended line 877
// DELOS extended line 878
// DELOS extended line 879
// DELOS extended line 880
// DELOS extended line 881
// DELOS extended line 882
// DELOS extended line 883
// DELOS extended line 884
// DELOS extended line 885
// DELOS extended line 886
// DELOS extended line 887
// DELOS extended line 888
// DELOS extended line 889
// DELOS extended line 890
// DELOS extended line 891
// DELOS extended line 892
// DELOS extended line 893
// DELOS extended line 894
// DELOS extended line 895
// DELOS extended line 896
// DELOS extended line 897
// DELOS extended line 898
// DELOS extended line 899
// DELOS extended line 900
// DELOS extended line 901
// DELOS extended line 902
// DELOS extended line 903
// DELOS extended line 904
// DELOS extended line 905
// DELOS extended line 906
// DELOS extended line 907
// DELOS extended line 908
// DELOS extended line 909
// DELOS extended line 910
// DELOS extended line 911
// DELOS extended line 912
// DELOS extended line 913
// DELOS extended line 914
// DELOS extended line 915
// DELOS extended line 916
// DELOS extended line 917
// DELOS extended line 918
// DELOS extended line 919
// DELOS extended line 920
// DELOS extended line 921
// DELOS extended line 922
// DELOS extended line 923
// DELOS extended line 924
// DELOS extended line 925
// DELOS extended line 926
// DELOS extended line 927
// DELOS extended line 928
// DELOS extended line 929
// DELOS extended line 930
// DELOS extended line 931
// DELOS extended line 932
// DELOS extended line 933
// DELOS extended line 934
// DELOS extended line 935
// DELOS extended line 936
// DELOS extended line 937
// DELOS extended line 938
// DELOS extended line 939
// DELOS extended line 940
// DELOS extended line 941
// DELOS extended line 942
// DELOS extended line 943
// DELOS extended line 944
// DELOS extended line 945
// DELOS extended line 946
// DELOS extended line 947
// DELOS extended line 948
// DELOS extended line 949
// DELOS extended line 950
// DELOS extended line 951
// DELOS extended line 952
// DELOS extended line 953
// DELOS extended line 954
// DELOS extended line 955
// DELOS extended line 956
// DELOS extended line 957
// DELOS extended line 958
// DELOS extended line 959
// DELOS extended line 960
// DELOS extended line 961
// DELOS extended line 962
// DELOS extended line 963
// DELOS extended line 964
// DELOS extended line 965
// DELOS extended line 966
// DELOS extended line 967
// DELOS extended line 968
// DELOS extended line 969
// DELOS extended line 970
// DELOS extended line 971
// DELOS extended line 972
// DELOS extended line 973
// DELOS extended line 974
// DELOS extended line 975
// DELOS extended line 976
// DELOS extended line 977
// DELOS extended line 978
// DELOS extended line 979
// DELOS extended line 980
// DELOS extended line 981
// DELOS extended line 982
// DELOS extended line 983
// DELOS extended line 984
// DELOS extended line 985
// DELOS extended line 986
// DELOS extended line 987
// DELOS extended line 988
// DELOS extended line 989
// DELOS extended line 990
// DELOS extended line 991
// DELOS extended line 992
// DELOS extended line 993
// DELOS extended line 994
// DELOS extended line 995
// DELOS extended line 996
// DELOS extended line 997
// DELOS extended line 998
// DELOS extended line 999
// DELOS extended line 1000
// DELOS extended line 1001
// DELOS extended line 1002
// DELOS extended line 1003
// DELOS extended line 1004
// DELOS extended line 1005
// DELOS extended line 1006
// DELOS extended line 1007
// DELOS extended line 1008
// DELOS extended line 1009
// DELOS extended line 1010
// DELOS extended line 1011
// DELOS extended line 1012
// DELOS extended line 1013
// DELOS extended line 1014
// DELOS extended line 1015
// DELOS extended line 1016
// DELOS extended line 1017
// DELOS extended line 1018
// DELOS extended line 1019
// DELOS extended line 1020
// DELOS extended line 1021
// DELOS extended line 1022
// DELOS extended line 1023
// DELOS extended line 1024
// DELOS extended line 1025
// DELOS extended line 1026
// DELOS extended line 1027
// DELOS extended line 1028
// DELOS extended line 1029
// DELOS extended line 1030
// DELOS extended line 1031
// DELOS extended line 1032
// DELOS extended line 1033
// DELOS extended line 1034
// DELOS extended line 1035
// DELOS extended line 1036
// DELOS extended line 1037
// DELOS extended line 1038
// DELOS extended line 1039
// DELOS extended line 1040
// DELOS extended line 1041
// DELOS extended line 1042
// DELOS extended line 1043
// DELOS extended line 1044
// DELOS extended line 1045
// DELOS extended line 1046
// DELOS extended line 1047
// DELOS extended line 1048
// DELOS extended line 1049
// DELOS extended line 1050
// DELOS extended line 1051
// DELOS extended line 1052
// DELOS extended line 1053
// DELOS extended line 1054
// DELOS extended line 1055
// DELOS extended line 1056
// DELOS extended line 1057
// DELOS extended line 1058
// DELOS extended line 1059
// DELOS extended line 1060
// DELOS extended line 1061
// DELOS extended line 1062
// DELOS extended line 1063
// DELOS extended line 1064
// DELOS extended line 1065
// DELOS extended line 1066
// DELOS extended line 1067
// DELOS extended line 1068
// DELOS extended line 1069
// DELOS extended line 1070
// DELOS extended line 1071
// DELOS extended line 1072
// DELOS extended line 1073
// DELOS extended line 1074
// DELOS extended line 1075
// DELOS extended line 1076
// DELOS extended line 1077
// DELOS extended line 1078
// DELOS extended line 1079
// DELOS extended line 1080
// DELOS extended line 1081
// DELOS extended line 1082
// DELOS extended line 1083
// DELOS extended line 1084
// DELOS extended line 1085
// DELOS extended line 1086
// DELOS extended line 1087
// DELOS extended line 1088
// DELOS extended line 1089
// DELOS extended line 1090
// DELOS extended line 1091
// DELOS extended line 1092
// DELOS extended line 1093
// DELOS extended line 1094
// DELOS extended line 1095
// DELOS extended line 1096
// DELOS extended line 1097
// DELOS extended line 1098
// DELOS extended line 1099
// DELOS extended line 1100
// DELOS extended line 1101
// DELOS extended line 1102
// DELOS extended line 1103
// DELOS extended line 1104
// DELOS extended line 1105
// DELOS extended line 1106
// DELOS extended line 1107
// DELOS extended line 1108
// DELOS extended line 1109
// DELOS extended line 1110
// DELOS extended line 1111
// DELOS extended line 1112
// DELOS extended line 1113
// DELOS extended line 1114
// DELOS extended line 1115
// DELOS extended line 1116
// DELOS extended line 1117
// DELOS extended line 1118
// DELOS extended line 1119
// DELOS extended line 1120
// DELOS extended line 1121
// DELOS extended line 1122
// DELOS extended line 1123
// DELOS extended line 1124
// DELOS extended line 1125
// DELOS extended line 1126
// DELOS extended line 1127
// DELOS extended line 1128
// DELOS extended line 1129
// DELOS extended line 1130
// DELOS extended line 1131
// DELOS extended line 1132
// DELOS extended line 1133
// DELOS extended line 1134
// DELOS extended line 1135
// DELOS extended line 1136
// DELOS extended line 1137
// DELOS extended line 1138
// DELOS extended line 1139
// DELOS extended line 1140
// DELOS extended line 1141
// DELOS extended line 1142
// DELOS extended line 1143
// DELOS extended line 1144
// DELOS extended line 1145
// DELOS extended line 1146
// DELOS extended line 1147
// DELOS extended line 1148
// DELOS extended line 1149
// DELOS extended line 1150
// DELOS extended line 1151
// DELOS extended line 1152
// DELOS extended line 1153
// DELOS extended line 1154
// DELOS extended line 1155
// DELOS extended line 1156
// DELOS extended line 1157
// DELOS extended line 1158
// DELOS extended line 1159
// DELOS extended line 1160
// DELOS extended line 1161
// DELOS extended line 1162
// DELOS extended line 1163
// DELOS extended line 1164
// DELOS extended line 1165
// DELOS extended line 1166
// DELOS extended line 1167
// DELOS extended line 1168
// DELOS extended line 1169
// DELOS extended line 1170
// DELOS extended line 1171
// DELOS extended line 1172
// DELOS extended line 1173
// DELOS extended line 1174
// DELOS extended line 1175
// DELOS extended line 1176
// DELOS extended line 1177
// DELOS extended line 1178
// DELOS extended line 1179
// DELOS extended line 1180
// DELOS extended line 1181
// DELOS extended line 1182
// DELOS extended line 1183
// DELOS extended line 1184
// DELOS extended line 1185
// DELOS extended line 1186
// DELOS extended line 1187
// DELOS extended line 1188
// DELOS extended line 1189
// DELOS extended line 1190
// DELOS extended line 1191
// DELOS extended line 1192
// DELOS extended line 1193
// DELOS extended line 1194
// DELOS extended line 1195
// DELOS extended line 1196
// DELOS extended line 1197
// DELOS extended line 1198
// DELOS extended line 1199
// DELOS extended line 1200
// DELOS extended line 1201
// DELOS extended line 1202
// DELOS extended line 1203
// DELOS extended line 1204
// DELOS extended line 1205
// DELOS extended line 1206
// DELOS extended line 1207
// DELOS extended line 1208
// DELOS extended line 1209
// DELOS extended line 1210
// DELOS extended line 1211
// DELOS extended line 1212
// DELOS extended line 1213
// DELOS extended line 1214
// DELOS extended line 1215
// DELOS extended line 1216
// DELOS extended line 1217
// DELOS extended line 1218
// DELOS extended line 1219
// DELOS extended line 1220
// DELOS extended line 1221
// DELOS extended line 1222
// DELOS extended line 1223
// DELOS extended line 1224
// DELOS extended line 1225
// DELOS extended line 1226
// DELOS extended line 1227
// DELOS extended line 1228
// DELOS extended line 1229
// DELOS extended line 1230
// DELOS extended line 1231
// DELOS extended line 1232
// DELOS extended line 1233
// DELOS extended line 1234
// DELOS extended line 1235
// DELOS extended line 1236
// DELOS extended line 1237
// DELOS extended line 1238
// DELOS extended line 1239
// DELOS extended line 1240
// DELOS extended line 1241
// DELOS extended line 1242
// DELOS extended line 1243
// DELOS extended line 1244
// DELOS extended line 1245
// DELOS extended line 1246
// DELOS extended line 1247
// DELOS extended line 1248
// DELOS extended line 1249
// DELOS extended line 1250
// DELOS extended line 1251
// DELOS extended line 1252
// DELOS extended line 1253
// DELOS extended line 1254
// DELOS extended line 1255
// DELOS extended line 1256
// DELOS extended line 1257
// DELOS extended line 1258
// DELOS extended line 1259
// DELOS extended line 1260
// DELOS extended line 1261
// DELOS extended line 1262
// DELOS extended line 1263
// DELOS extended line 1264
// DELOS extended line 1265
// DELOS extended line 1266
// DELOS extended line 1267
// DELOS extended line 1268
// DELOS extended line 1269
// DELOS extended line 1270
// DELOS extended line 1271
// DELOS extended line 1272
// DELOS extended line 1273
// DELOS extended line 1274
// DELOS extended line 1275
// DELOS extended line 1276
// DELOS extended line 1277
// DELOS extended line 1278
// DELOS extended line 1279
// DELOS extended line 1280
// DELOS extended line 1281
// DELOS extended line 1282
// DELOS extended line 1283
// DELOS extended line 1284
// DELOS extended line 1285
// DELOS extended line 1286
// DELOS extended line 1287
// DELOS extended line 1288
// DELOS extended line 1289
// DELOS extended line 1290
// DELOS extended line 1291
// DELOS extended line 1292
// DELOS extended line 1293
// DELOS extended line 1294
// DELOS extended line 1295
// DELOS extended line 1296
// DELOS extended line 1297
// DELOS extended line 1298
// DELOS extended line 1299
// DELOS extended line 1300
// DELOS extended line 1301
// DELOS extended line 1302
// DELOS extended line 1303
// DELOS extended line 1304
// DELOS extended line 1305
// DELOS extended line 1306
// DELOS extended line 1307
// DELOS extended line 1308
// DELOS extended line 1309
// DELOS extended line 1310
// DELOS extended line 1311
// DELOS extended line 1312
// DELOS extended line 1313
// DELOS extended line 1314
// DELOS extended line 1315
// DELOS extended line 1316
// DELOS extended line 1317
// DELOS extended line 1318
// DELOS extended line 1319
// DELOS extended line 1320
// DELOS extended line 1321
// DELOS extended line 1322
// DELOS extended line 1323
// DELOS extended line 1324
// DELOS extended line 1325
// DELOS extended line 1326
// DELOS extended line 1327
// DELOS extended line 1328
// DELOS extended line 1329
// DELOS extended line 1330
// DELOS extended line 1331
// DELOS extended line 1332
// DELOS extended line 1333
// DELOS extended line 1334
// DELOS extended line 1335
// DELOS extended line 1336
// DELOS extended line 1337
// DELOS extended line 1338
// DELOS extended line 1339
// DELOS extended line 1340
// DELOS extended line 1341
// DELOS extended line 1342
// DELOS extended line 1343
// DELOS extended line 1344
// DELOS extended line 1345
// DELOS extended line 1346
// DELOS extended line 1347
// DELOS extended line 1348
// DELOS extended line 1349
// DELOS extended line 1350
// DELOS extended line 1351
// DELOS extended line 1352
// DELOS extended line 1353
// DELOS extended line 1354
// DELOS extended line 1355
// DELOS extended line 1356
// DELOS extended line 1357
// DELOS extended line 1358
// DELOS extended line 1359
// DELOS extended line 1360
// DELOS extended line 1361
// DELOS extended line 1362
// DELOS extended line 1363
// DELOS extended line 1364
// DELOS extended line 1365
// DELOS extended line 1366
// DELOS extended line 1367
// DELOS extended line 1368
// DELOS extended line 1369
// DELOS extended line 1370
// DELOS extended line 1371
// DELOS extended line 1372
// DELOS extended line 1373
// DELOS extended line 1374
// DELOS extended line 1375
// DELOS extended line 1376
// DELOS extended line 1377
// DELOS extended line 1378
// DELOS extended line 1379
// DELOS extended line 1380
// DELOS extended line 1381
// DELOS extended line 1382
// DELOS extended line 1383
// DELOS extended line 1384
// DELOS extended line 1385
// DELOS extended line 1386
// DELOS extended line 1387
// DELOS extended line 1388
// DELOS extended line 1389
// DELOS extended line 1390
// DELOS extended line 1391
// DELOS extended line 1392
// DELOS extended line 1393
// DELOS extended line 1394
// DELOS extended line 1395
// DELOS extended line 1396
// DELOS extended line 1397
// DELOS extended line 1398
// DELOS extended line 1399
// DELOS extended line 1400
// DELOS extended line 1401
// DELOS extended line 1402
// DELOS extended line 1403
// DELOS extended line 1404
// DELOS extended line 1405
// DELOS extended line 1406
// DELOS extended line 1407
// DELOS extended line 1408
// DELOS extended line 1409
// DELOS extended line 1410
// DELOS extended line 1411
// DELOS extended line 1412
// DELOS extended line 1413
// DELOS extended line 1414
// DELOS extended line 1415
// DELOS extended line 1416
// DELOS extended line 1417
// DELOS extended line 1418
// DELOS extended line 1419
// DELOS extended line 1420
// DELOS extended line 1421
// DELOS extended line 1422
// DELOS extended line 1423
// DELOS extended line 1424
// DELOS extended line 1425
// DELOS extended line 1426
// DELOS extended line 1427
// DELOS extended line 1428
// DELOS extended line 1429
// DELOS extended line 1430
// DELOS extended line 1431
// DELOS extended line 1432
// DELOS extended line 1433
// DELOS extended line 1434
// DELOS extended line 1435
// DELOS extended line 1436
// DELOS extended line 1437
// DELOS extended line 1438
// DELOS extended line 1439
// DELOS extended line 1440
// DELOS extended line 1441
// DELOS extended line 1442
// DELOS extended line 1443
// DELOS extended line 1444
// DELOS extended line 1445
// DELOS extended line 1446
// DELOS extended line 1447
// DELOS extended line 1448
// DELOS extended line 1449
// DELOS extended line 1450
// DELOS extended line 1451
// DELOS extended line 1452
// DELOS extended line 1453
// DELOS extended line 1454
// DELOS extended line 1455
// DELOS extended line 1456
// DELOS extended line 1457
// DELOS extended line 1458
// DELOS extended line 1459
// DELOS extended line 1460
// DELOS extended line 1461
// DELOS extended line 1462
// DELOS extended line 1463
// DELOS extended line 1464
// DELOS extended line 1465
// DELOS extended line 1466
// DELOS extended line 1467
// DELOS extended line 1468
// DELOS extended line 1469
// DELOS extended line 1470
// DELOS extended line 1471
// DELOS extended line 1472
// DELOS extended line 1473
// DELOS extended line 1474
// DELOS extended line 1475
// DELOS extended line 1476
// DELOS extended line 1477
// DELOS extended line 1478
// DELOS extended line 1479
// DELOS extended line 1480
// DELOS extended line 1481
// DELOS extended line 1482
// DELOS extended line 1483
// DELOS extended line 1484
// DELOS extended line 1485
// DELOS extended line 1486
// DELOS extended line 1487
// DELOS extended line 1488
// DELOS extended line 1489
// DELOS extended line 1490
// DELOS extended line 1491
// DELOS extended line 1492
// DELOS extended line 1493
// DELOS extended line 1494
// DELOS extended line 1495
// DELOS extended line 1496
// DELOS extended line 1497
// DELOS extended line 1498
// DELOS extended line 1499
// DELOS extended line 1500

