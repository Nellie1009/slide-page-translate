# GitHub 调研：从课件到可学习的复习资料

调研日期：2026-09-20。以下直接阅读项目文档或源码，借鉴组织方法；未安装、运行这些项目，也未把用户课件传给其模型服务。此处不是对学习效果的实验验证。

## 1. SlideNote：覆盖、来源与教学讲解分开

项目：[Cat-blizzard/SlideNote](https://github.com/Cat-blizzard/SlideNote)，阅读版本 `d3718ca753cf5d859e2995b6bee0444e87b3b8f7`。

核对：[质量与学习包说明](https://github.com/Cat-blizzard/SlideNote/blob/d3718ca753cf5d859e2995b6bee0444e87b3b8f7/docs/quality-and-guard.zh-CN.md)、[讲义提示规则](https://github.com/Cat-blizzard/SlideNote/blob/d3718ca753cf5d859e2995b6bee0444e87b3b8f7/slidenote/notes/prompt_rules.py)、[复习清单渲染](https://github.com/Cat-blizzard/SlideNote/blob/d3718ca753cf5d859e2995b6bee0444e87b3b8f7/slidenote/study_pack/review.py)。

项目先理解整份/逐页材料，再写讲义、做覆盖检查，另生成复习与考试材料。复习结构包括逻辑链、知识点及解释、易错点、来源、解题方法、图表公式速查。

采纳：先理解整章再规划精简复习提纲，内容与覆盖检查分工；来源保存在数据中，必要时短写知识关系与易混辨析。

不照搬：外部模型 API、整套导出平台、无依据的考试重要性标签；本技能依旧由当前模型完成内容工作。

## 2. ExamPass-Assistant：把隐含推理展开成教学链

项目：[WUBING2023/ExamPass-Assistant](https://github.com/WUBING2023/ExamPass-Assistant)，阅读版本 `3812643baf5de8b92bac17fbb4e136adcc19c41b`（master）。

核对：[知识清单提示构造代码](https://github.com/WUBING2023/ExamPass-Assistant/blob/3812643baf5de8b92bac17fbb4e136adcc19c41b/scripts/knowledge_analyzer.py)。

该代码提供考试、平衡、深度学习模式；深度模式先给直觉，再说明定义、动机、推导、例子、对比、易错点和记忆抓手，反对只有术语加一句解释。

采纳：读者可能不理解时补必要的短解释，辨析使用共同维度；不自动扩写推导、动机和案例。

不照搬：每页强制八个栏目和每个方法都补例子，会让窄栏冗余；原代码以强调、重复等推测“必考/高频”，不足以证明真实考情，本规范只按来源整理复习提纲。

## 3. bilingual-slide-study-kit：按页码范围建立学习路线

项目：[Misakakuroko/bilingual-slide-study-kit](https://github.com/Misakakuroko/bilingual-slide-study-kit)，阅读版本 `09fc9055f068449551a4dec8ad7489cbcda644a2`。

核对：[复习页面评审标准](https://github.com/Misakakuroko/bilingual-slide-study-kit/blob/09fc9055f068449551a4dec8ad7489cbcda644a2/skills/course-ppt-review-html/references/review-page-criteria.md)。

该项目按课件页码范围重建课程逻辑，组织重要图像解释、术语、短答、方法比较、易混点和复习顺序。图片解释要求说明这页想教什么、如何读图和应避免的误解。

采纳：以全课件知识关系组织整体架构，按需整理术语、常规双语短答和易混辨析。整体架构通常只写一次。

不照搬：只用英文作答、HTML 产品布局、固定中文字数门槛及选择性跳页。短答题目和答案均用中英双语。本技能第二栏默认完整中文，第一、二栏逐页完整覆盖。

## 4. school-skills / lecture-to-study-guide：问题引导与主动回忆

项目：[Jellypod-Inc/school-skills](https://github.com/Jellypod-Inc/school-skills)，阅读版本 `cd484795e924e454caafd13ddc25c1ec76c48718`。

核对：[技能说明](https://github.com/Jellypod-Inc/school-skills/blob/cd484795e924e454caafd13ddc25c1ec76c48718/skills/lecture-to-study-guide/SKILL.md)、[学习方法参考](https://github.com/Jellypod-Inc/school-skills/blob/cd484795e924e454caafd13ddc25c1ec76c48718/skills/lecture-to-study-guide/references/study-techniques.md)。

项目用主题大纲、带来源的术语、概念讲解、例题、练习与速查页组织学习资料；参考文件把 SQ3R 用于问题引导，把费曼式解释用于定义和解题步骤，把 Cornell 结构用于速查。

采纳：用常规问题帮助回忆，答案优先摘用PPT原句；本技能将中英题目和答案相邻排列，便于直接背诵，不增设自测区。

不照搬：固定七章、10–20 题、固定题型比例，以及与三栏版式无关的工具依赖。所述方法是该项目的设计选择，不是本次验证过的教学效果结论。

## 融入本技能的规则

从整份课件按需选择“整体架构、重要术语、中英双语短答、易混辨析”，简短且跨页去重。非知识页可留空，不强迫每页凑齐四类，不增加固定学习目标、自测或复习建议。来源覆盖单独检查，不把覆盖率清单当成正文模板。正式考纲依赖教师或课程材料；没有依据时只生成清楚标注的复习提纲。

执行规则见[知识点规范](study-guide.md)。这些项目没有被当作原位 PPT 翻译或三栏渲染已经可用的证据。
