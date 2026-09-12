# 译文质量标准与正反例

本文件在翻译第一批前阅读；纯模型也应收到这些例子。例子说明翻译与结构标准，不作为其他课件的现成答案。

## 不合格结果与修正

| 原文/情形 | 不合格 | 合格 |
|---|---|---|
| What does E-Health refer to? | What does “E-健康” refer 到? | 电子健康指什么？ |
| Typical E-Health Terminologies | Typical E-健康 Terminologies | 常见电子健康术语 |
| Historical Perspectives | 译文：Historical Perspectives | 历史沿革 |
| Evidence-based medicine | Evidence-基于 医学 | 循证医学 |
| Reduced operating and maintenance costs | Reduced operating 和 maintenance 成本 | 降低运行和维护成本 |
| Independence of suppliers | Independence 的 suppliers | 不依赖特定供应商 |
| Telemedicine/Telecare | 译文：Telemedicine/Telecare | 远程医疗／远程照护 |
| Hospitals, clinics, / doctors, healthcare / personnel（同一标签的三行） | 每行独立一段，中间夹杂英文 | 医院、诊所、医生和医疗卫生人员（连接成一个标签） |

禁止用词典、正则或字符串替换批量“翻译”正文；这些只能用于已完成翻译后的明确术语统一。不得用“译文：”加原文、自动添加一个中文词、改 status 或虚报 reviewed 来通过检查。不能为了节省时间/token 而省略句子、图内文字或把全文改为摘要。

## 好例子一：标题和目录

原页主标题 Contents，下方是四个条目。译文应呈现为：

**目录**（title，21 pt 加粗）

- 电子健康指什么？（bullet）
- 常见电子健康术语（bullet）
- 历史沿革（bullet）
- 支撑技术与里程碑（bullet）

响应条目示例（实际使用必须复制请求中的 ID）：

```json
[
  {"id":"p0002-t0001","zh":"目录","role":"title","status":"translated"},
  {"id":"p0002-t0002","zh":"电子健康指什么？","role":"bullet","status":"translated"},
  {"id":"p0002-t0003","zh":"常见电子健康术语","role":"bullet","status":"translated"}
]
```

标题不能依据“短于70字”猜测。页眉课程代码、页码、来源应为 footnote；不得把它们当主标题或加“译文：”。原文没有标题时不编造标题。

## 好例子二：断行重组

原文是同一标签跨三条，保留所有 ID 和逐条译文，通过 join_previous 连接成完整一段。不要把跨行单词割裂翻译，不同列表项不能连接。

```json
[
  {"id":"p0004-t0001","zh":"医院、诊所、","role":"body","status":"translated"},
  {"id":"p0004-t0002","zh":"医生和医疗卫生","role":"body","status":"translated","join_previous":true},
  {"id":"p0004-t0003","zh":"人员","role":"body","status":"translated","join_previous":true}
]
```

图示按实际分组使用小标题、列表、图注，明确箭头或上下级关系，不把抽取出的标签按随机顺序堆成正文。表格按 rows/header_rows 绘制，不能逐格散排。

## 好例子三：允许保留的英文

- 电子健康记录（EHR）、计算机断层成像（CT）、剂量 0.5 mg：中文含义完整，缩写/单位保留。
- Intel 处理器：品牌可保留，条目添加 `"retained_terms":[{"text":"Intel","reason":"品牌名"}]`。
- 作者姓名、正式文献题名、网址、型号、公式可按需要保留；非自动识别的英文须逐项说明保留理由。
- 不能将 vendors、personnel、maintenance 等普通单词登记为“专有名词”；不能整段豁免漏译。中文后括注英文术语应克制，不能用括注原文代替中文翻译。

## 翻译与交付两道复核

1. 每批完成后逐条读一遍中文：主谓关系、否定、因果、比较、数字、单位是否准确？是否还有普通英文词？是否出现词典替换式语序？术语表只是辅助，不能替代逐句翻译。
2. 先做至少三类代表页（标题/正文页、图示页、表格或密集页；课件没有的类型不强求），检查译文后再继续。不要一键生成全部响应并统一填 reviewed。
3. 完整运行 `validate` → `audit` → `build` → `verify`。audit/build 对缺失 role、“译文：”占位和疑似英文残留报错，在 quality-report.json 定位源页及条目。普通正文缺层级给出逐页复核提示；按原图修正，不为了消除提示造标题。
4. 对所有中文文本（含表格单元格、图注）做语义复核，再看全稿缩略图，放大检查所有警告页及代表页。脚本检查通过只说明未发现这些机械问题，不证明翻译准确、完整或真的看过图片。
5. 仍有残留或结构错误就返工相应批次，重新导出。无法辨认的原文标明位置；无法达到要求时如实说明，不能称为合格成品。

旧任务也适用：补齐 role，修正英文残留，按原图连接断行，增加必要的 retained_terms；不能靠旧版 build 或删除检查跳过。不要因旧提示词未包含新规则而继续交付低质量结果。
