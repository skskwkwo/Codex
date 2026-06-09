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


