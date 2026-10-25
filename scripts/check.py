#!/usr/bin/env python3
"""Validate every page, asset, internal link, anchor and contact destination."""
import json,pathlib,sys
from html.parser import HTMLParser
from urllib.parse import urlsplit,unquote
ROOT=pathlib.Path(__file__).resolve().parents[1];DIST=ROOT/'dist'
class Page(HTMLParser):
    def __init__(self,text):
        super().__init__(convert_charrefs=True);self.ids=[];self.refs=[];self.h1=0;self.forms=[];self.canonical=[];self.feed(text)
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if 'id' in a:self.ids.append(a['id'])
        if tag=='h1':self.h1+=1
        if tag=='form':self.forms.append(a)
        if tag=='link' and a.get('rel')=='canonical':self.canonical.append(a.get('href'))
        for key in ('src','href'):
            if key in a:self.refs.append((tag,a[key]))

def check():
    routes=json.loads((ROOT/'source/routes.json').read_text());pages={};errors=[]
    for route in routes:
        file=DIST/route.lstrip('/')/'index.html'
        if not file.exists():errors.append('Missing page '+route);continue
        text=file.read_text();p=Page(text);pages[route]=p
        if p.h1!=1:errors.append(route+': expected exactly one h1')
        if len(p.ids)!=len(set(p.ids)):errors.append(route+': duplicate ids')
        if '{{' in text:errors.append(route+': unresolved template')
        if 'csrf' in text or 'wa.me' in text or 'WhatsApp' in text:errors.append(route+': stale form or messenger')
        if p.canonical!=['https://photoslava.com'+route]:errors.append(route+': incorrect canonical')
        for form in p.forms:
            if not form.get('action','').startswith('https://t.me/'):errors.append(route+': unexpected form destination')
    for route,p in pages.items():
        for tag,ref in p.refs:
            u=urlsplit(ref)
            if u.scheme or u.netloc:continue
            path=unquote(u.path) or route
            if path in pages:
                if u.fragment and unquote(u.fragment) not in pages[path].ids:errors.append(route+': broken anchor '+ref)
            else:
                asset=DIST/path.lstrip('/')
                if not asset.is_file() or not asset.stat().st_size:errors.append(route+': missing asset/link '+ref)
    if errors:raise AssertionError('\n'.join(errors))
    print(f'PASS: {len(pages)} pages; internal links, anchors, assets, forms, canonical URLs')
if __name__=='__main__':check()
