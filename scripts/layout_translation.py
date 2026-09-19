"""Conservative PDF text replacement without altering existing image/vector operators.

Coordinates are points, measured from the top-left of a zero-origin, unrotated
page. A text-show operator is the translation unit. Unsupported geometry fails
explicitly; it is never silently flattened, resized, or guessed.
"""
from __future__ import annotations

import hashlib
import io
import math
from pathlib import Path

from pdfminer.converter import PDFPageAggregator
from pdfminer.pdfinterp import PDFPageInterpreter, PDFResourceManager
from pdfminer.pdfpage import PDFPage
from pypdf import PdfReader, PdfWriter
from pypdf.generic import ArrayObject, ContentStream, FloatObject
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

_SHOW = {b'Tj', b'TJ', b"'", b'"'}


def _rgb(value):
    if isinstance(value, (int, float)):
        return [float(value)] * 3
    value = list(value or (0, 0, 0))
    if len(value) == 1:
        return [float(value[0])] * 3
    if len(value) == 4:
        c, m, y, k = value
        return [round(1 - min(1, v + k), 6) for v in (c, m, y)]
    if len(value) != 3:
        raise ValueError('Unsupported native text color space')
    return [round(float(v), 6) for v in value]


class _OperationDevice(PDFPageAggregator):
    def __init__(self, manager):
        super().__init__(manager)
        self.records = []
        self.glyphs = []

    def render_char(self, *args, **kwargs):
        advance = super().render_char(*args, **kwargs)
        self.glyphs.append(self.cur_item._objs[-1])
        return advance

    def render_string(self, textstate, seq, ncs, graphicstate):
        start = len(self.glyphs)
        before = textstate.linematrix
        super().render_string(textstate, seq, ncs, graphicstate)
        glyphs = self.glyphs[start:]
        denominator = textstate.fontsize * textstate.scaling * .00001
        displacement = textstate.linematrix[0] - before[0]
        self.records.append({
            'glyphs': glyphs, 'advance_adjustment': -displacement / denominator if denominator else 0,
            'font_size': textstate.fontsize, 'render_mode': textstate.render,
            'scaling': textstate.scaling, 'rise': textstate.rise,
            'vertical': textstate.font.is_vertical(),
            'color_space': ncs.name,
            'color': _rgb(graphicstate.ncolor),
        })


def _check_page(page, page_number):
    if page.rotation % 360:
        raise ValueError(f'Page {page_number}: rotated page (rotation={page.rotation}) unsupported; normalize its rotation first')
    media, crop = list(page.mediabox), list(page.cropbox)
    if media != crop or abs(float(media[0])) > 1e-6 or abs(float(media[1])) > 1e-6:
        raise ValueError(f'Page {page_number}: cropped/nonzero-origin page unsupported; normalize page boxes first')
    if float(page.get('/UserUnit', 1)) != 1:
        raise ValueError(f'Page {page_number}: nonstandard UserUnit unsupported')
    # Form streams have independent text state and may be reused several times.
    # Reject text-bearing forms rather than editing a shared object incorrectly.
    def inspect_forms(resources, seen):
        for obj in (resources or {}).get('/XObject', {}).values():
            obj = obj.get_object()
            if obj.get('/Subtype') != '/Form' or id(obj) in seen:
                continue
            seen.add(id(obj))
            stream = ContentStream(obj, page.pdf)
            if any(op in _SHOW for _, op in stream.operations):
                raise ValueError(f'Page {page_number}: native text in nested Form XObject unsupported; obtain normalized editable source')
            inspect_forms(obj.get('/Resources', resources), seen)
    inspect_forms(page.get('/Resources', {}), set())


def _extract_operation_pages(pdf_path):
    """Extract all visible native text operations, with source style and geometry."""
    reader = PdfReader(str(pdf_path))
    for n, page in enumerate(reader.pages, 1):
        _check_page(page, n)
    manager = PDFResourceManager()
    device = _OperationDevice(manager)
    interpreter = PDFPageInterpreter(manager, device)
    pages = []
    with open(pdf_path, 'rb') as source:
        for n, miner_page in enumerate(PDFPage.get_pages(source), 1):
            device.records, device.glyphs = [], []
            interpreter.process_page(miner_page)
            page = reader.pages[n - 1]
            width, height = float(page.mediabox.width), float(page.mediabox.height)
            content = page.get_contents()
            operations = content.operations if content is not None else []
            show_indices = [i for i, (_, op) in enumerate(operations) if op in _SHOW]
            if len(show_indices) != len(device.records):
                raise ValueError(f'Page {n}: cannot map native text safely to content operators')
            items = []
            for op_index, record in zip(show_indices, device.records):
                chars = record['glyphs']
                if not chars:
                    continue
                source_text = ''.join(c.get_text() for c in chars)
                matrix = chars[0].matrix
                baseline_scale = math.hypot(matrix[0], matrix[1])
                direction = [matrix[0] / baseline_scale, -matrix[1] / baseline_scale] if baseline_scale else [0, 0]
                bbox = [min(c.x0 for c in chars), height - max(c.y1 for c in chars), max(c.x1 for c in chars), height - min(c.y0 for c in chars)]
                item_id = f'p{n:04d}-t{len(items)+1:04d}'
                flags = (16 if 'bold' in chars[0].fontname.lower() else 0) | (2 if any(s in chars[0].fontname.lower() for s in ('italic', 'oblique')) else 0)
                layout = {
                    'bbox': [round(v, 6) for v in bbox],
                    'origin': [round(matrix[4], 6), round(height-matrix[5], 6)],
                    'font_size': round(record['font_size'] * baseline_scale, 6),
                    'font': chars[0].fontname, 'color': record['color'],
                    'flags': flags, 'direction': [round(v, 6) for v in direction],
                    'operation_index': op_index,
                    'advance_adjustment': record['advance_adjustment'],
                    'render_mode': record['render_mode'],
                    'scaling': record['scaling'], 'rise': record['rise'],
                    'matrix': [round(v, 6) for v in matrix[:4]],
                    'vertical': record['vertical'], 'color_space': record['color_space'],
                }
                items.append({'id': item_id, 'source': source_text, 'layout': layout,
                              'unreadable': '(cid:' in source_text or '\ufffd' in source_text or '\x00' in source_text})
            pages.append({'page': n, 'width': width, 'height': height, 'items': items,
                          'content_sha256': hashlib.sha256(content.get_data() if content is not None else b'').hexdigest()})
    return pages


def _finite_numbers(values, count):
    return isinstance(values, (list, tuple)) and len(values) == count and all(isinstance(v, (int, float)) and math.isfinite(v) for v in values)


def _validate_layout(layout, item_id, width, height):
    if not isinstance(layout, dict) or not _finite_numbers(layout.get('bbox'), 4):
        raise ValueError(f'{item_id}: invalid layout bbox')
    x0, y0, x1, y1 = layout['bbox']
    if not (0 <= x0 < x1 <= width + .01 and 0 <= y0 < y1 <= height + .01):
        raise ValueError(f'{item_id}: invalid/out-of-page layout bbox')
    size = layout.get('font_size')
    if not isinstance(size, (int, float)) or not math.isfinite(size) or size <= 0:
        raise ValueError(f'{item_id}: invalid font_size')
    if not _finite_numbers(layout.get('color'), 3) or any(v < 0 or v > 1 for v in layout['color']):
        raise ValueError(f'{item_id}: invalid RGB color')
    if not _finite_numbers(layout.get('origin'), 2):
        raise ValueError(f'{item_id}: invalid layout origin')


def _font(font_path):
    font_path = Path(font_path)
    if not font_path.is_file():
        raise ValueError(f'Chinese fallback font does not exist: {font_path}')
    name = 'SlideTranslation_' + hashlib.sha256(str(font_path).encode()).hexdigest()[:12]
    if name not in pdfmetrics.getRegisteredFontNames():
        try:
            pdfmetrics.registerFont(TTFont(name, str(font_path)))
        except Exception as exc:
            raise ValueError(f'Cannot use Chinese font {font_path}: {exc}') from exc
    return name


def _choose_font(original_font, zh, fallback):
    # Reuse PDF standard fonts when they cover the actual replacement text.
    base = original_font.split('+')[-1]
    if base in pdfmetrics.standardFonts and all(ord(c) < 128 for c in zh):
        return base
    return fallback


def _check_fit(zh, layout, font, item_id, synthesized_styles=False):
    if not isinstance(zh, str) or not zh.strip():
        raise ValueError(f'{item_id}: empty translation')
    if '\n' in zh or '\r' in zh:
        raise ValueError(f'{item_id}: multiline translation cannot fit single native text operation; rewrite compactly')
    face = pdfmetrics.getFont(font).face
    cmap = getattr(face, 'charToGlyph', None)
    if cmap is not None and any(ord(ch) not in cmap for ch in zh):
        raise ValueError(f'{item_id}: fallback font lacks required glyphs')
    text_width = pdfmetrics.stringWidth(zh, font, layout['font_size'])
    if synthesized_styles:
        text_width += layout['font_size'] * (.22 if layout.get('flags',0) & 2 else 0)
        text_width += layout['font_size'] * (.025 if layout.get('flags',0) & 16 else 0)
    x0, _, x1, _ = layout['bbox']
    if layout['origin'][0] + text_width > x1 + .05 or layout['origin'][0] < x0 - .05:
        raise ValueError(f'{item_id}: translation overflow; needs {text_width:.2f} pt at original {layout["font_size"]} pt, region width {x1-x0:.2f} pt. Supply a faithful shorter translation or explicitly approve a layout change')


def render_translated(original_pdf, manifest, results, output_pdf, font_path):
    """Create Chinese pages or raise ValueError before writing on any unsafe item.

    Native source glyph operators are replaced by numeric TJ advances. The
    original source image objects and vector drawing operators remain intact.
    Raster annotations require a human-verified solid background and are reported
    separately as approximations. No text resizing or region widening is used.
    """
    if Path(original_pdf).resolve() == Path(output_pdf).resolve():
        raise ValueError('Output must not overwrite original PDF')
    actual_pages = extract_pages(original_pdf, backend=manifest.get('text_backend','auto'))
    if any(p.get('backend') == 'mupdf' for p in actual_pages):
        return _render_mupdf(original_pdf, manifest, results, output_pdf, font_path, actual_pages)
    pages = manifest.get('pages', [])
    if len(pages) != len(actual_pages):
        raise ValueError('Manifest page count differs from original PDF')
    reader = PdfReader(str(original_pdf))
    writer = PdfWriter()
    fallback = _font(font_path)
    report = {'pages': len(pages), 'translated_items': 0, 'preserved_items': 0,
              'font_substitutions': [], 'raster_replacements': [], 'unreadable_items': [],
              'method': 'native text-show strings replaced by position-preserving numeric TJ; original graphics reused',
              'limitations': ['Replacement glyphs are appended in an overlay; review stacking against overlapping source artwork.', 'Embedded subset fonts are not reconstructed; available standard fonts or the specified CJK font are used.']}
    for expected, actual in zip(pages, actual_pages):
        n = actual['page']
        if expected.get('page') != n or expected.get('width') != actual['width'] or expected.get('height') != actual['height']:
            raise ValueError(f'Page {n}: manifest page geometry differs from source')
        if expected.get('content_sha256', actual['content_sha256']) != actual['content_sha256']:
            raise ValueError(f'Page {n}: manifest source content changed; re-prepare')
        if len(expected.get('items', [])) != len(actual['items']):
            raise ValueError(f'Page {n}: native item coverage differs from source')
        responses = results.get(n, results.get(str(n), {}))
        translated = responses.get('items', [])
        by_id = {item.get('id'): item for item in translated}
        if len(by_id) != len(translated) or set(by_id) != {i['id'] for i in actual['items']}:
            raise ValueError(f'Page {n}: missing, duplicate or extra native translation IDs')
        replacements = {}
        overlays = []
        for supplied, item in zip(expected['items'], actual['items']):
            ident, layout = item['id'], item['layout']
            if supplied.get('id') != ident or supplied.get('source') != item['source'] or supplied.get('layout') != layout:
                raise ValueError(f'{ident}: manifest source/layout geometry differs from original PDF; re-prepare')
            if item['unreadable']:
                report['unreadable_items'].append(ident)
                raise ValueError(f'{ident}: unreadable native glyphs; manual source review and a safe editable source are required')
            response = by_id[ident]
            zh = response.get('zh')
            if zh == item['source'] or response.get('status') == 'preserved':
                report['preserved_items'] += 1
                continue
            _validate_layout(layout, ident, actual['width'], actual['height'])
            a, b, c, d = layout['matrix']
            if layout['vertical'] or abs(b) > 1e-6 or abs(c) > 1e-6 or a <= 0 or abs(a-d) > 1e-6 or layout['scaling'] != 100 or layout['rise'] != 0:
                raise ValueError(f'{ident}: rotated/skewed/scaled or raised native text unsupported; normalize source')
            if layout['render_mode'] != 0 or layout['color_space'] not in ('DeviceRGB', 'DeviceGray', 'DeviceCMYK'):
                raise ValueError(f'{ident}: unsupported native rendering mode/color space')
            font = _choose_font(layout['font'], zh, fallback)
            _check_fit(zh, layout, font, ident, synthesized_styles=font==fallback)
            if font == fallback:
                report['font_substitutions'].append({'id': ident, 'original_font': layout['font'], 'replacement_font': str(font_path), 'font_size': layout['font_size'], 'color': layout['color'], 'original_flags': layout['flags'], 'synthesized_styles': (['bold'] if layout['flags'] & 16 else []) + (['italic'] if layout['flags'] & 2 else []), 'note': 'Fallback glyph metrics may differ; original emphasis is synthesized when needed; source size, baseline and color retained'})
            replacements[layout['operation_index']] = layout['advance_adjustment']
            overlays.append((zh, layout, font, None))
            report['translated_items'] += 1
        notes = responses.get('notes', responses.get('figure_notes', []))
        for index, note in enumerate(notes):
            ident = note.get('id', f'p{n:04d}-figure-{index+1}')
            if note.get('status') == 'preserved' or note.get('zh') == note.get('source'):
                continue
            layout = dict(note.get('layout') or {})
            background = layout.get('background_color')
            if layout.get('background_verified') is not True or not _finite_numbers(background, 3) or any(v < 0 or v > 1 for v in background):
                raise ValueError(f'{ident}: raster figure replacement requires an explicitly verified solid background_color; complex backgrounds cannot be safely erased')
            if 'origin' not in layout and _finite_numbers(layout.get('bbox'), 4) and isinstance(layout.get('font_size'), (int,float)):
                layout['origin'] = [layout['bbox'][0], layout['bbox'][1] + layout['font_size']]
            _validate_layout(layout, ident, actual['width'], actual['height'])
            x0,y0,x1,y1 = layout['bbox']
            for native in actual['items']:
                u0,v0,u1,v1 = native['layout']['bbox']
                if x0 < u1 and x1 > u0 and y0 < v1 and y1 > v0:
                    raise ValueError(f'{ident}: raster background overlaps native text {native["id"]}; unsafe replacement')
            _check_fit(note.get('zh'), layout, fallback, ident)
            if layout['origin'][1] > y1 or layout['origin'][1] - layout['font_size'] < y0 - .01:
                raise ValueError(f'{ident}: raster translation cannot fit vertical region')
            overlays.append((note['zh'], layout, fallback, background))
            report['raster_replacements'].append({'id': ident, 'page': n, 'bbox': layout['bbox'], 'approximation': 'Human-verified solid-background cover; font/size estimated from raster source'})
        page = writer.add_page(reader.pages[n-1])
        content = page.get_contents()
        clip_bounds = _source_constraints(page, n) if overlays else None
        if replacements:
            operations = []
            for index, (operands, operator) in enumerate(content.operations):
                if index not in replacements:
                    operations.append((operands, operator))
                    continue
                if operator == b"'":
                    operations.append(([], b'T*'))
                elif operator == b'"':
                    operations.extend([([operands[0]], b'Tw'), ([operands[1]], b'Tc'), ([], b'T*')])
                operations.append(([ArrayObject([FloatObject(replacements[index])])], b'TJ'))
            content.operations = operations
            page.replace_contents(content)
        if overlays:
            buffer = io.BytesIO()
            overlay = canvas.Canvas(buffer, pagesize=(actual['width'], actual['height']))
            if clip_bounds is not None:
                x0,y0,x1,y1=clip_bounds
                path=overlay.beginPath();path.rect(x0,y0,x1-x0,y1-y0)
                overlay.clipPath(path,stroke=0)
            for zh, layout, font, background in overlays:
                overlay.saveState()
                if background is not None:
                    x0,y0,x1,y1=layout['bbox']
                    overlay.setFillColorRGB(*background)
                    overlay.rect(x0, actual['height']-y1, x1-x0, y1-y0, fill=1, stroke=0)
                overlay.setFillColorRGB(*layout['color'])
                overlay.setFont(font, layout['font_size'])
                if font == fallback and layout.get('flags', 0) & 18:
                    text = overlay.beginText()
                    text.setFont(font, layout['font_size'])
                    text.setTextTransform(1, 0, .22 if layout.get('flags', 0) & 2 else 0, 1, layout['origin'][0], actual['height']-layout['origin'][1])
                    if layout.get('flags', 0) & 16:
                        overlay.setStrokeColorRGB(*layout['color'])
                        overlay.setLineWidth(max(.15, layout['font_size'] * .025))
                        text.setTextRenderMode(2)
                    text.textOut(zh)
                    overlay.drawText(text)
                else:
                    overlay.drawString(layout['origin'][0], actual['height']-layout['origin'][1], zh)
                overlay.restoreState()
            overlay.save()
            buffer.seek(0)
            page.merge_page(PdfReader(buffer).pages[0])
    destination = Path(output_pdf)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('wb') as target:
        writer.write(target)
    return report


def _mupdf():
    try:
        import pymupdf
        return pymupdf
    except ImportError as exc:
        raise ValueError('PyMuPDF is required for rotated/cropped pages and text-bearing Form XObjects. Install the declared dependency; no automatic download is performed.') from exc


def _normalized_document(pdf_path):
    fitz = _mupdf()
    document = fitz.open(str(pdf_path))
    for page in document:
        if page.rotation:
            page.remove_rotation()
    return document


def _extract_mupdf(pdf_path):
    fitz = _mupdf()
    digest = hashlib.sha256(Path(pdf_path).read_bytes()).hexdigest()
    pages = []
    with _normalized_document(pdf_path) as document:
        for page in document:
            items = []
            raw = page.get_text('dict', flags=fitz.TEXT_PRESERVE_WHITESPACE)
            for block in raw['blocks']:
                if block['type'] != 0:
                    continue
                for line in block['lines']:
                    for span in line['spans']:
                        source = span['text']
                        if not source.strip():
                            continue
                        color = span['color']
                        layout = {
                            'bbox': [round(v,6) for v in span['bbox']],
                            'origin': [round(v,6) for v in span['origin']],
                            'font_size': round(span['size'],6), 'font': span['font'],
                            'color': [round(((color >> shift) & 255)/255,6) for shift in (16,8,0)],
                            'flags': span['flags'], 'direction': [round(v,6) for v in line['dir']],
                            'alpha': span.get('alpha',255),
                            'ascender': span.get('ascender'), 'descender': span.get('descender'),
                        }
                        items.append({'id':f'p{page.number+1:04d}-t{len(items)+1:04d}', 'source':source, 'layout':layout,
                                      'unreadable':'\ufffd' in source or '\x00' in source or '(cid:' in source})
            pages.append({'page':page.number+1,'width':round(page.rect.width,6),'height':round(page.rect.height,6),
                          'items':items,'backend':'mupdf','content_sha256':digest})
    return pages


def extract_pages(pdf_path, backend="auto"):
    """Use exact PDF operations normally; MuPDF normalizes complex page geometry."""
    if backend == "mupdf":
        return _extract_mupdf(pdf_path)
    try:
        return _extract_operation_pages(pdf_path)
    except ValueError as exc:
        if not any(term in str(exc) for term in ('rotated page','cropped/nonzero-origin','Form XObject','UserUnit')):
            raise
        return _extract_mupdf(pdf_path)


def _render_mupdf(original_pdf, manifest, results, output_pdf, font_path, actual_pages):
    fitz = _mupdf()
    expected_pages = manifest.get('pages',[])
    if len(expected_pages) != len(actual_pages):
        raise ValueError('Manifest page count differs from original PDF')
    if not Path(font_path).is_file():
        raise ValueError(f'Chinese fallback font does not exist: {font_path}')
    fallback = fitz.Font(fontfile=str(font_path))
    report = {'pages':len(actual_pages), 'translated_items':0,'preserved_items':0,
              'font_substitutions':[],'raster_replacements':[],'unreadable_items':[],
              'method':'PyMuPDF rotation normalization and native TEXT ONLY redaction (images=0, graphics=0, fill=False)',
              'limitations':['Replacements are appended over original artwork; inspect stacking and nearby annotations.', 'Raster regions use verified solid backgrounds or explicitly authorized local background covers; image text fonts are estimated.']}
    source_reader=PdfReader(str(original_pdf))
    with _normalized_document(original_pdf) as document:
        for expected, actual, page in zip(expected_pages,actual_pages,document):
            n=actual['page']
            for key in ('page','width','height','content_sha256'):
                if expected.get(key,actual[key]) != actual[key]:
                    raise ValueError(f'Page {n}: manifest source/layout {key} changed; re-prepare')
            if len(expected.get('items',[])) != len(actual['items']):
                raise ValueError(f'Page {n}: native item coverage differs from source')
            responses=results.get(n,results.get(str(n),{}))
            items=responses.get('items',[])
            by_id={i.get('id'):i for i in items}
            if len(by_id)!=len(items) or set(by_id)!={i['id'] for i in actual['items']}:
                raise ValueError(f'Page {n}: missing, duplicate or extra native translation IDs')
            edits=[]
            preserved=[]
            for supplied,item in zip(expected['items'],actual['items']):
                ident=item['id']; layout=item['layout']; response=by_id[ident]
                if any(supplied.get(k)!=item[k] for k in ('id','source','layout')):
                    raise ValueError(f'{ident}: manifest source/layout geometry differs from original PDF')
                if item['unreadable']:
                    raise ValueError(f'{ident}: unreadable native glyphs; manual source review required')
                zh=response.get('zh')
                if zh==item['source'] or response.get('status')=='preserved':
                    preserved.append(item);report['preserved_items']+=1;continue
                _validate_layout(layout,ident,actual['width'],actual['height'])
                direction=layout['direction']
                rotations={(1,0):0,(0,-1):90,(-1,0):180,(0,1):270}
                if tuple(direction) not in rotations:
                    raise ValueError(f'{ident}: nonorthogonal rotated text unsupported; normalize source')
                rotation=rotations[tuple(direction)]
                if not isinstance(zh,str) or not zh.strip() or '\n' in zh or '\r' in zh:
                    raise ValueError(f'{ident}: empty or multiline text cannot fit source span')
                # Reuse an embedded original font only if it covers every new glyph.
                chosen=fallback; font_buffer=None
                for info in page.get_fonts(full=True):
                    basename=info[3].split('+')[-1].replace(' ','').lower()
                    if basename!=layout['font'].split('+')[-1].replace(' ','').lower():
                        continue
                    try:
                        buffer=document.extract_font(info[0])[3]
                        candidate=fitz.Font(fontbuffer=buffer) if buffer else None
                        if candidate and all(candidate.has_glyph(ord(ch)) for ch in zh):
                            chosen=candidate;font_buffer=buffer;break
                    except (RuntimeError,ValueError):
                        pass
                if not all(chosen.has_glyph(ord(ch)) for ch in zh):
                    raise ValueError(f'{ident}: fallback font lacks required glyphs')
                rect=fitz.Rect(layout['bbox'])
                available=rect.width if rotation in (0,180) else rect.height
                length=chosen.text_length(zh,fontsize=layout['font_size'])
                if font_buffer is None:
                    length += layout['font_size'] * (.22 if layout['flags'] & 2 else 0)
                    length += layout['font_size'] * (.025 if layout['flags'] & 16 else 0)
                if length > available + .05:
                    raise ValueError(f'{ident}: translation overflow; needs {length:.2f} pt at original {layout["font_size"]} pt, region {available:.2f} pt')
                if font_buffer is None:
                    report['font_substitutions'].append({'id':ident,'original_font':layout['font'],'replacement_font':str(font_path),
                        'font_size':layout['font_size'],'color':layout['color'],'original_flags':layout['flags'],
                        'synthesized_styles':(['bold'] if layout['flags'] & 16 else [])+(['italic'] if layout['flags'] & 2 else []), 'note':'Source font unavailable for Chinese; fallback at original baseline/size/color; emphasis synthesized when required'})
                edits.append((item,zh,rotation,font_buffer))
                report['translated_items']+=1
            # A redaction removes any intersecting glyph, so protect entire preserved
            # spans conservatively. This also catches duplicate overlapping labels.
            for item,_,_,_ in edits:
                target=fitz.Rect(item['layout']['bbox'])
                for untouched in preserved:
                    overlap=target & fitz.Rect(untouched['layout']['bbox'])
                    if not overlap.is_empty and overlap.width>.01 and overlap.height>.01:
                        raise ValueError(f'{item["id"]}: text-only redaction overlaps preserved text {untouched["id"]}; safe replacement requires editable source')
            raster=[]
            for index,note in enumerate(responses.get('notes',responses.get('figure_notes',[]))):
                ident=note.get('id',f'p{n:04d}-figure-{index+1}')
                if note.get('status')=='preserved' or note.get('zh')==note.get('source'):
                    continue
                layout=dict(note.get('layout') or {});background=layout.get('background_color')
                if not (layout.get('background_verified') is True or layout.get('background_change_authorized') is True) or not _finite_numbers(background,3) or any(v<0 or v>1 for v in background):
                    raise ValueError(f'{ident}: raster figure requires explicitly verified solid background_color')
                if 'origin' not in layout and _finite_numbers(layout.get('bbox'),4) and isinstance(layout.get('font_size'),(int,float)):
                    layout['origin']=[layout['bbox'][0],layout['bbox'][1]+layout['font_size']]
                _validate_layout(layout,ident,actual['width'],actual['height'])
                rotation=layout.get('rotation',0)
                if rotation not in (0,90,180,270):raise ValueError(f'{ident}: invalid raster text rotation')
                fit_layout=layout
                if rotation in (90,270):
                    x0,y0,x1,y1=layout['bbox'];fit_layout=dict(layout,bbox=[0,0,y1-y0,x1-x0],origin=[0,layout['font_size']])
                _check_fit(note.get('zh'),fit_layout,_font(font_path),ident)
                rect=fitz.Rect(layout['bbox'])
                if any(not (rect & fitz.Rect(i['layout']['bbox'])).is_empty for i in actual['items']):
                    raise ValueError(f'{ident}: raster background overlaps native text; unsafe replacement')
                raster.append((ident,note['zh'],layout,background))
            if edits or raster:
                _source_constraints(source_reader.pages[n-1],n)
            for item,_,_,_ in edits:
                page.add_redact_annot(fitz.Rect(item['layout']['bbox']),fill=False,cross_out=False)
            if edits:
                page.apply_redactions(images=0,graphics=0,text=0)
            for index,(item,zh,rotation,font_buffer) in enumerate(edits):
                layout=item['layout'];name=f'SlideCJK{index}'
                if font_buffer is None:
                    page.insert_font(fontname=name,fontfile=str(font_path))
                else:
                    page.insert_font(fontname=name,fontbuffer=font_buffer)
                kwargs={}
                if font_buffer is None and layout['flags'] & 16:
                    kwargs.update(render_mode=2,border_width=.025,fill=layout['color'])
                if font_buffer is None and layout['flags'] & 2:
                    dx,dy=layout['direction'];k=.22
                    kwargs['morph']=(fitz.Point(layout['origin']),fitz.Matrix(1+k*dx*dy,k*dy*dy,-k*dx*dx,1-k*dx*dy,0,0))
                page.insert_text(fitz.Point(layout['origin']),zh,fontname=name,fontsize=layout['font_size'],
                    color=layout['color'],rotate=rotation,fill_opacity=layout.get('alpha',255)/255,
                    stroke_opacity=layout.get('alpha',255)/255,**kwargs)
            for index,(ident,zh,layout,background) in enumerate(raster):
                page.draw_rect(fitz.Rect(layout['bbox']),color=None,fill=background,overlay=True)
                name=f'RasterCJK{index}';page.insert_font(fontname=name,fontfile=str(font_path))
                page.insert_text(fitz.Point(layout['origin']),zh,fontname=name,fontsize=layout['font_size'],color=layout['color'],rotate=layout.get('rotation',0))
                report['raster_replacements'].append({'id':ident,'page':n,'bbox':layout['bbox'],'approximation':('User-authorized local background cover; font metrics estimated' if layout.get('background_change_authorized') else 'Human-verified solid background cover; font metrics estimated')})
        destination=Path(output_pdf);destination.parent.mkdir(parents=True,exist_ok=True)
        document.save(str(destination),garbage=3,deflate=True)
    return report


def _source_constraints(page, number):
    """Validate overlay-sensitive source state, including nested Form streams.

    A single axis-aligned page rectangle may differ by <=0.1 pt from the CropBox
    because Office rounds PDF coordinates. Its exact bounds are returned so the
    ordinary overlay can inherit the same clipping. Other clips are rejected.
    """
    visible = [float(v) for v in page.cropbox]
    page_clip = list(visible)
    def resolved(value):
        return value.get_object() if hasattr(value,'get_object') else value
    def compose(outer, inner):
        a,b,c,d,e,f=outer; A,B,C,D,E,F=inner
        return (a*A+c*B,b*A+d*B,a*C+c*D,b*C+d*D,a*E+c*F+e,b*E+d*F+f)
    def rectangle(values, matrix):
        x,y,w,h=map(float,values);a,b,c,d,e,f=matrix
        points=[(a*u+c*v+e,b*u+d*v+f) for u,v in ((x,y),(x+w,y),(x+w,y+h),(x,y+h))]
        xs={round(p[0],5) for p in points};ys={round(p[1],5) for p in points}
        if len(xs)!=2 or len(ys)!=2:
            return None
        return [min(xs),min(ys),max(xs),max(ys)]
    def check_clip(bounds):
        if bounds is None or any((bounds[i]-visible[i])*(1 if i<2 else -1)>.1 for i in range(4)):
            raise ValueError(f'Page {number}: restrictive/nonrectangular clipping cannot be reproduced safely on translated text; normalize editable source')
        page_clip[:]=[max(page_clip[0],bounds[0]),max(page_clip[1],bounds[1]),min(page_clip[2],bounds[2]),min(page_clip[3],bounds[3])]
    def walk(stream,resources,matrix,render,ancestry,clips):
        resources=resolved(resources or {})
        stack=[];path=[];nonrectangular=False
        for args,op in stream.operations:
            if op==b'q':
                stack.append((matrix,render,list(clips)))
            elif op==b'Q':
                if stack: matrix,render,clips=stack.pop()
            elif op==b'cm':
                matrix=compose(matrix,tuple(map(float,args)))
            elif op==b'Tr':
                render=int(args[0])
            elif op in _SHOW:
                if render!=0:
                    raise ValueError(f'Page {number}: unsupported native text rendering mode {render}; preserve an editable source')
                for active_clip in clips:
                    check_clip(active_clip)
            elif op==b're':
                path.append(rectangle(args,matrix))
            elif op in (b'm',b'l',b'c',b'v',b'y'):
                nonrectangular=True
            elif op in (b'W',b'W*'):
                clips.append(path[0] if len(path)==1 and not nonrectangular else None)
            elif op in (b'n',b'S',b's',b'f',b'F',b'f*',b'B',b'B*',b'b',b'b*'):
                path=[];nonrectangular=False
            elif op==b'gs':
                states=resolved(resources.get('/ExtGState',{}))
                state=resolved(states.get(args[0],{}))
                if float(state.get('/ca',1))!=1 or float(state.get('/CA',1))!=1 or state.get('/BM','/Normal') not in ('/Normal','/Compatible') or state.get('/SMask','/None')!='/None':
                    raise ValueError(f'Page {number}: unsupported graphics-state opacity/blending for translated text')
            elif op==b'Do':
                objects=resolved(resources.get('/XObject',{}));obj=resolved(objects.get(args[0],{}))
                if obj.get('/Subtype')!='/Form': continue
                identity=id(obj)
                if identity in ancestry:
                    raise ValueError(f'Page {number}: recursive Form XObject unsupported')
                form_matrix=compose(matrix,tuple(map(float,obj.get('/Matrix',[1,0,0,1,0,0]))))
                # A Form BBox is itself an implicit clip. Only page-wide forms can
                # be safely overlaid without recreating that clipping hierarchy.
                form_clips=list(clips)
                if '/BBox' in obj:
                    x0,y0,x1,y1=map(float,obj['/BBox'])
                    form_clips.append(rectangle((x0,y0,x1-x0,y1-y0),form_matrix))
                walk(ContentStream(obj,page.pdf),obj.get('/Resources',resources),form_matrix,render,ancestry|{identity},form_clips)
    content=page.get_contents()
    if content is not None:
        walk(content,page.get('/Resources',{}),(1,0,0,1,0,0),0,set(),[])
    return page_clip
