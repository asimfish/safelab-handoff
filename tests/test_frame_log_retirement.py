"""Prove retention, byte identity and archive guards before derived-copy retirement."""
import contextlib,datetime,gzip,hashlib,importlib.util,io,json,pathlib,sys,tempfile,unittest
REPO=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('retire_frame_log_compat',REPO/'scripts/retire-frame-log-compat.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
def sha(b):return hashlib.sha256(b).hexdigest()
class Retirement(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(dir=REPO.parent);self.base=pathlib.Path(self.tmp.name);self.root=self.base/'repo';self.archive=self.base/'archive';self.root.mkdir();self.archive.mkdir();self.original_root=module.ROOT;self.original_archive_root=module.ARCHIVE_ROOT;module.ROOT=self.root;module.ARCHIVE_ROOT=self.base;self.old_argv=sys.argv[:]
  self.rel='media/frame_logs/3/run/case.json';self.new=self.rel+'.gz';self.raw=b'{"schema_version":"safelab-frame-log-v1","case_id":"case","rows":[]}\n';self.wire=gzip.compress(self.raw,mtime=0)
  for base,name,b in [(self.root,self.rel,self.raw),(self.root,self.new,self.wire),(self.archive,self.rel,self.raw)]:p=base/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
  old={'url':'https://asimfish.github.io/safelab-handoff/'+self.rel,'sha256':sha(self.raw),'bytes':len(self.raw)};new={'url':'https://asimfish.github.io/safelab-handoff/'+self.new,'sha256':sha(self.wire),'bytes':len(self.wire),'encoding':'gzip','decoded_sha256':sha(self.raw),'decoded_bytes':len(self.raw)}
  self.manifest=self.root/'media/manifests/3/run.json';self.manifest.parent.mkdir(parents=True);self.manifest.write_text(json.dumps({'cases':[{'case_id':'case','frame_log':new,'frame_log_previous':old}]}));(self.root/'media/index.json').write_text(json.dumps({'manifests':[{'url':'https://asimfish.github.io/safelab-handoff/media/manifests/3/run.json','sha256':sha(self.manifest.read_bytes())}]}))
  led=self.root/'media/migrations/frame-log-test.json';led.parent.mkdir(parents=True);led.write_text(json.dumps({'logs':[{'path':self.rel,'gzip_path':self.new,'original_sha256':sha(self.raw),'original_bytes':len(self.raw),'gzip_sha256':sha(self.wire),'case_ids':['case']}]}));self.receipt=self.base/'receipt.json';self.proof={'online':True,'release':'test','verified':1,'verified_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'verification':[{'path':self.new,'decoded_sha256':sha(self.raw),'old_url_retained':True,'content_encoding':None}]};self.save_receipt()
  sys.argv=['retire','--release','test','--receipt',str(self.receipt),'--archive',str(self.archive),'--publication-commit','a'*40,'--apply']
 def tearDown(self):module.ROOT=self.original_root;module.ARCHIVE_ROOT=self.original_archive_root;sys.argv=self.old_argv;self.tmp.cleanup()
 def save_receipt(self):self.receipt.write_text(json.dumps(self.proof))
 def mature(self):self.proof['verified_at']=(datetime.datetime.now(datetime.timezone.utc)-datetime.timedelta(seconds=601)).isoformat();self.save_receipt()
 def test_early_retirement_refused_without_any_change(self):
  before=self.manifest.read_bytes()
  with self.assertRaisesRegex(SystemExit,'window has not elapsed'):module.main()
  self.assertEqual(self.manifest.read_bytes(),before);self.assertEqual((self.root/self.rel).read_bytes(),self.raw)
 def test_mature_retirement_preserves_canonical_and_archive_and_rejects_replay(self):
  self.mature()
  with contextlib.redirect_stdout(io.StringIO()):module.main()
  self.assertFalse((self.root/self.rel).exists());self.assertEqual((self.root/self.new).read_bytes(),self.wire);self.assertEqual((self.archive/self.rel).read_bytes(),self.raw);self.assertNotIn('frame_log_previous',json.loads(self.manifest.read_text())['cases'][0])
  with self.assertRaisesRegex(SystemExit,'already recorded'):module.main()
 def test_archive_mismatch_prevents_retirement(self):
  self.mature();(self.archive/self.rel).write_bytes(b'not the source')
  with self.assertRaisesRegex(SystemExit,'archive mismatch'):module.main()
  self.assertEqual((self.root/self.rel).read_bytes(),self.raw)
 def test_symlinked_parent_prevents_retirement(self):
  self.mature();p=(self.root/self.rel).parent;replacement=p.with_name('target');p.rename(replacement);p.symlink_to(replacement,target_is_directory=True)
  with self.assertRaisesRegex(SystemExit,'escapes repository'):module.main()
  self.assertEqual((replacement/'case.json').read_bytes(),self.raw)
if __name__=='__main__':unittest.main()
