"""Servidor de teste que imita o mínimo do Supabase (login e duas tabelas) para testar a sincronização sem internet.
Uso: from mock_supabase import start; srv, state = start()  ->  srv.url
"""
import json, threading, uuid, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs


class State:
    def __init__(self):
        self.users = {}      # email -> {id, password}
        self.tokens = {}     # access_token -> user id
        self.refresh = {}    # refresh_token -> user id
        self.dados = {}      # user id -> {user_id, conteudo, versao, atualizado_em}
        self.backups = []    # {id, user_id, criado_em, motivo, conteudo}
        self.seq = 0
        self.lock = threading.Lock()

    def sessao(self, uid, email):
        a, r = 'acc-' + uuid.uuid4().hex, 'ref-' + uuid.uuid4().hex
        self.tokens[a] = uid
        self.refresh[r] = uid
        return {'access_token': a, 'refresh_token': r, 'expires_in': 3600, 'user': {'id': uid, 'email': email}}


def _filtra(rows, q):
    for campo, val in q.items():
        if campo in ('select', 'order', 'limit', 'offset'):
            continue
        v = val[0]
        if v.startswith('eq.'):
            alvo = v[3:]
            rows = [r for r in rows if str(r.get(campo)) == alvo]
        elif v.startswith('in.('):
            alvo = v[4:-1].split(',')
            rows = [r for r in rows if str(r.get(campo)) in alvo]
    return rows


def _proj(rows, q):
    sel = q.get('select', ['*'])[0]
    if sel == '*':
        return rows
    cols = [c.strip() for c in sel.split(',')]
    return [{c: r.get(c) for c in cols} for r in rows]


def make_handler(state):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _cors(self):
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Headers', 'apikey, authorization, content-type, prefer')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, PATCH, DELETE, OPTIONS')

        def _json(self, code, obj):
            body = b'' if code == 204 else json.dumps(obj).encode()
            self.send_response(code)
            self._cors()
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _body(self):
            n = int(self.headers.get('Content-Length') or 0)
            return json.loads(self.rfile.read(n) or b'null') if n else None

        def _uid(self):
            h = self.headers.get('Authorization', '')
            return state.tokens.get(h.replace('Bearer ', ''))

        def do_OPTIONS(self):
            self.send_response(204)
            self._cors()
            self.end_headers()

        def _rota(self, met):
            u = urlparse(self.path)
            q = parse_qs(u.query)
            body = self._body() if met in ('POST', 'PATCH') else None
            with state.lock:
                if u.path == '/auth/v1/signup' and met == 'POST':
                    if body['email'] in state.users:
                        return self._json(422, {'msg': 'User already registered'})
                    if len(body['password']) < 6:
                        return self._json(422, {'msg': 'Password should be at least 6 characters.'})
                    uid = str(uuid.uuid4())
                    state.users[body['email']] = {'id': uid, 'password': body['password']}
                    return self._json(200, state.sessao(uid, body['email']))
                if u.path == '/auth/v1/token' and met == 'POST':
                    g = q.get('grant_type', [''])[0]
                    if g == 'password':
                        us = state.users.get(body['email'])
                        if not us or us['password'] != body['password']:
                            return self._json(400, {'error_description': 'Invalid login credentials'})
                        return self._json(200, state.sessao(us['id'], body['email']))
                    if g == 'refresh_token':
                        uid = state.refresh.get(body['refresh_token'])
                        if not uid:
                            return self._json(400, {'error_description': 'Invalid Refresh Token'})
                        email = [e for e, x in state.users.items() if x['id'] == uid][0]
                        return self._json(200, state.sessao(uid, email))
                uid = self._uid()
                if not uid:
                    return self._json(401, {'message': 'JWT inválido'})
                if u.path == '/rest/v1/ljwa_dados':
                    mine = [r for r in state.dados.values() if r['user_id'] == uid]
                    if met == 'GET':
                        return self._json(200, _proj(_filtra(mine, q), q))
                    if met == 'POST':
                        if uid in state.dados:
                            return self._json(409, {'message': 'duplicate key'})
                        row = {'user_id': uid, 'conteudo': body['conteudo'], 'versao': body.get('versao', 1), 'atualizado_em': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
                        state.dados[uid] = row
                        return self._json(201, [row])
                    if met == 'PATCH':
                        alvo = _filtra(mine, q)
                        for r in alvo:
                            r.update({k: body[k] for k in body if k in ('conteudo', 'versao', 'atualizado_em')})
                        return self._json(200, alvo)
                if u.path == '/rest/v1/ljwa_backups':
                    mine = [r for r in state.backups if r['user_id'] == uid]
                    if met == 'GET':
                        mine = sorted(mine, key=lambda r: r['id'], reverse=True)
                        mine = _filtra(mine, q)
                        off = int(q.get('offset', ['0'])[0])
                        lim = int(q.get('limit', ['1000'])[0])
                        return self._json(200, _proj(mine[off:off + lim], q))
                    if met == 'POST':
                        state.seq += 1
                        state.backups.append({'id': state.seq, 'user_id': uid, 'criado_em': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'motivo': body.get('motivo'), 'conteudo': body['conteudo']})
                        return self._json(201, None)
                    if met == 'DELETE':
                        ids = {r['id'] for r in _filtra(mine, q)}
                        state.backups[:] = [r for r in state.backups if r['id'] not in ids]
                        return self._json(204, None)
            return self._json(404, {'message': 'rota não encontrada: ' + u.path})

        def do_GET(self): self._rota('GET')
        def do_POST(self): self._rota('POST')
        def do_PATCH(self): self._rota('PATCH')
        def do_DELETE(self): self._rota('DELETE')
    return H


def start():
    state = State()
    srv = ThreadingHTTPServer(('127.0.0.1', 0), make_handler(state))
    srv.url = 'http://127.0.0.1:%d' % srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, state
