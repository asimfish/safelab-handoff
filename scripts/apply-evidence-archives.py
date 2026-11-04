"""Only modify checkout after every planned object has verified anonymous GET SHA."""
import pathlib,json,hashlib,re,posixpath,urllib.parse,urllib.request,subprocess,argparse
ap=argparse.ArgumentParser();ap.add_argument('plan',type=pathlib.Path);ap.add_argument('receipt',type=pathlib.Path);a=ap.parse_args();root=pathlib.Path.cwd();plan=json.loads(a.plan.read_text());receipt=json.loads(a.receipt.read_text());verified={x['path']:x for x in receipt['objects']};mapping={x['path']:x for x in plan['objects']}
for path,item in mapping.items():
 v=verified[path];assert v['public_get_verified'] and v['verified_sha256']==item['sha256'] and v['verified_bytes']==item['bytes'];assert hashlib.sha256((root/path).read_bytes()).hexdigest()==item['sha256'];raw=urllib.request.urlopen(item['url'],timeout=45).read();assert len(raw)==item['bytes'] and hashlib.sha256(raw).hexdigest()==item['sha256']
files=subprocess.check_output(['git','ls-files'],text=True).splitlines()
for name in files:
 p=root/name
 if name in mapping or not p.is_file() or p.suffix not in ['.html','.md','.js','.json','.txt']:continue
 # Frozen report JSON bytes and media assets stay untouched. Only living page/data links change.
 if p.suffix=='.json' and name!='data.json':continue
 s=p.read_text();before=s
 if p.suffix=='.html':
  def resolve(m):
   attribute,quote,url=m.group(1),m.group(2),m.group(3);u=urllib.parse.urlsplit(url)
   if u.scheme or u.netloc:return m.group(0)
   path=posixpath.normpath(posixpath.join(posixpath.dirname(name),u.path));item=mapping.get(path)
   return attribute+'='+quote+item['url']+('#'+u.fragment if u.fragment else '')+quote if item else m.group(0)
  s=re.sub(r'(href|src)=([\"\'])([^\"\']+)\2',resolve,s)
 for old,item in mapping.items():
  s=s.replace('https://asimfish.github.io/safelab-handoff/'+old,item['url'])
  s=s.replace(old,item['url'])
 if s!=before:p.write_text(s)
index={'schema_version':'safelab-evidence-archive-v1','policy':'Evidence over200000 bytes lives in TOS; data.json and same-origin frame logs exempt. No CORS dependency for ordinary download links.','objects':[{**i,'public_get_verified':True} for i in plan['objects']]};(root/'reports/archive-index.json').write_text(json.dumps(index,ensure_ascii=False,indent=2)+'\n')
for path in mapping:subprocess.run(['git','rm','--',path],check=True)
print('Removed verified repository copies only; remote originals unchanged',len(mapping))
