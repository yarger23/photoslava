#!/usr/bin/env python3
"""Deterministic static build. Python 3 standard library; no npm or PHP needed."""
import hashlib, html, json, pathlib, re, shutil
from urllib.parse import urlsplit

ROOT = pathlib.Path(__file__).resolve().parents[1]

def build():
    config = json.loads((ROOT / 'site.json').read_text())
    if not re.fullmatch(r'https://t\.me/[A-Za-z0-9_]+', config['telegram']):
        raise ValueError('telegram must be a public https://t.me/username link')
    if config['max']:
        parsed = urlsplit(config['max'])
        if parsed.scheme != 'https' or parsed.hostname not in {'max.ru', 'www.max.ru'}:
            raise ValueError('max must be an HTTPS profile link on max.ru')
    routes = json.loads((ROOT / 'source/routes.json').read_text())
    dist = ROOT / 'dist'
    if dist.exists(): shutil.rmtree(dist)
    shutil.copytree(ROOT / 'public', dist)
    hashes = {}
    for p in dist.rglob('*'):
        if p.is_file(): hashes['/' + p.relative_to(dist).as_posix()] = hashlib.sha256(p.read_bytes()).hexdigest()[:12]
    components = {p.stem.upper():p.read_text() for p in (ROOT / 'source/components').glob('*.html')}
    for route, filename in routes.items():
        text = (ROOT / 'source/pages' / filename).read_text()
        for key, value in components.items(): text = text.replace('{{' + key + '}}', value)
        text = text.replace('https://t.me/yarmach', html.escape(config['telegram'], quote=True))
        # A shared header starts without a selected page; decorate per output route.
        text = text.replace(' aria-current="page"', '')
        text = re.sub(r'(<a\b[^>]*href="' + re.escape(route) + r'")', r'\1 aria-current="page"', text)
        if config['max']:
            link = '<a class="max-contact" href="' + html.escape(config['max'], quote=True) + '">MAX ↗</a>'
            text = re.sub(r'(<a\b[^>]*href="' + re.escape(html.escape(config['telegram'], quote=True)) + r'"[^>]*>Telegram[^<]*</a>)', r'\1' + link, text)
        for path, digest in hashes.items(): text = text.replace('"' + path + '"', '"' + path + '?v=' + digest + '"')
        output = dist / route.lstrip('/') / 'index.html'
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text)
    (dist / 'robots.txt').write_text('User-agent: *\nAllow: /\nSitemap: ' + config['origin'] + '/sitemap.xml\n')
    urls = ''.join('<url><loc>' + html.escape(config['origin'] + path) + '</loc></url>' for path in routes)
    (dist / 'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + urls + '</urlset>')
    (dist / '404.html').write_text('<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Страница не найдена — Photoslava</title><link rel="stylesheet" href="/assets/css/base.css"><link rel="stylesheet" href="/assets/css/design.css"><main class="container section"><p class="eyebrow">Photoslava / 404</p><h1>Страница не найдена</h1><p>Вернёмся к фотографиям?</p><a class="button" href="/">На главную ↗</a></main></html>')
    print(f'Built {len(routes)} pages in {dist}')
    return dist

if __name__ == '__main__': build()
