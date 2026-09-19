# 执行接口与能力边界

## 运行环境

使用 Python 3.10+ 和 `scripts/requirements.txt` 中的依赖：pypdf、pdfplumber、ReportLab、Pillow，以及处理复杂 PDF 页面的 PyMuPDF（本版验证基线为 1.28.2）。三个执行模块 `slide_translate.py`、`three_column.py`、`layout_translation.py` 必须位于同一目录；不要只复制入口脚本。

已有可用环境不重复安装。在 Codex 中可用工作区依赖工具查找随应用提供的 Python、字体和 LibreOffice；必要时通过 `--soffice /实际路径/soffice` 指定转换器。不要把开发机器的绝对路径写成通用依赖。

PDF 直接复制为任务内的 `original.pdf`。PPT/PPTX 等 Office 输入先经本机或运行环境提供的 LibreOffice 导出 PDF；核对字体、公式、隐藏页、动画静态化及页序。当前不编辑 PPTX 的 shape/run，不交付可编辑中文 PPTX。其他格式先由原应用导出，再用 `--normalized-pdf` 接入；链接需先用已授权方式取得文件，脚本不抓取网页。

图片目录按文件名自然排序，多帧 TIFF 保持帧序。`--ocr` 需本机 Tesseract，仅帮助识读没有原生文字的页；OCR 不创建可信的原位文字对象或自动擦除区域。schema v2 的可替换对象来自原生 PDF 几何抽取，扫描字仍需看图并人工提交位置。

## 默认流程与真实 CLI

```bash
python "SKILL/scripts/slide_translate.py" prepare "课件.pdf" --work "job"
# 查看原页与上下文，按批填写 job/responses/<chunk_id>.json。
python "SKILL/scripts/slide_translate.py" validate --work "job" --partial
# 全部响应齐全后：
python "SKILL/scripts/slide_translate.py" validate --work "job"
python "SKILL/scripts/slide_translate.py" audit --work "job"
python "SKILL/scripts/slide_translate.py" build --work "job" --output "三栏学习资料.pdf"
python "SKILL/scripts/slide_translate.py" verify --work "job"
```

`SKILL` 替换为实际技能目录。默认 `prepare` 等同 `--layout three-column`，生成 schema v2。明确选择历史双栏时，创建新任务并加 `--layout two-column`；后续命令依 manifest 版本自动路由，不能在 `build` 时切换布局，也不能把旧响应当作 v2 响应。

| 命令 | 参数与用途 |
|---|---|
| `prepare INPUT --work JOB` | 可加 `--normalized-pdf`、`--soffice`、`--labels`、`--glossary`、`--chunk-chars`（默认 1400）、`--dpi`（默认 130）、`--ocr`、`--ocr-lang`（默认 eng）、`--layout`、`--text-backend auto/mupdf`、`--exam-syllabus` |
| `validate --work JOB` | `--partial` 检查已完成批次并报告剩余批次；完整校验检查全部覆盖 |
| `audit --work JOB` | 完整校验后检查译文中的部分英文残留和类型问题，生成质量报告 |
| `build --work JOB --output RESULT.pdf` | 完整校验、审查并生成三栏；`--font` 指定覆盖目标字符的 TrueType 字体，`--force` 允许替换已有结果 |
| `verify --work JOB` | 核验最终 PDF 哈希和页数，生成全部缩略图；`--pages 2,5` 额外渲染指定输出页 |

`validate/audit/build` 保留兼容参数 `--allow-unreviewed-images`，但 **schema v2 不允许豁免真实看图**。没有 `--layout` 之外的自由画布、改字号、移动文本框或插入外部配图参数。`--exam-syllabus` 接收非空 UTF-8 文本文件，不直接解析考纲 PDF。

`prepare` 不覆盖非空工作目录；续做时复用原任务和正确响应。源 PDF 的 SHA-256 是 `document_id`，实际文件页序是唯一对应依据，印刷页码仅作标签。请求、几何和考纲都有一致性检查；不要编辑 manifest 或请求来掩盖错误，源文件变化时创建新任务。

## 源文字与响应映射

任务包含 `original.pdf`、逐页图片、`manifest.json`、`deck-context.json`、`requests/`、`prompts/`、`responses/`。每页第一批也承载本页教学内容；课件上下文可在 `deck-context.json` 中查看。

原生文字条目包含 `id/source/layout/unreadable`，`layout` 记录坐标、基线、字号、字体、颜色等抽取证据。通常一个 ID 对应一个 PDF 文字显示操作；PyMuPDF 路径中对应文字 span。它们不是重新识别的完整段落，不能假定一条就是一句。模型要结合前后条目理解完整段落，但按原 ID 返回，不能合并或拆分源对象。`--chunk-chars` 是分批参考阈值，不拆开单个文字对象。

下面是每页第一批的响应结构示例。身份、ID 和源页号均须替换为请求的真实值；示例内容不应照抄到无关课件。

```json
{
  "document_id": "复制请求中的 document_id",
  "chunk_id": "p0001-c001",
  "visual_review": "reviewed",
  "items": [
    {
      "id": "p0001-t0001",
      "zh": "信号",
      "role": "title",
      "status": "translated"
    },
    {
      "id": "p0001-t0002",
      "zh": "已有中文",
      "role": "body",
      "status": "preserved",
      "preserve_reason": "chinese"
    }
  ],
  "figure_notes": [],
  "study": {
    "mode": "outline",
    "page_kind": "content",
    "points": [
      {
        "kind": "short_answer",
        "title": "短答｜处理器分工",
        "question_zh": "CPU的作用是什么？",
        "question_en": "What is the role of the CPU?",
        "answer_zh": "协调应用运行。",
        "answer_en": "Coordination.",
        "source_pages": [
          1
        ]
      }
    ]
  }
}
```

- `items` 必须完整且恰好一次覆盖本批 ID。`zh` 非空；角色用 `title/heading/body/bullet/caption/footnote`。角色是内容标记，不改变源字号或位置；表格按原对象逐条译，不用旧 `table/rows` 重排。
- `status` 用 `translated` 或 `preserved`。`preserved` 必须与源文字完全相同，并有 `preserve_reason: chinese/notation/code/name/url`；仅适用于本来不需要翻译的中文、符号、代码、名称或网址，不能豁免未译自然语言。含外文的混合段落需译出外文并保护已有中文、数字和公式。
- 原生条目不得提交 `layout`、`retained_terms`、`table_ref`、`join_previous`、`diagram`、`rows`。不要照抄请求中的整个对象；布局由源记录决定。
- `unreadable` 状态不能导出；无法辨认的原生字形也会阻止原位制作。只有真实查看原图才可写 `reviewed`；`unavailable` 记录的是未完成状态，不通过 v2 校验。
- 每页第一批必须提交 `study`，且只有它可以提交 `figure_notes`。后续批次使用 `study: null` 和 `figure_notes: []`。

## study：默认精简复习提纲

每页第一批使用 `mode: "outline"`，`page_kind` 为 `content/title/transition/references/blank`；`points` 为列表。后续批次仍为 `study: null`。

- `points: []` 表示第三栏完全留空；脚本不打印栏目标题、说明或占位句，也不丢失该源页。
- 普通条目包含 `kind: structure/term/distinction`、可选 `title`、非空 `answer` 和 `source_pages`。`answer` 可用换行写简短层次。为兼容旧精简数据，也接受 `kind: note` 或省略kind。
- `kind: short_answer` 包含可选 `title`、非空的 `question_zh/question_en/answer_zh/answer_en` 及 `source_pages`。四个语言字段必须齐全；脚本相邻打印中文题、英文题、中文答、英文答，不额外生成自测区。模型仍须核对两种语言语义一致。
- 来源页必须属于当前任务，保存在数据中；不自动逐条打印来源标签。第三栏按整份PPT规划，不强迫每页拥有相同类型或数量。
- 无考试证据不得写必考、官方考纲等。普通条目不强制双语，短答强制双语。

旧任务的 `objective/sections/self_test/exam` 结构仍可读取；它的必填字段及考纲逐字证据校验保持兼容。新任务不再用旧结构强迫每页生成学习目标、讲解和复习建议。

第三栏支持文字段落与问答，不提供额外图片或 `diagram` 接口。条目写法及取舍见[study-guide.md](study-guide.md)。

## 图中漏抽文字与无文字页

原插图直接复用原 PDF 内容，不下载、不重新生成。原生图标签若已出现在 `items`，按原生条目处理。未被抽出的栅格字在真实看图、确认纯色背景且不会遮挡图形后写入首批 `figure_notes`：

```json
{
  "source": "Signal",
  "zh": "信号",
  "role": "caption",
  "status": "translated",
  "layout": {
    "bbox": [40, 60, 120, 84],
    "font_size": 12,
    "color": [0, 0, 0],
    "background_color": [1, 1, 1],
    "background_verified": true
  }
}
```

坐标单位为 PDF 点，原点在对应源页左上角；`bbox` 为左、上、右、下，颜色为 0–1 RGB。可显式给 `origin: [x, y]`；省略时基线取 `[bbox.left, bbox.top + font_size]`。示例坐标仅说明结构，不能拿去覆盖实际课件。字体和字号来自栅格观察，属于近似，记录在版面报告中。PyMuPDF路径也接受 `background_change_authorized: true`，仅用于用户明确允许局部背景改动时，不得伪填 `background_verified`；须保护关键图形、数值和连线。支持 `rotation: 0/90/180/270` 的图中文字。与原生文字交叠的覆盖区域仍会被拒绝。

真正完全没有文字的页面仍需看图、提供 `study`，并在首批添加明确的确认，例如：

```json
{
  "source": "本页无文字",
  "zh": "本页无文字",
  "role": "caption",
  "status": "preserved",
  "no_text": true
}
```

该确认不能有 `layout`，不能替代扫描页或漏抽页上的真实文字翻译。程序不能通过这个布尔值证明整页无字，须由看图复核保证。

## 原位引擎与限制

常规 PDF 优先按文字显示操作删除待译原字并叠加中文，保留原图片和矢量操作。旋转页、裁切或非零页原点、带文字的 Form XObject 等复杂页面采用 PyMuPDF 后备路径；它归一化页旋转并仅移除原文字，保留图片和图形。后备路径不是任意 PDF 编辑保证：非正交旋转、无法解码的字形、不安全交叠及不支持的文字状态会明确失败，需要结合具体输入解决。

原字号、基线和颜色是受支持替换的基准。常规路径可复用覆盖目标字的标准 PDF 字体；后备路径会尝试复用可提取且覆盖目标字的原字体。不能满足时使用 `--font` 或自动找到的中文字体，记录 `font_substitutions`。ReportLab 字体需为其可加载的 TrueType 轮廓；并非所有 OTF/TTC 都可用。回退字形、字重、斜体和度量可能不同，不能宣称原字体完全还原。

已标记保留的中文、公式与其他无需翻译的对象不重新排字。混合语言同一文字对象中的保护内容由模型保持正确；程序不自动理解或证明公式语义。替换文字是叠加层，须检查原图遮挡顺序和附近标注。

严格检查原字号下的文字宽度，超出源区域就报出 ID、所需宽度和区域宽度；不自动缩小、不折行重排、不截断。还需视觉检查字形上下边界、重叠和复杂背景，不能把宽度检查当成全部版面验收。任何布局调整都需要另行具体处理，当前响应没有任意布局覆盖接口。

三栏画布固定为 1836 × 841.89 点，前两栏各在 650 点范围内等比缩放，第三栏文字宽 432 点。当前没有自定义纸张参数。只有第三栏续页；前两栏不会因讲解长度而拆分。

## 输出与验收

成功 `build` 保存中栏单页 PDF `translated.pdf`、`layout-report.json`、`build-report.json` 和指定最终 PDF。版面报告记录字体替换、栅格近似与限制；原位制作失败时记录 `status: blocked` 及具体错误。构建报告含源页/输出页数、续页映射、前两栏缩放、列区域和文件哈希。`--force` 不允许覆盖原始输入、外部提供的归一化源 PDF、`original.pdf` 或受保护的译后中间文件。

`validate` 检查身份、覆盖、来源、响应和考纲结构；`audit` 是有限的词法检查，不能判断完整句意、教学质量或图中漏译。`verify` 在 `qa/` 生成全部缩略图，并默认渲染首末页和知识点续页，额外页可用 `--pages` 指定。它不自动查看图像，报告中的视觉复核状态仍待人检查。

最终必须检查全部输出页和每处文字替换：原文完整、中文准确、源字号/位置/颜色与插图保留、没有裁切遮挡、第三栏解释准确且来源可回溯。逐项披露仍存在的字体或版面差异；测试与校验通过不能代替这些检查。

页面范围内的矩形裁切（如 LibreOffice 导出的页边界裁切）可保留；限制文字可见区域的局部裁切、不支持的文字渲染模式会被拒绝，包括 Form 内部的情况。
