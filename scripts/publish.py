#!/usr/bin/env python3
"""Publish to the existing Photoslava Nginx vhost. No backups or archives."""
import dataclasses, os, pathlib, re, shutil, subprocess, sys, tempfile
from build import ROOT, build

@dataclasses.dataclass
class Directive:
    start:int
    end:int
    words:list
    children:list

TOKEN=re.compile(r'\s+|\#[^\n]*|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|[{};]|[^\s{};#]+')

def parse(text):
    tokens=[m for m in TOKEN.finditer(text) if not m[0].isspace() and not m[0].startswith('#')]
    pos=0
    def block(nested=False):
        nonlocal pos
        items=[]
        while pos<len(tokens):
            if tokens[pos][0]=='}':
                if not nested: raise ValueError('Unexpected closing brace in nginx configuration')
                closing=tokens[pos].end();pos+=1;return items,closing
            start=tokens[pos].start();words=[]
            while pos<len(tokens) and tokens[pos][0] not in ('{',';','}'):
                words.append(tokens[pos][0].strip('\"\''));pos+=1
            if pos==len(tokens) or tokens[pos][0]=='}': raise ValueError('Incomplete nginx directive')
            delimiter=tokens[pos];pos+=1
            children=[]
            if delimiter[0]=='{': children,end=block(True)
            else:end=delimiter.end()
            items.append(Directive(start,end,words,children))
        if nested: raise ValueError('Unclosed nginx block')
        return items,len(text)
    return block()[0]

def plan(text):
    edits=[];roots=set();matched=0
    for server in parse(text):
        if server.words!=['server']:continue
        names=[x for d in server.children if d.words[:1]==['server_name'] for x in d.words[1:]]
        if 'photoslava.com' not in names and 'www.photoslava.com' not in names:continue
        if not set(names)<= {'photoslava.com','www.photoslava.com'}:
            raise ValueError('Photoslava shares a server block with another domain; automatic change refused')
        root=[d for d in server.children if d.words[:1]==['root']]
        if not root:
            if any(d.words[:1]==['return'] for d in server.children):continue
            raise ValueError('No explicit root in Photoslava server block. Show this vhost configuration to review it.')
        if len(root)!=1 or len(root[0].words)!=2:raise ValueError('Ambiguous document root')
        target=pathlib.Path(root[0].words[1])
        if target not in (pathlib.Path('/var/www/photoslava'),pathlib.Path('/var/www/photoslava/public')):
            raise ValueError('Unexpected Photoslava root: '+str(target))
        roots.add(target);matched+=1
        # Exact root locations or alternate wildcard route handlers require a review.
        locations=[d for d in server.children if d.words[:1]==['location']]
        if any(d.words[1:] in (['=','/'],['^~','/']) for d in locations):
            raise ValueError('Special root location found; automatic change refused')
        generic=[d for d in locations if d.words==['location','/']]
        if len(generic)>1:raise ValueError('Duplicate location /')
        replacement='location / {\n        try_files $uri/index.html $uri =404;\n    }'
        additions=[]
        if generic:edits.append((generic[0].start,generic[0].end,replacement))
        else:additions.append(replacement)
        indices=[d for d in server.children if d.words[:1]==['index']]
        if indices:
            for d in indices:edits.append((d.start,d.end,'index index.html;'))
        else:additions.append('index index.html;')
        if additions:edits.append((server.end-1,server.end-1,'\n    '+'\n    '.join(additions)+'\n'))
    if not matched or len(roots)!=1:raise ValueError('Expected one Photoslava document root in the enabled vhost')
    result=text
    for start,end,value in sorted(edits,reverse=True):result=result[:start]+value+result[end:]
    return result,next(iter(roots))

def atomic_write(path,data,mode=0o644):
    fd,name=tempfile.mkstemp(prefix='.photoslava-',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as f:f.write(data)
        os.chmod(name,mode);os.replace(name,path)
    finally:
        if os.path.exists(name):os.unlink(name)

def main():
    if os.geteuid()!=0:raise SystemExit('Run: sudo bash scripts/deploy.sh')
    conf=pathlib.Path('/etc/nginx/sites-enabled/photoslava.com').resolve(strict=True)
    if not conf.is_relative_to(pathlib.Path('/etc/nginx')):raise SystemExit('Unexpected nginx configuration path')
    old=conf.read_text();new,target=plan(old)
    if target.is_symlink():raise SystemExit('Document root is a symlink; review the target before deployment')
    subprocess.run(['nginx','-t'],check=True)
    dist=build()
    subprocess.run([sys.executable,str(ROOT/'scripts/check.py')],check=True)
    # nginx syntax is checked while old text is held in memory, never in a backup file.
    changed=(new!=old);mode=conf.stat().st_mode & 0o777
    if changed:
        atomic_write(conf,new.encode(),mode)
        try:subprocess.run(['nginx','-t'],check=True)
        except BaseException:
            atomic_write(conf,old.encode(),mode);raise
    try:
        target.mkdir(parents=True,exist_ok=True)
        # Do not remove unrelated files, certificates, old databases, or uploads.
        for src in sorted(dist.rglob('*')):
            if not src.is_file():continue
            dest=target/src.relative_to(dist)
            if dest.exists() and dest.is_dir():raise ValueError('File/directory collision: '+str(dest))
            dest.parent.mkdir(parents=True,exist_ok=True)
            if not dest.resolve().is_relative_to(target.resolve()):raise ValueError('Symlink escapes the document root')
            atomic_write(dest,src.read_bytes())
        subprocess.run(['systemctl','reload','nginx'],check=True)
    except BaseException:
        if changed:atomic_write(conf,old.encode(),mode)
        print('Deployment stopped. No content backup exists; inspect the error before retrying.',file=sys.stderr)
        raise
    print('Published to '+str(target)+'. No backups created. Check https://photoslava.com/')

if __name__=='__main__':main()
