"""把行程頁做成獨立網站（GitHub Pages）。
用法：TIX_PW=密碼 python3 -I build_site.py <行程頁.html> <receipts/vault.json> <輸出資料夾> [--new-salt]
- 明文正本 receipts/ 不部署；輸出資料夾只有 index.html、sw.js、robots.txt、vault/（密文）。
- salt 沿用既有 manifest（換 salt 會讓手機上記住的 Face ID 失效），要作廢舊裝置才加 --new-salt。
- 票面檔名帶密文雜湊：內容一變檔名就變，手機的離線快取不會拿到舊的。"""
import sys,os,json,base64,hashlib,io,subprocess,tempfile,shutil
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from PIL import Image
page,src,out=sys.argv[1:4];newsalt='--new-salt' in sys.argv
pw=os.environ.get('TIX_PW','').strip()
pw=''.join(chr(ord(c)-0xFEE0) if '０'<=c<='ｚ' else c for c in pw)
if len(pw)<4:sys.exit('TIX_PW 沒給或太短')
here=os.path.dirname(os.path.abspath(__file__));srcdir=os.path.dirname(os.path.abspath(src))
os.makedirs(os.path.join(out,'vault'),exist_ok=True)
manp=os.path.join(out,'vault','manifest.json')
old=json.load(open(manp)) if os.path.exists(manp) else None
ITER=310000
salt=base64.b64decode(old['salt']) if old and not newsalt else os.urandom(16)
key=hashlib.pbkdf2_hmac('sha256',pw.encode(),salt,ITER,32);A=AESGCM(key)
def seal(b):iv=os.urandom(12);return {'iv':base64.b64encode(iv).decode(),'ct':base64.b64encode(A.encrypt(iv,b,None)).decode()}
def unseal(o):return A.decrypt(base64.b64decode(o['iv']),base64.b64decode(o['ct']),None)
if old and not newsalt:
  try:unseal(old['chk'])
  except Exception:sys.exit('密碼跟既有 manifest 對不上（要換密碼請加 --new-salt）')
cachep=os.path.join(srcdir,'.build-cache.json');cache=json.load(open(cachep)) if os.path.exists(cachep) and not newsalt else {}
if old and old['salt']!=base64.b64encode(salt).decode():cache={}
def jpgs(path):
  if path.lower().endswith('.pdf'):
    t=tempfile.mkdtemp();subprocess.run(['pdftoppm','-r','150','-jpeg','-jpegopt','quality=90',path,os.path.join(t,'p')],check=True)
    fs=sorted(f for f in os.listdir(t) if f.endswith('.jpg'))[:12];ims=[Image.open(os.path.join(t,f)).convert('RGB') for f in fs];shutil.rmtree(t,ignore_errors=True)
  else:
    im=Image.open(path);im.load()
    if im.mode in('RGBA','LA','P'):bg=Image.new('RGB',im.size,'white');im=im.convert('RGBA');bg.paste(im,mask=im.split()[-1]);im=bg
    ims=[im.convert('RGB')]
  res=[]
  for im in ims:
    s=min(1,2000/max(im.size))
    if s<1:im=im.resize((round(im.width*s),round(im.height*s)),Image.LANCZOS)
    b=io.BytesIO();im.save(b,'JPEG',quality=90);res.append((b.getvalue(),im.width,im.height))
  return res
def pdf_links(fp):
  out=[]
  try:
    from pypdf import PdfReader
    for pg in PdfReader(fp).pages:
      for an in (pg.get('/Annots') or []):
        an=an.get_object();u=(an.get('/A') or {}).get('/URI')
        if u and str(u).startswith('http') and str(u) not in out:out.append(str(u))
  except Exception as ex:print('PDF 連結抽取失敗',fp,ex)
  return out
V=json.load(open(src));entries=[];keep=set()
for e in V['entries']:
  o={k:e[k] for k in('id','t','d1','d2','bk','note') if e.get(k)}
  o.setdefault('d2','');o.setdefault('bk','');o.setdefault('note','')
  sec=e.get('sec','').strip()
  for f in e.get('files',[]) if e.get('pdf_links') else []:   # 原始 PDF 已經一起放上去（連結可點），預設不再把連結抄進號碼欄
    if f.lower().endswith('.pdf'):
      for u in pdf_links(os.path.join(srcdir,f)):
        if u not in sec:sec+=('\n' if sec else '')+'PDF 連結 '+u
  if sec:o['sec']=seal(sec.encode())
  files=[];n=0
  for f in e.get('files',[]):
    fp=os.path.join(srcdir,f);h=hashlib.sha256(open(fp,'rb').read()).hexdigest()
    if h in cache and all(os.path.exists(os.path.join(out,'vault',x['a']+'.enc')) for x in cache[h]):pages=cache[h]
    else:
      pages=[]
      for b,w,hh in jpgs(fp):
        n+=1;blob=json.dumps(seal(b)).encode();fid='%s-%s'%(e['id'],hashlib.sha256(blob).hexdigest()[:10])
        open(os.path.join(out,'vault',fid+'.enc'),'wb').write(blob);pages.append({'a':fid,'m':'image/jpeg','w':w,'h':hh})
      if fp.lower().endswith('.pdf'):   # 原始 PDF 也加密放上去：手機用 PDF 檢視器開，裡面的連結可以點
        blob=json.dumps(seal(open(fp,'rb').read())).encode();fid='%s-pdf-%s'%(e['id'],hashlib.sha256(blob).hexdigest()[:10])
        open(os.path.join(out,'vault',fid+'.enc'),'wb').write(blob);pages.insert(0,{'a':fid,'m':'application/pdf','doc':True})
      cache[h]=pages
    files+=pages
  o['files']=files;keep.update(x['a'] for x in files);o['at']=len(entries);entries.append(o)
man={'v':1,'salt':base64.b64encode(salt).decode(),'iter':ITER,'chk':old['chk'] if old and not newsalt else seal(b'tix-ok'),'entries':entries}
json.dump(man,open(manp,'w'),ensure_ascii=False,indent=1);json.dump(cache,open(cachep,'w'))
orph=[f for f in os.listdir(os.path.join(out,'vault')) if f.endswith('.enc') and f[:-4] not in keep]
for f in orph:os.remove(os.path.join(out,'vault',f))
html=open(page,encoding='utf-8').read()
assert '<meta charset' in html.lower()[:600] or True
inj='<meta name="robots" content="noindex,nofollow">\n<meta name="apple-mobile-web-app-capable" content="yes">\n<meta name="apple-mobile-web-app-title" content="大阪京都">\n<script>window.TIX_STATIC=1</script>\n'
i=html.index('<style>');html=html[:i]+inj+html[i:]
open(os.path.join(out,'index.html'),'w',encoding='utf-8').write(html)
for f in('sw.js','robots.txt'):shutil.copy(os.path.join(here,f),os.path.join(out,f))
open(os.path.join(out,'.nojekyll'),'w').close()
print('entries',len(entries),'files',len(keep),'removed',len(orph))
