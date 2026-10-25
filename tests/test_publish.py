import pathlib,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'scripts'))
from publish import plan

class NginxPlan(unittest.TestCase):
    sample='''# Existing certificate configuration
server { listen 80; server_name photoslava.com www.photoslava.com; return 301 https://photoslava.com$request_uri; }
server {
 listen 443 ssl;
 server_name photoslava.com www.photoslava.com;
 ssl_certificate /etc/letsencrypt/live/photoslava.com/fullchain.pem;
 root /var/www/photoslava/public;
 index index.php index.html;
 location / { try_files $uri $uri/ /index.php?$query_string; }
 location ~ \\.php$ { include fastcgi_params; fastcgi_pass unix:/run/php/php8.3-fpm.sock; }
}
server { server_name fateforce.ru; root /var/www/fateforce; location / { proxy_pass http://localhost:3000; } }
'''
    def test_preserves_tls_and_other_site(self):
        new,target=plan(self.sample)
        self.assertEqual(str(target),'/var/www/photoslava/public')
        self.assertIn('try_files $uri/index.html $uri =404;',new)
        self.assertIn('ssl_certificate /etc/letsencrypt/live/photoslava.com/fullchain.pem;',new)
        self.assertEqual(self.sample.split('server { server_name fateforce')[1],new.split('server { server_name fateforce')[1])
        self.assertEqual(plan(new)[0],new)
    def test_shared_domain_refused(self):
        with self.assertRaises(ValueError):plan(self.sample.replace('photoslava.com www.photoslava.com','photoslava.com another.com'))
    def test_unknown_root_refused(self):
        with self.assertRaises(ValueError):plan(self.sample.replace('/var/www/photoslava/public','/var/www/fateforce'))
    def test_special_route_refused(self):
        with self.assertRaises(ValueError):plan(self.sample.replace('location / {','location = / {',1))
    def test_braces_in_comments_and_quotes(self):
        new,_=plan(self.sample.replace('listen 443 ssl;','# ignore { }\n listen 443 ssl; add_header Example "value { x }";'))
        self.assertIn('"value { x }"',new)
    def test_absent_index_and_route(self):
        new,_=plan('server {server_name photoslava.com; root /var/www/photoslava;}')
        self.assertIn('index index.html;',new);self.assertIn('location /',new)

if __name__=='__main__':unittest.main()
