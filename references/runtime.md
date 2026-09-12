# 执行端说明

## 环境

Python 3.10+，安装 `scripts/requirements.txt`。脚本不含模型 API，不发送网络请求，也不需要 API key；依赖安装本身可能联网。输入和译文均在执行端本地处理。

```bash
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows PowerShell 改用：.venv\Scripts\Activate.ps1
python -m pip install -r "SKILL/scripts/requirements.txt"
python "SKILL/scripts/slide_translate.py" --help
```

也可用已有的可用 Python 解释器，不必重建虚拟环境。Codex 本地可调用 load_workspace_dependencies 找到自带 Python。不得在提示词里固定开发者电脑路径。

## 输入兼容策略

| 输入 | 自动路径 | 没有转换器时 |
|---|---|---|
| PDF | 直接保留原页 | 加密文件用有权限的原应用导出未加密副本 |
| PPT/PPTX/ODP/PPS/PPSX/POT/POTX | 本机 LibreOffice 无界面导出 | PowerPoint/LibreOffice 导出 PDF |
| PNG/JPEG/TIFF/BMP/WebP | 原图嵌入 PDF | HEIC/其他图片先用原应用转 PNG 或 PDF |
| 图片文件夹 | 仅识别支持的图片，文件名自然排序 | 先按 001、002 等命名确认顺序；非图片文件不作为页 |
| Keynote/HTML/网页/Google Slides/其他 | 使用原应用 PDF 导出，接入统一流程 | 导出/打印 PDF，再继续 |

“输入格式不限”采用转换接口实现，**不等于无依赖解析任何二进制格式**。对于任何可导出 PDF 的格式都能接入，不能导出或无法访问的源必须说明缺少哪一步。URL 不直接传给 CLI：先在有权限的浏览器或连接器取得本地原文件/PDF，不能臆测网页内容。

```bash
python "SKILL/scripts/slide_translate.py" prepare "源文件.key" --normalized-pdf "源文件导出.pdf" --work "job"
python "SKILL/scripts/slide_translate.py" prepare "源文件.pptx" --soffice "/path/to/soffice" --work "job"
python "SKILL/scripts/slide_translate.py" prepare "图片目录" --work "job"
```

导出时确定隐藏页、动画步骤是否需要保留；遵循用户要求，否则使用应用正常的完整课件静态导出并检查。不把演讲者备注当可见页面正文。外部 PDF 必须确实来自该输入，脚本无法证明两份文件语义相同。

## OCR 与图像

每页都生成图片，即使已有可抽取文字也要核对图中嵌入标签。`--ocr` 只为没有原生文本的页调用本机 Tesseract，不覆盖已有文字；它不能保证读出混合页面内的所有图片标签。

```bash
python "SKILL/scripts/slide_translate.py" prepare "扫描课件.pdf" --work "job" --ocr --ocr-lang "eng" --dpi 200
```

OCR 需要另装 Tesseract 和对应语言数据。例如中英混排使用 `eng+chi_sim`，前提是本机有这些语言包。没有 OCR 仍可给视觉模型看每页图片，并在 figure_notes 中完成译文。纯文本模型只能使用执行端提供的 OCR/人工转录，不能标记已经看图。

## 页码与上下文

`--labels labels.json`：例如 `{"1":"1","2":"1","3":null}`。键为实际源页号，值为原页可见标签。重复页脚不影响顺序；罗马数字等可手动标注。准备后如发现标签有误，仅修正 manifest 中相应 `printed_label`（不改 page、ID、源文件或请求）；在之后核对 PDF 顶栏。

`--glossary glossary.txt`：一行一术语，例如 `attenuation = 衰减`。每批都会携带术语表。先统一高频专业词，再翻译，避免小模型在不同请求中自行换词。

请求按源页与文字长度拆分，不跨页合批。一个超长原文行也会拆成多个条目；模型须结合原页图像理解断行，逐 ID 返回，不能合并删除 ID。程序验收的是覆盖关系，不保证翻译语义。

## 中文字体

默认查找本机常见 CJK 字体（macOS Arial Unicode、Windows Arial Unicode、Linux AR PL 等），并在 PDF 中嵌入所需字符。若找不到，显式指定：

```bash
python "SKILL/scripts/slide_translate.py" build --work "job" --output "译文.pdf" --font "/path/to/font.ttf"
```

需要覆盖实际译文的 TrueType 轮廓字体。某些 Noto/Source Han `.otf` 或 `.ttc` 使用 CFF 轮廓，ReportLab 不支持，需换 TrueType 版本。脚本会检查缺字并拒绝输出乱码。没有随包分发商业字体。PDF 左侧原页使用原文件字体/图形，不重新绘制其文字。

## 完整性与恢复

- `original.pdf` 的 SHA-256 作为文档 ID。不能把别的课件译文混进来。
- 每个 chunk 只接受一个同名 JSON，每个原文 ID 恰好一次。额外或丢失条目均报错。
- 拒绝空译文和 pending 状态。unreadable 允许，但最终显示明确说明，不宣称完整识别。
- 模型用 Markdown 的单个 JSON 代码围栏包裹响应时可以读取；其他多余解释、多个对象需要重做/整理。
- 可用 `validate --partial` 检查已保存批次并显示剩余清单；它不能使 build 跳过缺失内容。
- 再运行 prepare 不覆盖已有 job；继续填写已有 responses，然后 validate/build。
- build 默认不覆盖已有 PDF，更新时用 `--force`。仍禁止覆盖本次输入及 original.pdf。
- 机械验证只确认身份、覆盖、基本结构、分页、可抽取中文及文件完整性。数字翻错、图表语义错、伪称看图等需要人工/模型对照检查，不能仅凭校验通过声称翻译正确。

## 最终版面

A3 横向，完整原页左侧、分层中文右侧（标题 21 pt、小标题 16 pt、正文 13 pt、图注 11 pt、脚注 10 pt）；超长译文续页，字号不缩小。源页可能横向、纵向、旋转、裁剪，按原可见裁剪框等比例缩放。每页有源页号、原页标签、输出页号；续页有分段号。图像仍小的场景可在 PDF 中放大；原本低分辨率的图片不能凭空变清晰。

```bash
python "SKILL/scripts/test_pipeline.py"
```

随附测试用于验证脚本机制。具体环境是否有 Office 转换器、OCR 与目标字体，需单独验证；不要将未测的转换器称为已验证。


## 原表格按表格翻译

原页出现表格，中文栏也优先使用真正的表格，不能把单元格拼成散文或用截图代替译文。保留行列对应、表头层级、行标识、单位、空白格和脚注；看不清的格子明确写“无法辨认”，不能补值。合并单元格可通过重复上级表头展开，但必须明确归属。宽表按列拆分并重复行标识；长表跨页重复表头，保持可读字号。

在首个相关 `items` 条目中保留 `id`、`zh`、`status`，设置 `role="table"`，增加二维字符串数组 `rows` 和整数 `header_rows`（无表头为 0）。例如：

```json
{"id":"p0001-t0002","zh":"成像方式对照","status":"translated","role":"table","header_rows":1,"rows":[["方式","特点"],["MRI","软组织对比度高"],["CT","使用 X 射线"]]}
```

所有原条目仍逐一提交非空译文；其余已被该表覆盖的条目增加 `table_ref="p0001-t0002"`，脚本仅在首条位置绘制整表，避免重复。引用只能指向同一源页的表格。跨批次时依据同一原页填写整表，后续批次引用原表 ID；不要为凑结构改动 ID。未提取出的整表可放入第一批 `figure_notes`，保留 `source`、`zh`、`status`，同样提供 `role`、`rows`、`header_rows`。

单元格只能填纯文本；每行列数必须相同，空格填空字符串，表头行数必须小于总行数。检查渲染后的每张表，逐格核对对应关系、数字、单位、表头和续页。结构校验不能代替内容核对。旧 job 的提示词不会自动更新，继续旧任务时也应把本节规则交给翻译模型。

## 译文质量检查

逐句翻译，禁止用词典替换生成中英夹杂的正文。导出前运行 `audit --work job`；`build` 也会自动执行该检查。缺失 role、“译文：”占位、未解释的英文残留会阻止导出。质量报告为 `job/quality-report.json`；修正后重试。新旧任务都须补齐内容类型并核对自然中文，不能把校验通过当作语义准确。

阅读[完整正反例与断行处理](quality-examples.md)。
