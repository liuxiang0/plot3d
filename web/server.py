#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""server.py — plot3d 手机版 Web 服务（零额外框架依赖）

启动:  .venv/numina/bin/python plot3d/web/server.py [--port 8030]
手机访问: 与本机同一 WiFi 下打开  http://<电脑IP>:8030
桌面 Tkinter 程序（main_app.py）不受影响，两者并行。

API:
  GET /                → 前端页面
  GET /static/<file>   → 静态资源（three.js 已离线打包）
  GET /thumbs/<key>.png→ 条目缩略图
  GET /api/library     → 全部条目（含资料卡）
  GET /api/geometry?key=<key> → 采样几何（服务端缓存）
"""
import ast
import json
import mimetypes
import os
import socket
import sys
import threading
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

HERE = os.path.dirname(os.path.abspath(__file__))
P3D = os.path.dirname(HERE)                       # plot3d/
sys.path.insert(0, P3D)
sys.path.insert(0, HERE)

import curve_library                               # noqa: E402
import geometry                                    # noqa: E402

PORT = 8030
THUMB_DIR = os.path.join(P3D, 'thumbs')

# ---------------- 资料卡: 不 import gallery（依赖 tkinter），AST 提取 CARDS ----

def _load_cards():
    src = open(os.path.join(P3D, 'gallery.py'), encoding='utf-8').read()
    tree = ast.parse(src)
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == 'CARDS':
                    return ast.literal_eval(node.value)
    return {}

CARDS = _load_cards()

# ---------------- 库清单 + 几何缓存 ----------------

_grouped, _warns = curve_library.load_all()
LIBRARY = []
for _cat, items in _grouped:
    for e in items:
        c = CARDS.get(e['key'], {})
        LIBRARY.append({
            'key': e['key'], 'name': e['name'], 'category': e['category'],
            'expr': e['expr'], 'desc': e.get('desc', ''),
            'formula': c.get('formula', ''), 'props': c.get('props', []),
            'trivia': c.get('trivia', ''), 'user': e.get('user', False),
        })

_cache, _cache_lock = {}, threading.Lock()
_expr_cache = {}                                   # 自定义表达式缓存 (最多 64)


def get_geometry(key=None, expr=None):
    if expr is not None:
        expr = expr.strip()
        if not expr or len(expr) > 800:
            raise ValueError('表达式为空或过长')
        with _cache_lock:
            if expr in _expr_cache:
                return _expr_cache[expr]
        geo = geometry.sample(expr)                # 失败抛异常给上层转 422
        with _cache_lock:
            _expr_cache[expr] = geo
            if len(_expr_cache) > 64:
                _expr_cache.pop(next(iter(_expr_cache)))
        return geo
    with _cache_lock:
        if key in _cache:
            return _cache[key]
    entry = next((e for e in LIBRARY if e['key'] == key), None)
    if entry is None:
        return None
    faces = curve_library.BUILTIN.get(key, {}).get('faces')
    geo = geometry.sample(entry['expr'], entry['category'], faces=faces)
    with _cache_lock:
        _cache[key] = geo
    return geo


# ---------------- HTTP ----------------

class Handler(BaseHTTPRequestHandler):
    server_version = 'plot3d-web/1.0'

    def log_message(self, fmt, *args):                 # 安静: 只记错误
        if str(args[1]).startswith(('4', '5')):
            BaseHTTPRequestHandler.log_message(self, fmt, *args)

    # ---- 工具 ----
    def _send(self, code, body, ctype, extra=None):
        data = body if isinstance(body, bytes) else body.encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-cache')
        if extra:
            for k, v in extra.items():
                self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def _json(self, obj, code=200):
        self._send(code, json.dumps(obj, ensure_ascii=False),
                   'application/json; charset=utf-8')

    def _file(self, path, fallback_ctype='application/octet-stream'):
        if not os.path.isfile(path):
            self._json({'error': 'not found'}, 404)
            return
        ctype = mimetypes.guess_type(path)[0] or fallback_ctype
        with open(path, 'rb') as f:
            self._send(200, f.read(), ctype)

    # ---- 路由 ----
    def do_GET(self):
        u = urlparse(self.path)
        path = u.path
        try:
            if path in ('/', '/index.html'):
                self._file(os.path.join(HERE, 'static', 'index.html'),
                           'text/html; charset=utf-8')
            elif path.startswith('/static/'):
                safe = os.path.normpath(path[len('/static/'):])
                if safe.startswith('..'):
                    self._json({'error': 'forbidden'}, 403)
                    return
                self._file(os.path.join(HERE, 'static', safe))
            elif path.startswith('/thumbs/'):
                name = os.path.basename(path)
                self._file(os.path.join(THUMB_DIR, name), 'image/png')
            elif path == '/api/library':
                self._json({'entries': LIBRARY})
            elif path == '/api/geometry':
                q = parse_qs(u.query)
                key = q.get('key', [''])[0]
                expr = q.get('expr', [''])[0]
                try:
                    geo = get_geometry(key=key or None, expr=expr or None)
                except Exception as ex:
                    self._json({'error': str(ex)}, 422)
                    return
                if geo is None:
                    self._json({'error': 'unknown key'}, 404)
                else:
                    self._json(geo)
            else:
                self._json({'error': 'not found'}, 404)
        except Exception as ex:                        # 兜底
            try:
                self._json({'error': f'internal: {ex}'}, 500)
            except Exception:
                pass


def lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return '127.0.0.1'


def main():
    global PORT
    if '--port' in sys.argv:
        PORT = int(sys.argv[sys.argv.index('--port') + 1])
    srv = ThreadingHTTPServer(('0.0.0.0', PORT), Handler)
    ip = lan_ip()
    print(f'plot3d 手机版已启动:')
    print(f'  本机:   http://127.0.0.1:{PORT}')
    print(f'  手机:   http://{ip}:{PORT}  (同一 WiFi)')
    print(f'  条目:   {len(LIBRARY)} 条 · 资料卡 {len(CARDS)} 张')
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print('\n已停止')


if __name__ == '__main__':
    main()
