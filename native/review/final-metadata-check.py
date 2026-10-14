from pathlib import Path
import json,statistics,threading,urllib.parse
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from playwright.sync_api import sync_playwright
apps={'anatomy-of-a-business':('Anatomy of a Business','🧩','anatomy-ready'),'Diagnosing-Dollars':('Diagnosing Dollars','🩺','diagnosing-ready'),'filing-day-decisions':('Filing Day Decisions','📑','filing-ready'),'closing-time':('Closing Time','🕔','closing-ready')}
requests=[]
class Handler(SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
 def do_GET(self):
  path=urllib.parse.urlsplit(self.path).path;parts=path.split('/');repo=parts[1] if len(parts)>1 else ''
  requests.append(path)
  if repo in apps and len(parts)>=4 and parts[2]=='js':
   self.directory=str(Path('/workspace')/repo/'native/dist');self.path='/'+'/'.join(parts[3:]);super().do_GET()
  elif path=='/favicon.ico':self.send_response(204);self.end_headers()
  else:self.send_error(404)
server=ThreadingHTTPServer(('127.0.0.1',0),Handler);threading.Thread(target=server.serve_forever,daemon=True).start();origin='http://127.0.0.1:'+str(server.server_port)
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,proxy={'server':'http://127.0.0.1:9','bypass':'127.0.0.1,localhost'})
 for repo,(title,icon,mark) in apps.items():
  errors=[];external=[];samples=[]
  for _ in range(5):
   c=b.new_context();c.route('**/*',lambda r:r.continue_() if r.request.url.startswith(origin) else (external.append(r.request.url),r.abort())[-1]);page=c.new_page()
   page.on('pageerror',lambda e:errors.append(str(e)));page.on('console',lambda m:errors.append(m.text) if m.type=='error' else None)
   session=c.new_cdp_session(page);session.send('Network.enable');session.send('Network.setCacheDisabled',{'cacheDisabled':True})
   page.goto(origin+'/'+repo+'/js/',wait_until='networkidle');page.wait_for_function("document.documentElement.dataset.ready==='true'&&document.documentElement.dataset.saving==='false'")
   assert page.title()==title
   href=page.locator('link[rel=icon]').get_attribute('href');assert href.startswith('data:image/svg+xml,') and icon in urllib.parse.unquote(href)
   assert page.evaluate('url=>new Promise(resolve=>{const i=new Image();i.onload=()=>resolve(true);i.onerror=()=>resolve(false);i.src=url;})',href)
   samples.append(page.evaluate('name=>performance.getEntriesByName(name)[0].startTime',mark));c.close()
  assert not errors and not external,(repo,errors,external)
  n=Path('/workspace')/repo/'native';before=json.loads((n/'test-results/pre-icon-manifest.json').read_text());after=json.loads((n/'dist/manifest.json').read_text())
  changed=[name for name in before['files'] if before['files'][name]['sha256']!=after['files'][name]['sha256']];assert changed==['index.html'],changed
  evidence={'app':title,'title':title,'icon':icon,'svg_data_icon_decoded':True,'changed_runtime_assets':changed,'asset_bytes':after['asset_bytes'],'cold_initialization_ms':{'samples':samples,'median':statistics.median(samples),'conditions':'Final icon-inclusive bundle; five cache-disabled fresh Chromium contexts on local loopback; no hosted/network speed or classroom capacity claim.'},'page_console_errors':errors,'external_requests':external,'runtime_python_wasm_requests':[x for x in requests if '/'+repo+'/' in x and (x.endswith(('.py','.whl','.wasm')) or '/vendor/' in x)]}
  assert evidence['runtime_python_wasm_requests']==[]
  (n/'test-results/final-metadata.json').write_text(json.dumps(evidence,indent=2)+'\n')
  result_path=n/'test-results/browser-results.json';result=json.loads(result_path.read_text());assert all(x['status']=='passed' for x in result['checks']);result['checks'].append({'name':'Final title, original embedded tab icon and metadata-only runtime change; five fresh contexts','status':'passed'});result['cold_initialization_ms']=evidence['cold_initialization_ms'];result_path.write_text(json.dumps(result,indent=2)+'\n')
  print(repo,'PASS',after['asset_bytes'],'bytes; median',statistics.median(samples),flush=True)
 b.close()
server.shutdown()
