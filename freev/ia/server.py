#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════╗
║  FREEV AI — Serveur (local + Render.com)                 ║
║  Local  : python server.py → localhost:7432              ║
║  Render : start command    → 0.0.0.0:$PORT               ║
╚══════════════════════════════════════════════════════════╝
"""

import json
import os
import sys
import urllib.parse
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(errors='replace')
    except Exception:
        pass

# ── Port : Render impose $PORT, sinon 7432 en local ──────────────────────────
PORT = int(os.environ.get('PORT', 7432))
HOST = '0.0.0.0'   # IMPORTANT : pas localhost — Render ne peut pas y accéder

# ── Origines autorisées pour le CORS ─────────────────────────────────────────
# Ajoute ici l'URL de ton site hébergé par l'IT (ex: https://monsite.example.com)
ALLOWED_ORIGINS = [
    'http://localhost',
    'http://127.0.0.1',
    'https://trystan2340.github.io',
    'null',           # ouverture directe d'un fichier .html en local
]
ALLOWED_ORIGINS.extend(
    item.strip() for item in os.environ.get('ALLOWED_ORIGINS', '').split(',') if item.strip()
)
MAX_BODY_BYTES = 16 * 1024
BASE_DIR = Path(__file__).resolve().parent

# ── Charger FreevBrain ────────────────────────────────────────────────────────
print("⏳ Chargement de FreevBrain v7...", flush=True)
try:
    from brain import Freev
    freev = Freev()
    print(f"✅ FreevBrain prêt — {len(freev.brain.training_data)} paires chargées", flush=True)
except Exception as e:
    print(f"❌ Erreur chargement FreevBrain : {e}", flush=True)
    print("   Assure-toi que brain.py et freev_data.txt sont dans le même dossier.", flush=True)
    sys.exit(1)


# ── Handler HTTP ──────────────────────────────────────────────────────────────
class FreevHandler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        """Log minimal : seulement les requêtes POST /api/chat et les erreurs."""
        if '/api/chat' in str(args):
            print(f"  [{args[1]}] {self.command} {self.path}", flush=True)

    def _cors_headers(self):
        """Headers CORS — autorise le navigateur à appeler ce serveur."""
        origin = self.headers.get('Origin', '')
        allowed = 'null'
        if origin == 'null':
            allowed = 'null'
        elif any(origin == item or origin.startswith(item + ':') for item in ALLOWED_ORIGINS):
            allowed = origin
        elif origin.endswith('.github.io') or '.github.io/' in origin:
            allowed = origin
        self.send_header('Access-Control-Allow-Origin', allowed)
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Vary', 'Origin')

    def do_OPTIONS(self):
        """Réponse pre-flight CORS (navigateur l'envoie avant chaque POST)."""
        self.send_response(204)
        self._cors_headers()
        self.end_headers()

    def do_GET(self):
        """GET /status — vérifie que le serveur est vivant."""
        path = urllib.parse.urlparse(self.path).path
        if path == '/status':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self._cors_headers()
            self.end_headers()
            status = {
                'ok': True,
                'version': freev.VERSION,
                'trained': freev.brain.trained,
                'pairs': len(freev.brain.training_data),
                'personality': freev.personality,
            }
            self.wfile.write(json.dumps(status, ensure_ascii=False).encode())
        elif path == '/api/admin/status':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self._cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps(self._admin_status(), ensure_ascii=False).encode('utf-8'))
        elif path == '/api/admin/unknown':
            if not self._check_admin_auth():
                self._error(401, 'Token admin requis')
                return
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self._cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({'items': self._load_unknown_items()}, ensure_ascii=False).encode('utf-8'))
        elif path == '/admin':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self._cors_headers()
            self.end_headers()
            self.wfile.write(self._admin_html().encode('utf-8'))
        elif path == '/':
            # Page d'accueil simple si on visite l'URL Render directement
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self._cors_headers()
            self.end_headers()
            html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Freev AI Server</title>
<style>body{{font-family:monospace;background:#0f172a;color:#22d3ee;padding:2rem}}</style>
</head><body>
<h1>🤖 Freev AI Server v{freev.VERSION}</h1>
<p>✅ FreevBrain actif — {len(freev.brain.training_data)} paires</p>
<p>POST /api/chat — envoyer {{"message": "ta question"}}</p>
<p>GET  /status   — vérifier l'état</p>
</body></html>"""
            self.wfile.write(html.encode())
        else:
            self.send_response(404)
            self._cors_headers()
            self.end_headers()

    def do_POST(self):
        """POST /api/chat — endpoint principal."""
        path = urllib.parse.urlparse(self.path).path
        if path == '/api/admin/retrain':
            if not self._check_admin_auth():
                self._error(401, 'Token admin requis')
                return
            try:
                ok = freev.brain.train()
                self.send_response(200 if ok else 500)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self._cors_headers()
                self.end_headers()
                payload = self._admin_status()
                payload['retrained'] = bool(ok)
                self.wfile.write(json.dumps(payload, ensure_ascii=False).encode('utf-8'))
            except Exception as e:
                self._error(500, str(e))
            return

        if path == '/api/admin/learn':
            if not self._check_admin_auth():
                self._error(401, 'Token admin requis')
                return
            try:
                body = self._read_json_body()
                question = str(body.get('question', '')).strip()
                answer = str(body.get('answer', '')).strip()
                if not question or not answer:
                    raise ValueError('Question et réponse obligatoires')
                freev.brain.learn(question, answer)
                updated = self._mark_unknown_learned(question, answer)
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self._cors_headers()
                self.end_headers()
                payload = self._admin_status()
                payload.update({'learned': True, 'pending_updated': updated})
                self.wfile.write(json.dumps(payload, ensure_ascii=False).encode('utf-8'))
            except json.JSONDecodeError:
                self._error(400, 'JSON invalide')
            except Exception as e:
                self._error(500, str(e))
            return

        if path != '/api/chat':
            self.send_response(404)
            self._cors_headers()
            self.end_headers()
            return

        try:
            length = int(self.headers.get('Content-Length', 0))
            if length <= 0:
                raise ValueError('Corps de requête vide')
            if length > MAX_BODY_BYTES:
                self._error(413, 'Message trop long')
                return

            raw = self.rfile.read(length).decode('utf-8')
            body = json.loads(raw)
            if not isinstance(body, dict):
                raise ValueError('JSON objet attendu')
            message = str(body.get('message', '')).strip()

            if not message:
                raise ValueError('Message vide')

            # ── Réponse FreevBrain ──────────────────────────────────────────
            response = freev.generate_response(message)
            if not response:
                response = "Je n'ai pas compris. Reformule ta question !"
            unknown_saved = False
            if response.startswith(freev.brain.UNCERTAIN_RESPONSE):
                unknown_saved = freev.brain.record_unknown_question(message, source='web')
                if unknown_saved:
                    response += "\n\nJe viens d'enregistrer ta question dans les demandes d'apprentissage. Il faudra ajouter une réponse validée pour qu'elle devienne une vraie connaissance."

            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self._cors_headers()
            self.end_headers()
            self.wfile.write(
                json.dumps({'response': response, 'unknown_saved': unknown_saved}, ensure_ascii=False).encode('utf-8')
            )

        except json.JSONDecodeError:
            self._error(400, 'JSON invalide')
        except Exception as e:
            self._error(500, str(e))

    def _error(self, code, msg):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self._cors_headers()
        self.end_headers()
        self.wfile.write(json.dumps({'error': msg}, ensure_ascii=False).encode('utf-8'))

    def _read_json_body(self):
        length = int(self.headers.get('Content-Length', 0))
        if length <= 0:
            raise ValueError('Corps de requête vide')
        if length > MAX_BODY_BYTES:
            raise ValueError('Message trop long')
        raw = self.rfile.read(length).decode('utf-8')
        body = json.loads(raw)
        if not isinstance(body, dict):
            raise ValueError('JSON objet attendu')
        return body

    def _check_admin_auth(self):
        token = os.environ.get('ADMIN_TOKEN', '').strip()
        if not token:
            return True
        return self.headers.get('X-Admin-Token', '').strip() == token

    def _load_unknown_items(self):
        path = freev.brain.UNKNOWN_FILE
        items = []
        if not path.exists():
            return items
        try:
            with open(path, encoding='utf-8') as f:
                for idx, line in enumerate(f):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        item = json.loads(line)
                    except Exception:
                        continue
                    item.setdefault('id', idx)
                    if item.get('status', 'pending_answer') == 'pending_answer':
                        items.append(item)
        except Exception:
            return []
        return items

    def _mark_unknown_learned(self, question, answer):
        path = freev.brain.UNKNOWN_FILE
        if not path.exists():
            return False
        wanted = freev.brain._normalize_text(question)
        changed = False
        rows = []
        try:
            with open(path, encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        item = json.loads(line)
                    except Exception:
                        rows.append(line)
                        continue
                    if freev.brain._normalize_text(item.get('question', '')) == wanted:
                        item['status'] = 'learned'
                        item['answer'] = answer
                        item['learned_at'] = __import__('datetime').datetime.utcnow().isoformat(timespec='seconds') + 'Z'
                        changed = True
                    rows.append(json.dumps(item, ensure_ascii=False))
            with open(path, 'w', encoding='utf-8') as f:
                if rows:
                    f.write('\n'.join(rows) + '\n')
        except Exception:
            return False
        return changed

    def _admin_status(self):
        eval_path = BASE_DIR / 'freev_eval.txt'
        memory_path = BASE_DIR / 'vocal_history.json'
        eval_pairs = 0
        if eval_path.exists():
            try:
                eval_pairs = len(freev.brain.tester.load_test_file(str(eval_path)))
            except Exception:
                eval_pairs = 0
        memory_entries = 0
        unknown_pending = 0
        if memory_path.exists():
            try:
                data = json.loads(memory_path.read_text(encoding='utf-8'))
                memory_entries = len(data) if isinstance(data, list) else 0
            except Exception:
                memory_entries = 0
        unknown_path = freev.brain.UNKNOWN_FILE
        if unknown_path.exists():
            try:
                unknown_pending = len(self._load_unknown_items())
            except Exception:
                unknown_pending = 0
        return {
            'ok': True,
            'version': freev.VERSION,
            'brain_version': freev.brain.MODEL_VERSION,
            'trained': freev.brain.trained,
            'pairs': len(freev.brain.training_data),
            'vocabulary': len(freev.brain.vocabulary),
            'eval_pairs': eval_pairs,
            'memory_entries': memory_entries,
            'unknown_pending': unknown_pending,
            'voice_history_file': str(memory_path),
            'data_file': str(freev.brain._find_data_file() or ''),
        }

    def _admin_html(self):
        return """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Freev Admin</title>
<style>
body{margin:0;font-family:Arial,sans-serif;background:#f6f7f9;color:#17202a}
main{max-width:1060px;margin:0 auto;padding:28px}
h1{font-size:28px;margin:0 0 18px}
h2{font-size:20px;margin:28px 0 12px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px}
.card{background:white;border:1px solid #d9dee7;border-radius:8px;padding:16px}
.label{font-size:12px;color:#5b6675;text-transform:uppercase}
.value{font-size:26px;font-weight:700;margin-top:8px}
button{border:0;border-radius:6px;background:#0f766e;color:white;padding:10px 14px;font-weight:700;cursor:pointer}
button.secondary{background:#334155}
button:disabled{opacity:.5;cursor:not-allowed}
input,textarea{width:100%;box-sizing:border-box;border:1px solid #cbd5e1;border-radius:6px;padding:10px;font:inherit}
textarea{min-height:92px;resize:vertical}
.toolbar{display:flex;gap:10px;align-items:center;margin:18px 0;flex-wrap:wrap}
.toolbar input{max-width:320px}
.unknown{background:white;border:1px solid #d9dee7;border-radius:8px;padding:16px;margin:12px 0}
.question{font-weight:700;margin-bottom:8px}
.meta{font-size:12px;color:#64748b;margin-bottom:12px}
.actions{display:flex;gap:10px;margin-top:10px;align-items:center}
.empty{background:#e2e8f0;border-radius:8px;padding:16px;color:#475569}
pre{background:#111827;color:#d1fae5;border-radius:8px;padding:14px;overflow:auto}
</style>
</head>
<body>
<main>
<h1>Freev Admin</h1>
<section class="grid" id="cards"></section>
<div class="toolbar">
  <input id="token" type="password" placeholder="Token admin si configuré">
  <button id="saveToken" class="secondary">Sauver token</button>
  <button id="reload">Rafraîchir</button>
  <button id="retrain">Réentraîner</button>
</div>
<h2>Questions à apprendre</h2>
<section id="unknownList" class="empty">Chargement...</section>
<pre id="raw">Chargement...</pre>
</main>
<script>
const tokenInput=document.getElementById('token');
tokenInput.value=localStorage.getItem('freev_admin_token')||'';
function headers(){const t=tokenInput.value.trim();return t?{'X-Admin-Token':t}:{};}
function jsonHeaders(){return Object.assign({'Content-Type':'application/json'},headers());}
saveToken.onclick=()=>{localStorage.setItem('freev_admin_token',tokenInput.value.trim());refresh();};
async function refresh(){
  const r=await fetch('/api/admin/status');
  const s=await r.json();
  const items=[
    ['Paires',s.pairs],['Vocabulaire',s.vocabulary],['Benchmark',s.eval_pairs],
    ['À apprendre',s.unknown_pending],['Mémoire vocale',s.memory_entries],['Version',s.brain_version]
  ];
  cards.innerHTML=items.map(([k,v])=>`<article class="card"><div class="label">${k}</div><div class="value">${v}</div></article>`).join('');
  raw.textContent=JSON.stringify(s,null,2);
  await loadUnknown();
}
async function loadUnknown(){
  const list=document.getElementById('unknownList');
  const r=await fetch('/api/admin/unknown',{headers:headers()});
  if(r.status===401){list.className='empty';list.textContent='Token admin requis.';return;}
  const data=await r.json();
  const items=data.items||[];
  if(!items.length){list.className='empty';list.textContent='Aucune question en attente.';return;}
  list.className='';
  list.innerHTML=items.map((item,idx)=>`
    <article class="unknown">
      <div class="question">${escapeHtml(item.question||'')}</div>
      <div class="meta">${escapeHtml(item.timestamp||'')} · ${escapeHtml(item.source||'web')}</div>
      <textarea id="answer-${idx}" placeholder="Réponse validée à apprendre..."></textarea>
      <div class="actions">
        <button onclick="learn(${idx})">Valider et apprendre</button>
      </div>
    </article>`).join('');
  window.pendingUnknown=items;
}
async function learn(idx){
  const item=(window.pendingUnknown||[])[idx];
  const answer=document.getElementById('answer-'+idx).value.trim();
  if(!item||!answer){alert('Ajoute une réponse validée.');return;}
  const r=await fetch('/api/admin/learn',{method:'POST',headers:jsonHeaders(),body:JSON.stringify({question:item.question,answer})});
  if(!r.ok){alert(await r.text());return;}
  await refresh();
}
function escapeHtml(t){return String(t).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}
reload.onclick=refresh;
retrain.onclick=async()=>{retrain.disabled=true;raw.textContent='Réentraînement...';await fetch('/api/admin/retrain',{method:'POST',headers:headers()});retrain.disabled=false;refresh();};
refresh();
</script>
</body>
</html>"""


# ── Lancement ─────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    server = HTTPServer((HOST, PORT), FreevHandler)
    env    = 'Render' if os.environ.get('PORT') else 'Local'
    print(f'', flush=True)
    print(f'╔══════════════════════════════════════════════════╗', flush=True)
    print(f'║  🤖 Freev AI Server — {env}                       ', flush=True)
    print(f'║  Écoute sur {HOST}:{PORT}                        ', flush=True)
    print(f'╚══════════════════════════════════════════════════╝', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\n👋 Serveur arrêté.', flush=True)
        server.server_close()
