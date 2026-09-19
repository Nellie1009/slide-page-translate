import json, subprocess, sys, tempfile, unittest
from pathlib import Path
from reportlab.pdfgen import canvas
from pypdf import PdfReader

SCRIPT=Path(__file__).with_name('slide_translate.py')
class ThreeColumnTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name); self.work=self.root/'job'; self.source=self.root/'source.pdf'
  c=canvas.Canvas(str(self.source),pagesize=(720,405))
  for n in range(2):
   c.setFillColorRGB(.8,.1,.1); c.setFont('Helvetica',24); c.drawString(40,340,'Motion and speed')
   c.setFillColorRGB(0,.3,.5); c.setFont('Helvetica',18); c.drawString(40,290,'Speed is distance divided by time.')
   c.setFillColorRGB(.2,.6,.3); c.rect(440,80,150,100,fill=1); c.showPage()
  c.save()
 def tearDown(self): self.tmp.cleanup()
 def cli(self,*args,ok=True):
  r=subprocess.run([sys.executable,str(SCRIPT),*map(str,args)],capture_output=True,text=True)
  self.assertEqual(r.returncode==0,ok,r.stdout+r.stderr);return r
 def prepare(self):
  self.cli('prepare',self.source,'--work',self.work)
  return json.loads((self.work/'manifest.json').read_text())
 def fill(self,long=False):
  for file in (self.work/'requests').glob('*.json'):
   q=json.loads(file.read_text());items=[]
   for e in q['items']:
    zh={'Motion and speed':'运动与速度','Speed is distance divided by time.':'速度是距离除以时间。'}[e['source']]
    items.append(dict(id=e['id'],zh=zh,status='translated',role='body'))
   study=dict(page_kind='content',objective='理解速度如何描述运动快慢。',sections=[dict(title='本页逻辑',body=('同一距离，时间越短，速度越大。'*800 if long else '比较快慢需要同时考虑距离与时间。'),basis='explanation',source_pages=[q['page']])],self_test=[dict(question='同样距离，用时加倍时速度如何变化？',answer='速度减半。',source_pages=[q['page']])],exam=dict(status='review_suggestion',reason='这是理解公式的基础。',syllabus_quotes=[]))
   a=dict(document_id=q['document_id'],chunk_id=q['chunk_id'],visual_review='reviewed',items=items,figure_notes=[],study=study if q['part']==1 else None)
   (self.work/'responses'/file.name).write_text(json.dumps(a,ensure_ascii=False))
 def test_default_prepare_records_layout_and_new_schema(self):
  m=self.prepare();self.assertEqual(m['schema_version'],2);self.assertEqual(m['layout'],'three-column')
  self.assertIn('layout',m['pages'][0]['items'][0]);self.assertIn('study',next((self.work/'prompts').glob('p*.txt')).read_text())
 def test_missing_study_blocks_export(self):
  self.prepare();self.fill();f=next((self.work/'responses').glob('*.json'));d=json.loads(f.read_text());d.pop('study');f.write_text(json.dumps(d))
  r=self.cli('build','--work',self.work,'--output',self.root/'out.pdf',ok=False);self.assertIn('study',r.stderr);self.assertFalse((self.root/'out.pdf').exists())
 def test_three_columns_and_chinese_translation_have_same_scale(self):
  self.prepare();self.fill();out=self.root/'out.pdf';self.cli('build','--work',self.work,'--output',out)
  report=json.loads((self.work/'build-report.json').read_text());self.assertEqual(report['layout'],'three-column');self.assertEqual(len(PdfReader(out).pages),2)
  for page in report['pages']:
   self.assertEqual(page['original_scale'],page['translated_scale']);self.assertEqual(len(page['columns']),3)
  text=PdfReader(out).pages[0].extract_text();self.assertIn('知识点梳理',text);self.assertIn('运动与速度',text);self.assertIn('比较快慢',text)
  self.assertTrue((self.work/'translated.pdf').exists());self.cli('verify','--work',self.work);self.assertTrue((self.work/'qa/contact-001.jpg').exists())
 def test_long_study_continues_without_reflowing_translated_page(self):
  self.prepare();self.fill(long=True);self.cli('build','--work',self.work,'--output',self.root/'out.pdf')
  report=json.loads((self.work/'build-report.json').read_text());self.assertGreater(report['output_pages'],2)
  self.assertEqual(len(PdfReader(self.work/'translated.pdf').pages),2)
  seq=[x['source_page'] for x in report['pages']];self.assertEqual(seq,sorted(seq));self.assertEqual(set(seq),{1,2})
 def test_invalid_source_reference_and_unsupported_exam_claim_fail(self):
  self.prepare();self.fill();f=next((self.work/'responses').glob('*.json'));d=json.loads(f.read_text());d['study']['sections'][0]['source_pages']=[999];f.write_text(json.dumps(d))
  self.assertIn('source_pages',self.cli('validate','--work',self.work,ok=False).stderr)
  d['study']['sections'][0]['source_pages']=[1];d['study']['exam']['status']='provided_syllabus';f.write_text(json.dumps(d))
  self.assertIn('syllabus',self.cli('validate','--work',self.work,ok=False).stderr)
 def test_missing_image_review_cannot_be_waived_for_v2(self):
  self.prepare();self.fill();f=next((self.work/'responses').glob('*.json'));d=json.loads(f.read_text());d['visual_review']='unavailable';f.write_text(json.dumps(d))
  self.cli('build','--work',self.work,'--output',self.root/'out.pdf','--allow-unreviewed-images',ok=False)
 def test_native_style_cannot_be_overridden_and_retained_terms_rejected(self):
  self.prepare();self.fill();f=next((self.work/'responses').glob('*.json'));d=json.loads(f.read_text());d['items'][0]['layout']={'font_size':6};f.write_text(json.dumps(d))
  self.cli('validate','--work',self.work,ok=False)
  d['items'][0].pop('layout');d['items'][0]['retained_terms']=[{'text':'Motion','reason':'term'}];f.write_text(json.dumps(d));self.cli('validate','--work',self.work,ok=False)
 def test_changed_request_or_geometry_is_rejected(self):
  self.prepare();self.fill();f=next((self.work/'requests').glob('*.json'));d=json.loads(f.read_text());d['items'][0]['source']='Other';f.write_text(json.dumps(d))
  self.cli('validate','--work',self.work,ok=False)
 def test_supplied_pdf_is_protected_even_with_force(self):
  import hashlib
  exported=self.root/'exported.pdf';exported.write_bytes(self.source.read_bytes())
  self.cli('prepare',self.source,'--normalized-pdf',exported,'--work',self.work);self.fill()
  before=hashlib.sha256(exported.read_bytes()).hexdigest()
  self.cli('build','--work',self.work,'--output',exported,'--force',ok=False)
  self.assertEqual(hashlib.sha256(exported.read_bytes()).hexdigest(),before)
 def test_preservation_categories_cannot_exempt_english_prose(self):
  self.prepare();self.fill();f=next((self.work/'responses').glob('*.json'));d=json.loads(f.read_text())
  q=json.loads((self.work/'requests'/f.name).read_text())
  for reason in ['name','code','url']:
   with self.subTest(reason=reason):
    for e,s in zip(d['items'],q['items']):e.update(zh=s['source'],status='preserved',preserve_reason=reason)
    f.write_text(json.dumps(d));self.cli('validate','--work',self.work,ok=False)
 def test_study_heading_is_kept_with_body_when_body_needs_splitting(self):
  import slide_translate as api
  from reportlab.platypus import Paragraph
  from reportlab.lib.styles import ParagraphStyle
  body=ParagraphStyle('body',fontName='Helvetica',fontSize=10,leading=12,keepWithNext=False)
  head=ParagraphStyle('head',parent=body,keepWithNext=True)
  filler=Paragraph('line<br/>line<br/>line<br/>line<br/>line',body)
  heading=Paragraph('Heading',head)
  paragraph=Paragraph('body<br/>body<br/>body<br/>body<br/>body',body)
  pages=api.paginate([filler,heading,paragraph],200,100)
  for page in pages:
   self.assertFalse(page[-1][0].style.keepWithNext,'orphaned heading')
if __name__=='__main__':unittest.main()
