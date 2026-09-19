import copy
import tempfile
import unittest
from pathlib import Path
from io import BytesIO
from PIL import Image
from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

FONT = '/System/Library/Fonts/Supplemental/Arial Unicode.ttf'

class LayoutTranslationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.source = self.root / 'original.pdf'
        pdfmetrics.registerFont(TTFont('TestCJK', FONT))
        c = canvas.Canvas(str(self.source), pagesize=(400, 260))
        c.setFillColorRGB(.2, .4, .6)
        c.setFont('Helvetica', 20)
        c.drawString(30, 210, 'Original title')
        c.setFillColorRGB(0, 0, 0)
        c.setFont('TestCJK', 12)
        c.drawString(30, 170, '已有中文 123')
        c.setFillColorRGB(1, 0, 0)
        c.rect(220, 20, 100, 80, fill=1)
        image = Image.new('RGB', (40, 40), (31, 192, 98))
        self.img = self.root / 'img.png'
        image.save(self.img)
        c.drawImage(str(self.img), 250, 150, width=40, height=40)
        c.save()
    def tearDown(self):
        self.tmp.cleanup()
    def module(self):
        import layout_translation
        return layout_translation
    def prepared(self):
        m = self.module()
        pages = m.extract_pages(self.source)
        results = {1: {'items': [{'id': i['id'], 'zh': '标题' if i['source'] == 'Original title' else i['source'], 'status': 'translated' if i['source'] == 'Original title' else 'preserved'} for i in pages[0]['items']], 'notes': []}}
        return m, {'pages': pages}, results
    def test_extract_operation_geometry_and_all_languages(self):
        pages = self.module().extract_pages(self.source)
        self.assertEqual(len(pages), 1)
        self.assertEqual([i['source'] for i in pages[0]['items']], ['Original title', '已有中文 123'])
        item = pages[0]['items'][0]
        self.assertEqual(item['id'], 'p0001-t0001')
        self.assertEqual(item['layout']['origin'], [30.0, 50.0])
        self.assertEqual(item['layout']['font_size'], 20)
        self.assertEqual(item['layout']['color'], [.2, .4, .6])
    def test_replacement_preserves_styles_chinese_and_original_image(self):
        m, manifest, results = self.prepared()
        out = self.root / 'translated.pdf'
        report = m.render_translated(self.source, manifest, results, out, FONT)
        self.assertTrue(out.exists())
        p = PdfReader(out).pages[0]
        self.assertIn('已有中文 123', p.extract_text())
        self.assertIn('标题', p.extract_text())
        self.assertNotIn('Original title', p.extract_text())
        self.assertEqual(list(PdfReader(self.source).pages[0].images)[0].data, list(p.images)[0].data)
        self.assertIn(b'220 20 100 80 re', p.get_contents().get_data())
        translated = next(i for i in m.extract_pages(out)[0]['items'] if i['source'] == '标题')
        self.assertEqual(translated['layout']['origin'], [30.0, 50.0])
        self.assertEqual(translated['layout']['font_size'], 20)
        self.assertEqual(translated['layout']['color'], [.2, .4, .6])
        self.assertTrue(report['font_substitutions'])
    def test_overflow_has_actionable_id_and_does_not_write(self):
        m, manifest, results = self.prepared()
        results[1]['items'][0]['zh'] = '极长中文标题' * 20
        out = self.root / 'overflow.pdf'
        with self.assertRaisesRegex(ValueError, 'p0001-t0001.*(fit|overflow)'):
            m.render_translated(self.source, manifest, results, out, FONT)
        self.assertFalse(out.exists())
    def test_manifest_geometry_cannot_be_widened(self):
        m, manifest, results = self.prepared()
        manifest['pages'][0]['items'][0]['layout']['bbox'][2] = 390
        with self.assertRaisesRegex(ValueError, 'p0001-t0001.*(layout|geometry|source)'):
            m.render_translated(self.source, manifest, results, self.root / 'bad.pdf', FONT)
    def test_raster_requires_verified_simple_background(self):
        m, manifest, results = self.prepared()
        results[1]['notes'] = [{'id':'raster-1', 'source':'Label', 'zh':'标签', 'layout': {'bbox':[200,100,300,120], 'font_size':12, 'color':[0,0,0], 'background_color':[1,1,1]}}]
        with self.assertRaisesRegex(ValueError, '(raster-1|figure).*background'):
            m.render_translated(self.source, manifest, results, self.root / 'bad.pdf', FONT)
    def test_rotated_source_preserves_display_shape(self):
        writer = PdfWriter()
        writer.add_page(PdfReader(self.source).pages[0]).rotate(90)
        rotated = self.root / 'rotated.pdf'
        with rotated.open('wb') as f: writer.write(f)
        m=self.module()
        pages=m.extract_pages(rotated)
        self.assertEqual((pages[0]['width'],pages[0]['height']),(260,400))
        results={1:{'items':[{'id':i['id'],'zh':'标题' if i['source']=='Original title' else i['source']} for i in pages[0]['items']], 'notes':[]}}
        out=self.root/'rotated-out.pdf'
        m.render_translated(rotated,{'pages':pages},results,out,FONT)
        self.assertIn('标题',PdfReader(out).pages[0].extract_text())
    def test_adjacent_text_position_survives(self):
        c=canvas.Canvas(str(self.source),pagesize=(400,260))
        t=c.beginText(30,210); t.setFont('Helvetica',20); t.textOut('Original title'); t.textOut('123'); c.drawText(t); c.save()
        m, manifest, results = self.prepared()
        before = manifest['pages'][0]['items'][1]['layout']['origin']
        out=self.root/'adjacent.pdf'
        m.render_translated(self.source,manifest,results,out,FONT)
        after=next(i for i in m.extract_pages(out)[0]['items'] if i['source']=='123')['layout']['origin']
        self.assertEqual(before, after)

    def test_illustration_pixels_are_identical(self):
        import pypdfium2 as pdfium
        m, manifest, results = self.prepared()
        out = self.root / 'pixels.pdf'
        m.render_translated(self.source, manifest, results, out, FONT)
        before = pdfium.PdfDocument(self.source)[0].render(scale=2).to_pil()
        after = pdfium.PdfDocument(out)[0].render(scale=2).to_pil()
        self.assertEqual(before.crop((430,130,660,490)).tobytes(), after.crop((430,130,660,490)).tobytes())
    def test_verified_raster_translation_reports_approximation(self):
        m, manifest, results = self.prepared()
        results[1]['notes'] = [{'id':'raster-1','source':'Label','zh':'标签','layout':{'bbox':[10,220,110,240],'font_size':12,'color':[0,0,0],'background_color':[1,1,1],'background_verified':True}}]
        out=self.root/'raster.pdf'
        report=m.render_translated(self.source,manifest,results,out,FONT)
        self.assertEqual(report['raster_replacements'][0]['id'],'raster-1')
        self.assertIn('标签',PdfReader(out).pages[0].extract_text())
    def test_crop_is_supported_with_visible_geometry(self):
        writer=PdfWriter(); page=writer.add_page(PdfReader(self.source).pages[0]); page.cropbox.lower_left=(20,20)
        path=self.root/'crop.pdf'
        with path.open('wb') as f: writer.write(f)
        pages=self.module().extract_pages(path)
        self.assertEqual((pages[0]['width'],pages[0]['height']),(380,240))
    def test_text_inside_reused_form_is_translated(self):
        c=canvas.Canvas(str(self.source),pagesize=(400,260)); c.beginForm('label'); c.drawString(30,210,'Form label'); c.endForm(); c.doForm('label'); c.save()
        m=self.module(); pages=m.extract_pages(self.source)
        self.assertEqual(pages[0]['items'][0]['source'],'Form label')
        results={1:{'items':[{'id':pages[0]['items'][0]['id'],'zh':'标签'}],'notes':[]}}
        out=self.root/'form.pdf'; m.render_translated(self.source,{'pages':pages},results,out,FONT)
        self.assertIn('标签',PdfReader(out).pages[0].extract_text())
        self.assertNotIn('Form label',PdfReader(out).pages[0].extract_text())
    def test_font_must_cover_every_translation_glyph(self):
        m,manifest,results=self.prepared(); results[1]['items'][0]['zh']='\U0010ffff'
        with self.assertRaisesRegex(ValueError,'p0001-t0001.*glyph'):
            m.render_translated(self.source,manifest,results,self.root/'glyph.pdf',FONT)
    def test_changed_source_graphics_rejected(self):
        m,manifest,results=self.prepared()
        manifest['pages'][0]['content_sha256']='stale'
        with self.assertRaisesRegex(ValueError,'Page 1.*source'):
            m.render_translated(self.source,manifest,results,self.root/'stale.pdf',FONT)
    def test_clipped_text_fails_before_overlay(self):
        c=canvas.Canvas(str(self.source),pagesize=(400,260)); path=c.beginPath(); path.rect(30,190,60,40); c.clipPath(path,stroke=0); c.setFont('Helvetica',20); c.drawString(30,210,'Original title'); c.save()
        m,manifest,results=self.prepared()
        with self.assertRaisesRegex(ValueError,'clipp'):
            m.render_translated(self.source,manifest,results,self.root/'clip.pdf',FONT)

    def test_bold_italic_fallback_preserves_emphasis(self):
        c=canvas.Canvas(str(self.source),pagesize=(400,260)); c.setFont('Helvetica-BoldOblique',20); c.drawString(30,210,'Original title'); c.save()
        m,manifest,results=self.prepared(); out=self.root/'emphasis.pdf'
        report=m.render_translated(self.source,manifest,results,out,FONT)
        self.assertEqual(report['font_substitutions'][0]['synthesized_styles'],['bold','italic'])
        ops=PdfReader(out).pages[0].get_contents().operations
        self.assertTrue(any(op==b'Tr' and int(args[0])==2 for args,op in ops))
        self.assertTrue(any(op==b'Tm' and abs(float(args[2]))>.1 for args,op in ops))
    def test_cropped_replacement_preserves_source_pixels(self):
        import pypdfium2 as pdfium
        writer=PdfWriter(); page=writer.add_page(PdfReader(self.source).pages[0]); page.cropbox.lower_left=(20,20)
        source=self.root/'cropped-source.pdf'
        with source.open('wb') as f: writer.write(f)
        m=self.module(); pages=m.extract_pages(source)
        responses={1:{'items':[{'id':i['id'],'zh':'标题' if i['source']=='Original title' else i['source']} for i in pages[0]['items']],'notes':[]}}
        out=self.root/'cropped-out.pdf'; m.render_translated(source,{'pages':pages},responses,out,FONT)
        before=pdfium.PdfDocument(source)[0].render(scale=2).to_pil()
        after=pdfium.PdfDocument(out)[0].render(scale=2).to_pil()
        self.assertEqual(before.size,after.size)
        self.assertEqual(before.crop((410,130,620,450)).tobytes(),after.crop((410,130,620,450)).tobytes())
        self.assertIn('已有中文 123',PdfReader(out).pages[0].extract_text())

    def test_indirect_resources_extracts_safely(self):
        writer=PdfWriter(); page=writer.add_page(PdfReader(self.source).pages[0])
        page[NameObject('/Resources')]=writer._add_object(page['/Resources'])
        path=self.root/'indirect.pdf'
        with path.open('wb') as f: writer.write(f)
        pages=self.module().extract_pages(path)
        self.assertEqual(pages[0]['items'][0]['source'],'Original title')
    def test_synthesized_style_does_not_leak_to_next_span(self):
        c=canvas.Canvas(str(self.source),pagesize=(400,260)); c.setFont('Helvetica-BoldOblique',20); c.drawString(30,210,'Original title'); c.setFont('Helvetica',20); c.drawString(30,160,'Second title'); c.save()
        m,manifest,results=self.prepared();results[1]['items'][1]={'id':manifest['pages'][0]['items'][1]['id'],'zh':'次题','status':'translated'}
        out=self.root/'no-leak.pdf';m.render_translated(self.source,manifest,results,out,FONT)
        item=next(i for i in m.extract_pages(out)[0]['items'] if i['source']=='次题')
        self.assertEqual(item['layout']['render_mode'],0)
        self.assertEqual(item['layout']['matrix'],[1,0,0,1])

    def test_italic_shear_does_not_escape_source_region(self):
        c=canvas.Canvas(str(self.source),pagesize=(400,260));c.setFont('Helvetica-Oblique',20);c.drawString(30,210,'Four');c.save()
        m=self.module();pages=m.extract_pages(self.source);results={1:{'items':[{'id':pages[0]['items'][0]['id'],'zh':'标题'}],'notes':[]}}
        with self.assertRaisesRegex(ValueError,'p0001-t0001.*overflow'):
            m.render_translated(self.source,{'pages':pages},results,self.root/'italic-overflow.pdf',FONT)

    def test_libreoffice_rounded_page_clip_is_supported(self):
        c=canvas.Canvas(str(self.source),pagesize=(400,260));p=c.beginPath();p.rect(0,.028,399.972,259.972);c.clipPath(p,stroke=0);c.setFont('Helvetica',20);c.drawString(30,210,'Original title');c.save()
        m,manifest,results=self.prepared();out=self.root/'page-clip.pdf'
        m.render_translated(self.source,manifest,results,out,FONT)
        self.assertIn('标题',PdfReader(out).pages[0].extract_text())
        self.assertNotIn('Original title',PdfReader(out).pages[0].extract_text())
    def test_restrictive_form_clip_is_rejected(self):
        c=canvas.Canvas(str(self.source),pagesize=(400,260));c.beginForm('label');p=c.beginPath();p.rect(30,190,14,40);c.clipPath(p,stroke=0);c.setFont('Helvetica',20);c.drawString(30,210,'Original title');c.endForm();c.doForm('label');c.save()
        m,manifest,results=self.prepared()
        with self.assertRaisesRegex(ValueError,'clipp'):
            m.render_translated(self.source,manifest,results,self.root/'bad-form-clip.pdf',FONT)
    def test_outline_rendering_in_form_is_rejected(self):
        c=canvas.Canvas(str(self.source),pagesize=(400,260));c.beginForm('label');t=c.beginText(30,210);t.setFont('Helvetica',20);t.setTextRenderMode(1);t.textOut('Original title');c.drawText(t);c.endForm();c.doForm('label');c.save()
        m,manifest,results=self.prepared()
        with self.assertRaisesRegex(ValueError,'render'):
            m.render_translated(self.source,manifest,results,self.root/'bad-form-render.pdf',FONT)

if __name__ == '__main__': unittest.main()
