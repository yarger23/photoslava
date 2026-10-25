#!/usr/bin/env python3
"""Local preview preserving the production URLs without a trailing slash."""
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, unquote
import os
from build import build
ROOT=build()
class Handler(SimpleHTTPRequestHandler):
    def translate_path(self,path):
        clean=unquote(urlsplit(path).path).lstrip('/')
        p=(ROOT/clean).resolve()
        if not p.is_relative_to(ROOT): return str(ROOT/'__missing__')
        if p.is_dir(): return str(p/'index.html')
        return str(p)
    def end_headers(self):
        self.send_header('Cache-Control','no-store');super().end_headers()
os.chdir(ROOT)
ThreadingHTTPServer(('0.0.0.0',8765),Handler).serve_forever()
