import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import slide_translate as api,three_column as engine
class OutlineContract(unittest.TestCase):
 def test_nonknowledge_page_can_have_no_study_content(self):
  study={'mode':'outline','page_kind':'title','points':[]}
  try:engine.validate_study(api,study,1,{1,2,3},'')
  except api.UserError as ex:self.fail(f'Blank revision column rejected: {ex}')
  self.assertEqual(engine.study_entries(study,1),[])
 def test_answer_follows_its_topic_without_added_teaching_sections(self):
  study={'mode':'outline','page_kind':'content','points':[{'title':'处理器分工','answer':'CPU协调；GPU并行计算。','source_pages':[3]}]}
  try:engine.validate_study(api,study,3,{1,2,3},'')
  except api.UserError as ex:self.fail(f'Concise answer rejected: {ex}')
  result=engine.study_entries(study,3)
  self.assertEqual([x['zh'] for x in result],['处理器分工','CPU协调；GPU并行计算。'])
 def test_invalid_sources_and_unsupported_official_claims_still_rejected(self):
  for point in [{'answer':'解释','source_pages':[99]},{'answer':'这是官方考纲中的必考知识','source_pages':[3]}]:
   with self.assertRaises(api.UserError):engine.validate_study(api,{'mode':'outline','page_kind':'content','points':[point]},3,{1,2,3},'')
class BilingualShortAnswer(unittest.TestCase):
 def point(self):
  return dict(kind='short_answer',title='处理器分工',question_zh='CPU有什么作用？',question_en='What is the role of the CPU?',answer_zh='协调应用。',answer_en='Coordination.',source_pages=[3])
 def test_question_and_answer_render_in_both_languages_together(self):
  study=dict(mode='outline',page_kind='content',points=[self.point()])
  try:engine.validate_study(api,study,3,{1,2,3},'')
  except api.UserError as ex:self.fail(str(ex))
  text='\n'.join(x['zh'] for x in engine.study_entries(study,3))
  for value in ['CPU有什么作用？','What is the role of the CPU?','协调应用。','Coordination.']:self.assertIn(value,text)
  self.assertLess(text.index('What is the role'),text.index('Coordination.'))
 def test_missing_english_answer_is_rejected(self):
  point=self.point();point.pop('answer_en')
  with self.assertRaises(api.UserError):engine.validate_study(api,dict(mode='outline',page_kind='content',points=[point]),3,{1,2,3},'')
if __name__=='__main__':unittest.main()
