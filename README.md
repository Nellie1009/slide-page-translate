# Slide Page Translate · 课件逐页对照翻译

将课件按实际页码逐页翻译成中文，输出左侧原页、右侧中文的 PDF。适用于能运行脚本的 Agent，也提供普通聊天模型可用的操作说明和完整代码。

**模型负责翻译，Python 程序负责拆页、编号、校验、排版和导出。运行时不依赖其他 Skill。**

## 翻译效果预览

以下选自医学影像课件的逐页对照翻译 PDF：左侧保留英文原页，右侧为中文译文，同时标注 PDF 实际页码和课件印刷页码。点击图片可查看大图。

### CT：数值与单位对照

保留组织灰度示例，并对应翻译 HU 数值、单位及说明（PDF 第 29 页，课件标注第 28 页）。

![CT 对比度翻译效果：英文原页与中文译文并排，保留 HU 数值与图例](assets/examples/ct-contrast.png)

### MRI：医学图片与正文对照

保留 CT 与 MRI 的原始对比图，逐项翻译灰白质对比和软组织说明（PDF 第 34 页，课件标注第 33 页）。

![MRI 对比度翻译效果：保留 CT 与 MRI 图片，并附中文正文](assets/examples/mri-contrast.png)

### OCT：图中标签与层次说明

保留视网膜分层图，并在中文栏补充层次标签的翻译（PDF 第 46 页，课件标注第 45 页）。

![OCT 翻译效果：视网膜分层原图与中文正文、图中标签对照](assets/examples/oct-retinal-layers.png)

截图保留原页图表出处，用于展示翻译与排版效果。

## 功能

- 保留完整原页，同时标注源文件页码和课件印刷页码；重复、缺失或跳号的页脚不会改变源页顺序。
- 按页和文字长度拆成小批次；已完成的译文可保存、校验和继续处理。
- 检查文档身份、漏批、漏条目、重复编号和空译文。
- 中文保持可读字号；长页自动续页，不以缩小字体或截断文本强行塞入一页。
- 支持图内文字补译与无法辨认标记；未看图的结果必须明确披露。
- 最终成果格式为 PDF；JSON 和预览图片仅为中间文件。

## 输入格式

| 输入 | 处理方式 |
|---|---|
| PDF | 直接保留原页 |
| PPT / PPTX / ODP 等 | 通过本机 LibreOffice 转成 PDF |
| PNG / JPEG / TIFF / BMP / WebP，或图片目录 | 自动按图片顺序生成原页 |
| Keynote、在线幻灯片、网页及其他格式 | 原应用导出或打印成 PDF，通过 `--normalized-pdf` 接入 |

不限制原始课件格式，但无法自动解析的格式需要原应用完成 PDF 导出。扫描页可结合视觉模型、人工转录或可选的本机 Tesseract OCR。

## 给 Agent 使用

将整个仓库放到你的 Agent 支持的技能目录，文件夹命名为 `slide-page-translate`，保留根目录的 `SKILL.md`、`scripts/` 和 `references/`。

示例调用：

> 使用 slide-page-translate，按实际页码逐页对照翻译这份课件，只输出 PDF。

支持 `$技能名` 的环境可使用 `$slide-page-translate`。具体技能入口见 [SKILL.md](SKILL.md)。

## 给普通聊天模型使用

查看 [MODEL_ONLY_KIT.md](MODEL_ONLY_KIT.md)。该文件包含逐批提示词的使用方法、运行说明、依赖及完整 Python 源码。

没有代码执行能力的模型只返回翻译 JSON；由用户或具有代码执行能力的平台运行程序生成真正的 PDF。不需要模型自行重写排版代码，也不需要向每一批翻译请求重复提供整份程序。

## 命令行流程

需要 Python 3.10+、可嵌入且覆盖中文字形的 TrueType 字体。转换 Office 文件时另需 LibreOffice，OCR 时另需 Tesseract。

在仓库根目录执行：

```bash
python -m pip install -r scripts/requirements.txt
python scripts/slide_translate.py prepare "课件.pdf" --work "job"
```

将 `job/prompts/` 中每个提示词与对应的 `job/pages/` 原页图片交给模型，把响应 JSON 存入 `job/responses/`，文件名保持对应的 `chunk_id`。

```bash
# 每完成一批可校验一次
python scripts/slide_translate.py validate --work "job" --partial

# 全部译完后校验并生成 PDF
python scripts/slide_translate.py validate --work "job"
python scripts/slide_translate.py build --work "job" --output "对照翻译.pdf"
python scripts/slide_translate.py verify --work "job"
```

查看 `job/qa/` 的预览，并核对最终 PDF。字体、OCR、其他格式、恢复与排错详见 [运行说明](references/runtime.md)。

## 仓库内容

```text
SKILL.md                  Agent 的技能入口
agents/openai.yaml        可选界面元数据
scripts/slide_translate.py 固定执行程序
scripts/requirements.txt   Python 依赖
scripts/test_pipeline.py   自动化机制测试
references/               分场景说明
MODEL_ONLY_KIT.md         给普通模型的自包含备用版本
assets/examples/          README 翻译效果截图
```

没有额外的“技能包运行时”。ZIP 仅是这些文件的分发形式，不需要与本目录同时安装。仓库仅附上述效果截图，不附带完整课件、完整译文 PDF、商业字体或模型凭据。

## 验证与边界

```bash
python scripts/test_pipeline.py
```

发布前已通过 11 项机制测试，并用独立 Agent 完成含重复页码、图片文字和文档内指令的三页样例。另对 81 页课件完成拆页验证，检查了长译文续页与旋转、裁剪页面的排版。

这些检查不等于对所有小模型或所有操作系统的质量保证。模型的翻译准确性、专业术语、OCR 和图中标签仍需对照检查。当前未在本环境实测 LibreOffice 和 Tesseract 转换路径；缺少转换器时可使用原应用导出的 PDF。

程序不调用模型 API、不上传文件；如果用户主动把页面发送给外部模型，该传输由用户所用的平台处理。无需为本程序配置 API Key 或 GitHub Secrets。
