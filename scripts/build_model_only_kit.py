"""Regenerate the standalone kit from maintained documents and runtime modules."""
from pathlib import Path
import argparse,re,posixpath
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument("--check",action="store_true",help="Fail if the committed kit is out of date")
args=parser.parse_args()
root=Path(__file__).resolve().parent.parent
docs=['SKILL.md']+[str(p.relative_to(root)) for p in sorted((root/'references').glob('*.md'))]
def anchor(rel):return 'doc-'+rel.removesuffix('.md').replace('/','-')
parts=['# 三栏课件翻译与精简复习资料：独立工具包\n\n当前模型完成翻译与复习内容；不需要额外翻译API。以下含规范和全部三个执行模块，将代码块保存为标明的文件名，安装列出的依赖后使用。\n']
for rel in docs:
 text=(root/rel).read_text()
 if rel=='SKILL.md':text=re.sub(r'^---\n.*?\n---\n','',text,flags=re.S)
 def link(m):
  label,target=m.groups();resolved=posixpath.normpath(posixpath.join(posixpath.dirname(rel),target))
  return '['+label+'](#'+anchor(resolved)+')' if resolved in docs else m.group(0)
 text=re.sub(r'\[([^\]]+)\]\(([^)]+\.md)\)',link,text)
 parts.append('\n<a id="'+anchor(rel)+'"></a>\n<!-- 嵌入来源：'+rel+' -->\n\n'+text)
for rel in ['scripts/slide_translate.py','scripts/three_column.py','scripts/layout_translation.py','scripts/requirements.txt']:
 parts.append('\n## 文件：'+rel+'\n\n```'+('python' if rel.endswith('.py') else 'text')+'\n'+(root/rel).read_text()+'\n```\n')
rendered='\n'.join(parts)
output=root/'MODEL_ONLY_KIT.md'
if args.check:
 if not output.exists() or output.read_text()!=rendered:raise SystemExit('MODEL_ONLY_KIT.md is out of date; run scripts/build_model_only_kit.py')
 print('Standalone kit is synchronized.')
else:
 output.write_text(rendered)
 print('Regenerated MODEL_ONLY_KIT.md')
