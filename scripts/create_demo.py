"""Reproduce the synthetic public demo; never reads a user's teaching material.

Run without flags to create the source and unreviewed response fixtures. Inspect
all job/pages pages before --build-reviewed; inspect the result separately.
The bilingual content below is authored specifically for this fixed fixture,
not a dictionary-based translation implementation for arbitrary documents.
"""
import argparse
import json
import math
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
CLI = ROOT / 'scripts/slide_translate.py'
ASSETS = ROOT / 'assets/examples'

PAGES = [
    [
        ('Imaging and Measurement', '成像与测量', 30, 64, 315, 'title'),
        ('From light to a digital image', '从光到数字图像', 20, 64, 269, 'body'),
        ('A short introduction', '简明入门', 16, 64, 222, 'body'),
    ],
    [
        ('Course structure', '课程结构', 28, 40, 341, 'title'),
        ('Light enters the optical system.', '光进入光学系统。', 19, 40, 290, 'body'),
        ('The sensor converts light into an electrical signal.', '传感器将光转换为电信号。', 19, 40, 255, 'body'),
        ('A digital image is formed from sampled measurements.', '采样测量值形成数字图像。', 19, 40, 220, 'body'),
        ('Optical system', '光学系统', 16, 55, 111, 'caption'),
        ('Light sensor', '光传感器', 16, 259, 111, 'caption'),
        ('Digital image', '数字图像', 16, 460, 111, 'caption'),
    ],
    [
        ('Optical sensor', '光学传感器', 28, 40, 341, 'title'),
        ('A sensor converts a physical input into a measurable signal.', '传感器将物理输入转换为可测量的信号。', 18, 40, 285, 'body'),
        ('An optical sensor responds to incoming light.', '光学传感器响应入射光。', 18, 40, 253, 'body'),
        ('Incoming light', '入射光', 18, 49, 186, 'caption'),
        ('Electrical signal', '电信号', 18, 396, 186, 'caption'),
    ],
    [
        ('Sampling and quantization', '采样与量化', 28, 40, 341, 'title'),
        ('Sampling selects values at discrete positions.', '采样在离散位置选取数值。', 19, 40, 285, 'body'),
        ('Quantization maps values to a finite set of levels.', '量化将数值映射到有限的等级。', 19, 40, 251, 'body'),
        ('Discrete positions', '离散位置', 17, 68, 194, 'caption'),
        ('Finite levels', '有限等级', 17, 390, 194, 'caption'),
    ],
    [
        ('Image size and bit depth', '图像尺寸与位深', 28, 40, 341, 'title'),
        ('Image size counts pixels along each dimension.', '图像尺寸表示各维度的像素数。', 19, 40, 286, 'body'),
        ('Bit depth sets the number of bits used per pixel.', '位深表示每个像素使用的位数。', 19, 40, 252, 'body'),
        ('For grayscale data, 8 bits represent 256 intensity levels.', '灰度数据中，8位可表示256个强度等级。', 19, 40, 218, 'body'),
        ('Pixel grid', '像素网格', 17, 56, 169, 'caption'),
        ('Intensity levels', '强度等级', 17, 370, 169, 'caption'),
    ],
]
STUDIES = [
    dict(mode='outline', page_kind='title', points=[]),
    dict(mode='outline', page_kind='content', points=[
        dict(kind='structure', title='整体知识架构',
             answer='成像流程：光学系统 → 传感器 → 数字图像。\n先理解光如何变成信号，再理解采样与量化；最后用尺寸和位深描述图像。', source_pages=[2,3,4,5]),
    ]),
    dict(mode='outline', page_kind='content', points=[
        dict(kind='term', title='术语｜传感器',
             answer='传感器（sensor）：将物理输入转换为可测量的信号。光学传感器响应入射光。', source_pages=[3]),
    ]),
    dict(mode='outline', page_kind='content', points=[
        dict(kind='distinction', title='辨析｜采样与量化',
             answer='1. 采样（sampling）：在离散位置选取数值。\n2. 量化（quantization）：将数值映射到有限的等级。\n核心区别：采样离散化位置；量化离散化数值。', source_pages=[4]),
    ]),
    dict(mode='outline', page_kind='content', points=[
        dict(kind='short_answer', title='短答｜图像尺寸', question_zh='图像尺寸表示什么？',
             question_en='What does image size count?', answer_zh='图像尺寸表示各维度的像素数。',
             answer_en='Image size counts pixels along each dimension.', source_pages=[5]),
        dict(kind='short_answer', title='短答｜灰度等级', question_zh='8位灰度数据可表示多少个强度等级？',
             question_en='How many intensity levels can 8-bit grayscale data represent?',
             answer_zh='灰度数据中，8位可表示256个强度等级。',
             answer_en='For grayscale data, 8 bits represent 256 intensity levels.', source_pages=[5]),
    ]),
]

def run(*args):
    subprocess.run([sys.executable, str(CLI), *map(str,args)], check=True)


def source_pdf(path):
    from reportlab.pdfgen import canvas
    from reportlab.lib.colors import HexColor
    c = canvas.Canvas(str(path), pagesize=(640,400), invariant=1)
    c.setTitle('Imaging and Measurement - Synthetic Example')
    c.setAuthor('')
    c.setSubject('Original synthetic teaching example; no personal or course data')
    c.setCreator('slide-page-translate demo')
    navy,teal,orange = '#17334B','#138E91','#D76C36'
    def color(value): c.setFillColor(HexColor(value));c.setStrokeColor(HexColor(value))
    def line(points, stroke=teal, width=2):
        color(stroke);c.setLineWidth(width)
        p=c.beginPath();p.moveTo(*points[0])
        for xy in points[1:]:p.lineTo(*xy)
        c.drawPath(p)
    for n, rows in enumerate(PAGES,1):
        color('#F8FAFC');c.rect(0,0,640,400,fill=1,stroke=0)
        color(teal);c.rect(0,384,640,16,fill=1,stroke=0)
        if n==1:
            for x, y, r in [(130,110,38),(320,110,47),(510,110,38)]:
                color('#D6EBEC');c.circle(x,y,r,fill=1,stroke=0)
            line([(168,110),(273,110)]);line([(367,110),(472,110)])
            color(teal);c.circle(130,110,15,fill=1,stroke=0)
            color(navy);c.roundRect(292,90,56,40,5,fill=1,stroke=0)
            color('#F8FAFC');c.circle(320,110,12,fill=1,stroke=0)
            for i in range(3):
                for j in range(3):
                    color(teal if (i+j)%2 else orange);c.rect(492+i*13,92+j*13,10,10,fill=1,stroke=0)
        if n==2:
            for x in [40,240,440]:
                color('#E1EFF0');c.roundRect(x,85,155,67,7,fill=1,stroke=0)
            for x in [198,398]:
                line([(x,118),(x+35,118)]);line([(x+28,123),(x+35,118),(x+28,113)])
        if n==3:
            color('#D6EBEC');c.roundRect(267,90,85,77,7,fill=1,stroke=0)
            for y in [104,128,152]:
                line([(50,y),(260,y)],orange);line([(250,y+5),(260,y),(250,y-5)],orange)
            line([(359,129)]+[(x,129+25*math.sin((x-359)/17)) for x in range(360,590)],teal)
        if n==4:
            for x in [48,360]:
                line([(x,65),(x,169)],navy,1);line([(x,65),(x+221,65)],navy,1)
            line([(x,111+31*math.sin((x-48)/35)) for x in range(48,270)],'#AABAC9',2)
            for x in range(58,270,25):
                y=111+31*math.sin((x-48)/35);line([(x,65),(x,y)],teal,1)
                color(teal);c.circle(x,y,3,fill=1,stroke=0)
            line([(360,90),(390,90),(390,115),(425,115),(425,140),(475,140),(475,115),(510,115),(510,90),(570,90)],orange,3)
        if n==5:
            for i in range(8):
                for j in range(4):
                    color('#138E91' if (i+j)%3 else '#B4DEDF');c.rect(57+i*25,55+j*22,22,19,fill=1,stroke=0)
            for i in range(16):
                c.setFillGray(i/15);c.rect(365+i*14,88,14,40,fill=1,stroke=0)
        for en,zh,size,x,y,role in rows:
            color(navy if role=='title' else (teal if role=='caption' else '#263D50'))
            c.setFont('Helvetica-Bold' if role=='title' else 'Helvetica',size)
            c.drawString(x,y,en)
        color('#607487');c.setFont('Helvetica',10);c.drawString(606,22,str(n))
        c.showPage()
    c.save()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work',type=Path,default=ROOT/'tmp/demo-job')
    parser.add_argument('--build-reviewed',action='store_true',help='Only after visually reviewing every original page')
    parser.add_argument('--font',help='CJK TrueType font for translation and notes')
    args=parser.parse_args();work=args.work.resolve();ASSETS.mkdir(parents=True,exist_ok=True)
    source=ASSETS/'imaging-basics-source.pdf';result=ASSETS/'imaging-basics-three-column.pdf'
    if not args.build_reviewed:
        if work.exists() and any(work.iterdir()):parser.error('Use a new empty --work directory; existing work is preserved.')
        source_pdf(source)
        run('prepare',source,'--work',work,'--text-backend','mupdf')
        for request in sorted((work/'requests').glob('*.json')):
            q=json.loads(request.read_text());lookup={row[0]:row for row in PAGES[q['page']-1]};items=[]
            for item in q['items']:
                original=item['source']
                if original in lookup:
                    row=lookup[original];items.append(dict(id=item['id'],zh=row[1],role=row[5],status='translated'))
                elif original==str(q['page']):
                    items.append(dict(id=item['id'],zh=original,role='footnote',status='preserved',preserve_reason='notation'))
                else:raise ValueError(f'Unexpected source text in the fixed synthetic fixture: {original!r}')
            response=dict(document_id=q['document_id'],chunk_id=q['chunk_id'],visual_review='unavailable',items=items,figure_notes=[],study=STUDIES[q['page']-1] if q['part']==1 else None)
            (work/'responses'/request.name).write_text(json.dumps(response,ensure_ascii=False,indent=2)+'\n')
        print('Inspect every original page in the job pages directory before --build-reviewed.')
        return
    for response in sorted((work/'responses').glob('*.json')):
        data=json.loads(response.read_text());data['visual_review']='reviewed'
        response.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    run('validate','--work',work);run('audit','--work',work)
    run('build','--work',work,'--output',result,'--force',*(['--font',args.font] if args.font else []))
    run('verify','--work',work,'--pages','1,2,3,4,5')
    import pymupdf
    with pymupdf.open(result) as doc:
        assert len(doc)==5, 'Demo should not have continuation pages'
        for i,page in enumerate(doc,1):
            page.get_pixmap(matrix=pymupdf.Matrix(1,1)).save(ASSETS/f'imaging-basics-page-{i}.png')
        assert '复习提纲' not in doc[0].get_text()
        fifth=doc[4].get_text()
        for entry in STUDIES[4]['points']:
            for key in ['question_zh','question_en','answer_zh','answer_en']:
                assert ''.join(entry[key].split()) in ''.join(fifth.split()), (key,entry[key])
    print('Five-page result generated; inspect all five PNGs before publishing.')

if __name__=='__main__':main()
