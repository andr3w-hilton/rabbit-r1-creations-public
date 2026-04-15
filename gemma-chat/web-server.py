"""Static file server for R1 creations + Gemma 4 proxy + chat export."""
import html as html_lib
import json
import os
import random
import string
import time
import urllib.request
import urllib.error
from http.server import HTTPServer, SimpleHTTPRequestHandler

DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(DIR)

EXPORTS_DIR = os.path.join(DIR, 'exports')
os.makedirs(EXPORTS_DIR, exist_ok=True)

GOOGLE_AI_API_KEY = os.environ.get('GOOGLE_AI_API_KEY', '')
GEMMA_MODEL = os.environ.get('GEMMA_MODEL', 'gemma-4-26b-a4b-it')
BASE_URL = os.environ.get('BASE_URL', 'https://r1.youvebeenpwnd.com')


def make_id(length=7):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))


class Handler(SimpleHTTPRequestHandler):

    # ── Routing ──────────────────────────────────
    def do_GET(self):
        path = self.path.split('?')[0]
        if path.startswith('/chat-export/') and len(path) > len('/chat-export/'):
            self._serve_export(path[len('/chat-export/'):])
        else:
            super().do_GET()

    def do_POST(self):
        if self.path == '/gemma-proxy':
            self._handle_gemma()
        elif self.path == '/chat-export':
            self._handle_export()
        else:
            self.send_error(404)

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    # ── Gemma proxy ──────────────────────────────
    def _handle_gemma(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(length)) if length else {}

            contents = []
            for m in body.get('messages', []):
                role = 'user' if m.get('role') == 'user' else 'model'
                contents.append({'role': role, 'parts': [{'text': m.get('content', '')}]})

            url = (
                'https://generativelanguage.googleapis.com/v1beta/models/'
                + GEMMA_MODEL + ':generateContent?key=' + GOOGLE_AI_API_KEY
            )
            payload = json.dumps({
                'systemInstruction': {'parts': [{'text': (
                    'You are a helpful AI assistant running on a Rabbit R1 device. '
                    'Be concise and conversational. '
                    'Do NOT show your reasoning, thinking steps, bullet points, or chain-of-thought. '
                    'Reply directly with your final answer only. '
                    'Keep responses short — 1 to 3 sentences unless more detail is genuinely needed.'
                )}]},
                'contents': contents,
                'generationConfig': {'temperature': 0.7, 'maxOutputTokens': 512},
            }).encode('utf-8')

            req = urllib.request.Request(url, data=payload,
                headers={'Content-Type': 'application/json'}, method='POST')
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read())

            parts = result['candidates'][0]['content']['parts']
            text = ' '.join(
                p['text'] for p in parts
                if p.get('text') and not p.get('thought', False)
            ).strip()
            self._json_response(200, {'text': text})

        except urllib.error.HTTPError as e:
            err_body = e.read().decode('utf-8', errors='replace')
            print(f'[gemma-proxy] HTTP {e.code}: {err_body[:200]}')
            self._json_response(502, {'error': f'Upstream error {e.code}: {err_body[:120]}'})
        except Exception as e:
            print(f'[gemma-proxy] error: {e}')
            self._json_response(500, {'error': str(e)})

    # ── Chat export: save ─────────────────────────
    def _handle_export(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(length)) if length else {}

            export_id = make_id()
            data = {
                'id': export_id,
                'created': int(time.time()),
                'messages': body.get('messages', []),
            }

            path = os.path.join(EXPORTS_DIR, export_id + '.json')
            with open(path, 'w') as f:
                json.dump(data, f)

            self._json_response(200, {
                'id': export_id,
                'url': BASE_URL + '/chat-export/' + export_id,
            })
        except Exception as e:
            print(f'[chat-export] error: {e}')
            self._json_response(500, {'error': str(e)})

    # ── Chat export: serve reading page ──────────
    def _serve_export(self, export_id):
        # Sanitise ID — alphanumeric only
        safe_id = ''.join(c for c in export_id if c.isalnum())
        path = os.path.join(EXPORTS_DIR, safe_id + '.json')

        if not os.path.exists(path):
            self.send_error(404, 'Export not found')
            return

        with open(path) as f:
            data = json.load(f)

        created = time.strftime('%d %b %Y, %H:%M', time.localtime(data.get('created', 0)))
        messages = data.get('messages', [])

        bubbles_html = ''
        for m in messages:
            role = m.get('role', 'user')
            content = html_lib.escape(m.get('content', ''))
            label = 'You' if role == 'user' else 'Gemma 4'
            cls = 'user' if role == 'user' else 'gemma'
            bubbles_html += f'<div class="msg {cls}"><div class="label">{label}</div><div class="text">{content}</div></div>\n'

        page = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>R1 Chat Export</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
  background: #0e0e10; color: #fff;
  font-family: -apple-system, BlinkMacSystemFont, sans-serif;
  min-height: 100vh; padding: 24px 16px 48px;
}}
header {{
  display: flex; align-items: baseline; justify-content: space-between;
  margin-bottom: 24px; padding-bottom: 12px;
  border-bottom: 1px solid rgba(254,80,0,0.2);
}}
header h1 {{ font-size: 16px; font-weight: 700; color: #FE5000; letter-spacing: 1px; }}
header time {{ font-size: 11px; color: rgba(255,255,255,0.3); }}
.msg {{ margin-bottom: 14px; max-width: 480px; }}
.msg.user {{ margin-left: auto; text-align: right; }}
.label {{
  font-size: 10px; font-weight: 600; letter-spacing: 1px; text-transform: uppercase;
  margin-bottom: 4px; color: rgba(255,255,255,0.3);
}}
.msg.gemma .label {{ color: rgba(254,80,0,0.6); }}
.text {{
  display: inline-block; padding: 8px 12px; border-radius: 12px;
  font-size: 14px; line-height: 1.55; white-space: pre-wrap; word-break: break-word;
}}
.msg.user .text {{ background: rgba(255,255,255,0.07); border-bottom-right-radius: 3px; }}
.msg.gemma .text {{ background: rgba(254,80,0,0.1); border-bottom-left-radius: 3px; }}
</style>
</head>
<body>
<header>
  <h1>R1 Chat</h1>
  <time>{created}</time>
</header>
{bubbles_html}
</body>
</html>'''

        body = page.encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    # ── Helpers ──────────────────────────────────
    def _json_response(self, code, data):
        body = json.dumps(data).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def _cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def end_headers(self):
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()

    def log_message(self, fmt, *args):
        print(f'[server] {args[0]}')


if __name__ == '__main__':
    if not GOOGLE_AI_API_KEY:
        print('WARNING: GOOGLE_AI_API_KEY is not set — /gemma-proxy will fail')
    print(f'Using model: {GEMMA_MODEL}')
    server = HTTPServer(('0.0.0.0', 8082), Handler)
    print('Server running on http://0.0.0.0:8082')
    server.serve_forever()
