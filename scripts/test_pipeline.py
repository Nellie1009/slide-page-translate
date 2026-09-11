import unittest, tempfile, subprocess, json, sys
from pathlib import Path
from reportlab.pdfgen import canvas
from pypdf import PdfReader
SCRIPT=Path(__file__).with_name('slide_translate.py')
class PipelineTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.src=self.root/'source.pdf';self.work=self.root/'job'
  c=canvas.Canvas(str(self.src),pagesize=(720,540))
  for n in range(3):
   c.drawString(30,480,f'Page content {n+1}: Dose = 0.5 mg.');c.drawString(680,20,'22');c.showPage()
  c.save()
 def tearDown(self):self.tmp.cleanup()
 def run_cli(self,*args,ok=True):
  self.assertTrue(SCRIPT.exists(),'Missing executable pipeline: fixed-path exporter cannot prepare generic input')
  p=subprocess.run([sys.executable,str(SCRIPT),*map(str,args)],capture_output=True,text=True)
  if ok:self.assertEqual(p.returncode,0,p.stdout+p.stderr)
  else:self.assertNotEqual(p.returncode,0,p.stdout+p.stderr)
  return p
 def prepare(self):
  self.run_cli('prepare',self.src,'--work',self.work)
  return json.loads((self.work/'manifest.json').read_text())
 def fill(self,long=False):
  for req in sorted((self.work/'requests').glob('*.json')):
   q=json.loads(req.read_text());a={'document_id':q['document_id'],'chunk_id':q['chunk_id'],'visual_review':'reviewed','figure_notes':[], 'items':[{'id':b['id'],'zh':('中文长段落，需要自动续页。'*450 if long else '中文译文：剂量 0.5 mg。'),'status':'translated'} for b in q['items']]}
   (self.work/'responses'/req.name).write_text(json.dumps(a,ensure_ascii=False))
 def test_prepare_ids_and_duplicate_footer(self):
  m=self.prepare();self.assertEqual(len(m['pages']),3);self.assertEqual([p['page'] for p in m['pages']],[1,2,3]);self.assertEqual([p['printed_label'] for p in m['pages']],['22']*3)
  ids=[i['id'] for p in m['pages'] for i in p['items']];self.assertEqual(len(ids),len(set(ids)))
 def test_missing_page_rejected(self):
  self.prepare();self.fill();next((self.work/'responses').glob('*.json')).unlink()
  r=self.run_cli('build','--work',self.work,'--output',self.root/'out.pdf',ok=False);self.assertIn('Missing',r.stderr);self.assertFalse((self.root/'out.pdf').exists())
 def test_wrong_document_rejected(self):
  self.prepare();self.fill();f=next((self.work/'responses').glob('*.json'));d=json.loads(f.read_text());d['document_id']='wrong';f.write_text(json.dumps(d))
  self.assertIn('document_id',self.run_cli('build','--work',self.work,'--output',self.root/'out.pdf',ok=False).stderr)
 def test_continuation_preserves_source_page_order(self):
  self.prepare();self.fill(long=True);out=self.root/'out.pdf';self.run_cli('build','--work',self.work,'--output',out)
  p=PdfReader(out);self.assertGreater(len(p.pages),3)
  report=json.loads((self.work/'build-report.json').read_text());self.assertEqual(sorted(set(r['source_page'] for r in report['pages'])),[1,2,3]);self.assertEqual([r['source_page'] for r in report['pages']],sorted(r['source_page'] for r in report['pages']))
  self.assertTrue(all('中文' in page.extract_text() for page in p.pages))
 def test_unreviewed_image_must_be_disclosed(self):
  self.prepare();self.fill();f=next((self.work/'responses').glob('*.json'));d=json.loads(f.read_text());d['visual_review']='unavailable';f.write_text(json.dumps(d))
  self.run_cli('build','--work',self.work,'--output',self.root/'out.pdf',ok=False)
  self.run_cli('build','--work',self.work,'--output',self.root/'out.pdf','--allow-unreviewed-images')
  self.assertIn('未经图像核对',PdfReader(self.root/'out.pdf').pages[0].extract_text())
 def test_duplicate_translation_id_rejected(self):
  self.prepare();self.fill();f=next((self.work/'responses').glob('*.json'));d=json.loads(f.read_text());d['items'].append(d['items'][0]);f.write_text(json.dumps(d))
  self.assertIn('duplicate',self.run_cli('validate','--work',self.work,ok=False).stderr)
 def test_modified_source_rejected(self):
  self.prepare();self.fill()
  with (self.work/'original.pdf').open('ab') as f:f.write(b'\n% changed source\n')
  self.assertIn('checksum',self.run_cli('validate','--work',self.work,ok=False).stderr)
 def test_images_natural_order_and_no_text_not_skipped(self):
  from PIL import Image
  folder=self.root/'images';folder.mkdir()
  Image.new('RGB',(100,50),'red').save(folder/'slide10.png');Image.new('RGB',(100,50),'blue').save(folder/'slide2.png')
  self.run_cli('prepare',folder,'--work',self.work)
  m=json.loads((self.work/'manifest.json').read_text());self.assertEqual(len(m['pages']),2);self.assertEqual(len(m['chunks']),2)
  from PIL import Image as Img
  pixel=Img.open(self.work/m['pages'][0]['image']).getpixel((30,30));self.assertGreater(pixel[2],pixel[0])
  self.fill();self.assertIn('image-only',self.run_cli('validate','--work',self.work,ok=False).stderr)
  for f in (self.work/'responses').glob('*.json'):
   d=json.loads(f.read_text());d['figure_notes']=[{'source':'原图','zh':'本页仅有纯色图像，无可译文字。','status':'translated'}];f.write_text(json.dumps(d))
  self.run_cli('build','--work',self.work,'--output',self.root/'images.pdf')
  self.assertEqual(len(PdfReader(self.root/'images.pdf').pages),2)
 def test_external_pdf_adapter_for_unknown_format(self):
  other=self.root/'slides.key';other.write_bytes(b'fixture')
  self.run_cli('prepare',other,'--normalized-pdf',self.src,'--work',self.work)
  self.assertEqual(len(json.loads((self.work/'manifest.json').read_text())['pages']),3)
 def test_reject_output_non_pdf(self):
  self.prepare();self.fill();self.run_cli('build','--work',self.work,'--output',self.root/'out.html',ok=False)
  self.assertFalse((self.root/'out.html').exists())
 def test_partial_validation_accepts_finished_chunk_without_hiding_bad_ids(self):
  self.prepare();self.fill()
  files=sorted((self.work/'responses').glob('*.json'))
  for f in files[1:]:f.unlink()
  r=self.run_cli('validate','--work',self.work,'--partial');self.assertIn('remaining',r.stdout)
  d=json.loads(files[0].read_text());d['items'][0]['id']='wrong';files[0].write_text(json.dumps(d))
  self.assertIn('unknown',self.run_cli('validate','--work',self.work,'--partial',ok=False).stderr)
 def test_hierarchy_and_heading_kept_with_body(self):
  import slide_translate as pipeline
  pipeline.choose_font(None, '标题正文图注•')
  entries=[{'zh':t,'role':r,'status':'translated'} for t,r in [('标题','title'),('标题','heading'),('正文','body'),('正文','bullet'),('图注','caption'),('图注','footnote')]]
  paras=pipeline.page_paragraphs({}, {'items':entries,'notes':[],'unreviewed':False})
  self.assertGreater(paras[0].style.fontSize,paras[1].style.fontSize)
  self.assertGreater(paras[1].style.fontSize,paras[2].style.fontSize)
  self.assertGreater(paras[2].style.fontSize,paras[4].style.fontSize)
  self.assertGreater(paras[3].style.leftIndent,0)
  pages=pipeline.paginate([paras[2],paras[1],paras[2]],432,75)
  self.assertEqual(len(pages[0]),1, 'Heading must move with following body')
  self.assertEqual(len(pages[1]),2)
 def test_invalid_role_rejected(self):
  self.prepare();self.fill();f=next((self.work/'responses').glob('*.json'));d=json.loads(f.read_text());d['items'][0]['role']='invented';f.write_text(json.dumps(d))
  self.assertIn('role',self.run_cli('validate','--work',self.work,ok=False).stderr)
 def test_table_export_repeats_header_and_preserves_rows(self):
  self.prepare();self.fill()
  for f in (self.work/'responses').glob('*.json'):
   d=json.loads(f.read_text());first=d['items'][0]
   first.update(role='table',rows=[['项目','数值']]+[[f'指标{n}',f'{n} mg'] for n in range(70)],header_rows=1)
   for e in d['items'][1:]:e['table_ref']=first['id']
   f.write_text(json.dumps(d))
  out=self.root/'table.pdf';self.run_cli('build','--work',self.work,'--output',out)
  pdf=PdfReader(out);self.assertGreater(len(pdf.pages),3)
  self.assertTrue(all('项目' in p.extract_text() for p in pdf.pages))
  text=''.join(p.extract_text() for p in pdf.pages)
  self.assertEqual(text.count('指标69'),3)
 def test_table_rejects_ragged_rows_and_bad_reference(self):
  self.prepare();self.fill();f=next((self.work/'responses').glob('*.json'));d=json.loads(f.read_text());e=d['items'][0]
  e.update(role='table',rows=[['标题','值'],['缺列']],header_rows=1);f.write_text(json.dumps(d))
  self.assertIn('rectangular',self.run_cli('validate','--work',self.work,ok=False).stderr)
  e.update(role='body',table_ref='missing');f.write_text(json.dumps(d))
  self.assertIn('table_ref',self.run_cli('validate','--work',self.work,ok=False).stderr)
if __name__=='__main__':unittest.main()
