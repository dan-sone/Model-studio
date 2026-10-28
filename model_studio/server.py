"""Single shared workspace. Deploy behind an HTTPS reverse proxy."""
import hashlib
import hmac
import json
import os
import secrets
import time
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from . import provider
from .domain import Rejected
from .store import Store, Conflict

STATIC = Path(__file__).resolve().parent.parent / 'static'


def make_handler(store, password):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass  # Do not log model content, cookies or provider errors.

        def send(self, status, value, content_type='application/json; charset=utf-8', cookie=None):
            body = value if isinstance(value, bytes) else json.dumps(value, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'")
            if cookie:
                self.send_header('Set-Cookie', cookie)
            self.end_headers()
            self.wfile.write(body)

        def authorized(self):
            if not password:
                return True
            try:
                cookies = SimpleCookie(self.headers.get('Cookie', ''))
                token = cookies['session'].value
                digest = hashlib.sha256(token.encode()).hexdigest()
                with store.connect() as db:
                    return db.execute('SELECT 1 FROM sessions WHERE token=? AND expires>?', (digest, int(time.time()))).fetchone() is not None
            except (KeyError, ValueError):
                return False

        def do_GET(self):
            path = urlsplit(self.path).path
            if path == '/api/state':
                if not self.authorized():
                    return self.send(401, {'error': 'Logga in med arbetsytans lösenord.'})
                return self.send(200, dict(store.read(), configured=provider.configured()))
            files = {'/': ('index.html', 'text/html; charset=utf-8'), '/app.js': ('app.js', 'text/javascript; charset=utf-8'), '/style.css': ('style.css', 'text/css; charset=utf-8')}
            if path not in files:
                return self.send(404, {'error': 'Sidan finns inte.'})
            name, kind = files[path]
            self.send(200, (STATIC / name).read_bytes(), kind)

        def do_POST(self):
            request_id = None
            try:
                origin = self.headers.get('Origin')
                if origin and urlsplit(origin).netloc != self.headers.get('Host'):
                    return self.send(403, {'error': 'Begäran kommer från fel webbplats.'})
                if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                    return self.send(415, {'error': 'JSON krävs.'})
                size = int(self.headers.get('Content-Length', '0'))
                if not 0 < size <= 20000:
                    return self.send(413, {'error': 'Begäran är för stor eller tom.'})
                data = json.loads(self.rfile.read(size))
                if not isinstance(data, dict):
                    raise Rejected('Ogiltig begäran.')
                path = urlsplit(self.path).path
                if path == '/api/login':
                    candidate = data.get('password')
                    if not isinstance(candidate, str) or not hmac.compare_digest(candidate.encode(), password.encode()):
                        return self.send(401, {'error': 'Fel lösenord.'})
                    token = secrets.token_urlsafe(32)
                    with store.connect() as db:
                        db.execute('DELETE FROM sessions WHERE expires<=?', (int(time.time()),))
                        db.execute('INSERT INTO sessions VALUES (?,?)', (hashlib.sha256(token.encode()).hexdigest(), int(time.time()) + 86400))
                    secure = '; Secure' if os.environ.get('COOKIE_SECURE') == '1' else ''
                    return self.send(200, {'ok': True}, cookie='session=' + token + '; HttpOnly; SameSite=Strict; Path=/; Max-Age=86400' + secure)
                if not self.authorized():
                    return self.send(401, {'error': 'Logga in med arbetsytans lösenord.'})
                if path not in ('/api/chat', '/api/undo'):
                    return self.send(404, {'error': 'Okänd åtgärd.'})
                message = 'Ångra senaste ändringen' if path == '/api/undo' else data.get('message')
                if not isinstance(message, str) or not 1 <= len(message.strip()) <= 4000:
                    raise Rejected('Skriv ett meddelande med högst 4 000 tecken.')
                candidate_id = data.get('requestId')
                base = store.reserve(candidate_id, data.get('version'), data.get('revision'))
                request_id = candidate_id
                proposal = None if path == '/api/undo' else provider.infer(base['model'], base['conversation'], message)
                state = store.commit(request_id, base, message, proposal, undo=path == '/api/undo')
                self.send(200, dict(state, configured=provider.configured()))
            except (Rejected, ValueError) as error:
                if request_id:
                    store.fail(request_id)
                text = str(error) if isinstance(error, Rejected) else 'Ogiltig JSON-begäran.'
                self.send(409 if isinstance(error, Conflict) else 422, {'error': text})
            except Exception:
                if request_id:
                    store.fail(request_id)
                self.send(500, {'error': 'Serverfel. Läs in aktuell modell innan du försöker igen.'})
    return Handler


def main():
    host = os.environ.get('HOST', '127.0.0.1')
    password = os.environ.get('APP_PASSWORD', '')
    if host not in ('127.0.0.1', 'localhost', '::1') and len(password) < 16:
        raise SystemExit('Extern åtkomst kräver APP_PASSWORD med minst 16 tecken.')
    store = Store(os.environ.get('DATABASE_PATH', 'data/studio.sqlite3'))
    server = ThreadingHTTPServer((host, int(os.environ.get('PORT', '8000'))), make_handler(store, password))
    print('Model Studio startad. AI konfigurerad:', provider.configured(), flush=True)
    server.serve_forever()


if __name__ == '__main__':
    main()
