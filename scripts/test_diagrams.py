import copy, unittest
import slide_translate as s

FLOW={'kind':'flow','title':'监测与反馈','nodes':[{'id':'a','label':'采集数据'},{'id':'b','label':'检查异常'},{'id':'c','label':'通知医生'}], 'edges':[{'from':'a','to':'b','label':'输入'},{'from':'b','to':'c','label':'发现异常'},{'from':'b','to':'a','label':'继续监测'}]}
GANTT={'kind':'gantt','title':'项目安排','periods':['第一周','第二周','第三周'], 'tasks':[{'label':'需求分析','start':0,'end':1},{'label':'方案设计','start':1,'end':3}]}
class DiagramTests(unittest.TestCase):
 def test_simple_flow_labels_are_inside_diagram(self):
  s.choose_font(None,'监测与反馈采集数据检查异常通知医生输入发现异常继续监测')
  fs=s.diagram_flowables(FLOW)
  self.assertEqual(len(fs),2,'Simple flow should not need a separate numbered edge legend')
 def test_invalid_edge_and_time_rejected(self):
  s.check_diagram(FLOW,'test');s.check_diagram(GANTT,'test')
  bad=copy.deepcopy(FLOW);bad['edges'][0]['to']='missing'
  with self.assertRaises(s.UserError):s.check_diagram(bad,'test')
  bad=copy.deepcopy(GANTT);bad['tasks'][0]['end']=4
  with self.assertRaises(s.UserError):s.check_diagram(bad,'test')
 def test_diagram_does_not_replace_translation_and_is_searchable(self):
  from reportlab.pdfgen import canvas
  from pypdf import PdfReader
  import io
  s.choose_font(None,'完整正文监测与反馈采集数据检查异常通知医生输入发现异常继续监测项目安排第一周第二周第三周需求分析方案设计关系整理0123456789')
  e={'zh':'完整正文','role':'body','status':'translated','diagram':FLOW}
  fs=s.page_paragraphs({},dict(items=[e],notes=[],unreviewed=False))
  self.assertEqual(fs[0].getPlainText(),'完整正文');self.assertGreater(len(fs),1)
  buf=io.BytesIO();c=canvas.Canvas(buf,pagesize=(500,842))
  for page in s.paginate(fs+s.diagram_flowables(GANTT),432,700):
   y=780
   for f,h,b,a in page:y-=b;f.drawOn(c,34,y-h);y-=h+a
   c.showPage()
  c.save();text=''.join(p.extract_text() for p in PdfReader(buf).pages)
  for word in ['完整正文','发现异常','继续监测','需求分析','第三周']:self.assertIn(word,text)
 def test_diagram_labels_are_audited(self):
  e={'zh':'正文','role':'body','status':'translated','diagram':copy.deepcopy(FLOW)}
  e['diagram']['nodes'][0]['label']='Collect data'
  issues,_=s.quality_findings({1:dict(items=[e],notes=[])})
  self.assertTrue(issues)
 def test_cli_build_preserves_page_and_requires_image_review(self):
  import tempfile,json,subprocess,sys
  from pathlib import Path
  from reportlab.pdfgen import canvas
  from pypdf import PdfReader
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);source=root/'source.pdf';job=root/'job'
   c=canvas.Canvas(str(source));c.drawString(30,700,'Example');c.save()
   def run(*args):return subprocess.run([sys.executable,str(Path(s.__file__)),*map(str,args)],capture_output=True,text=True)
   self.assertEqual(run('prepare',source,'--layout','two-column','--work',job).returncode,0)
   f=next((job/'requests').glob('*.json'));q=json.loads(f.read_text())
   response=dict(document_id=q['document_id'],chunk_id=q['chunk_id'],visual_review='reviewed',items=[dict(id=q['items'][0]['id'],zh='完整正文',role='body',status='translated',diagram=FLOW)],figure_notes=[dict(source='原页时间图',zh='项目安排',role='caption',status='translated',diagram=GANTT)])
   dest=job/'responses'/f.name;dest.write_text(json.dumps(response))
   result=run('build','--work',job,'--output',root/'result.pdf');self.assertEqual(result.returncode,0,result.stderr)
   text=''.join(p.extract_text() for p in PdfReader(root/'result.pdf').pages);self.assertIn('通知医生',text);self.assertIn('需求分析',text)
   response['visual_review']='unavailable';dest.write_text(json.dumps(response))
   result=run('build','--work',job,'--output',root/'bad.pdf','--allow-unreviewed-images');self.assertNotEqual(result.returncode,0);self.assertIn('review the source image',result.stderr)
if __name__=='__main__':unittest.main()
