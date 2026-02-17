# MOLTBOT Office Word 模板对齐项目详细记录（2026-02-10）

## 1. 项目背景

- 目标：将输出文档 `final.docx` 在排版上尽量 100% 对齐用户模板 `报告模板.docx`。
- 关键例外：用户手打编号（如 `一、`、`（一）`、`1、`、`1）`）不再保留为手打文本，改为系统自动多级编号。
- 场景：WPS/Word 自动化出文，要求稳定保留模板中的字体、字号、行距、段落格式，同时解决编号可维护性。

## 2. 输入与参考文件

- 用户模板原件：`C:\Users\shikq\备份文档（Ewin）\brainstorm\工作\光大风控部\新课题\报告模板.docx`
- 项目内模板副本：`c:\moltbot-secure\data\office-template-extract\report-template-from-user.docx`
- 关键代码文件：`c:\moltbot-secure\skills\office\host_worker\wps_word.py`
- 关键验证文件：`c:\moltbot-secure\data\office-template-extract\template-finalize-verify-v7.json`

## 3. 需求拆解与约束

### 3.1 必须满足

- 页面、字体、字号、行距、段落参数尽可能与模板一致。
- 编号采用系统自动生成，禁止手打编号残留。
- 标号层级与文本语义一致：一级/二级/三级/四级可自动维护。

### 3.2 已识别难点

- WPS/Word 的列表模板在不同阶段可能引入隐式 tab/hanging indent，导致“看起来缩进漂移”。
- 若在 COM 层直接重做过多样式，容易破坏用户模板已有的细节格式。
- 段落里混有手打前缀与编号属性时，会出现“双编号”或位置错位。

## 4. 关键实现（代码层）

本次核心实现位于 `host_worker/wps_word.py`，新增/强化了以下能力：

1. 模板驱动能力
- 引入模板 profile 机制（`DEFAULT_WORD_TEMPLATE_PROFILE`、`_load_word_profile`）。
- 支持 `apply_cn_report_template` 动作下的定制收敛。

2. 手打编号识别与剥离
- 增加 `MANUAL_PREFIX_PATTERNS`（H1/H2/H3/H4）识别手打前缀。
- 使用 `_strip_manual_prefix_in_place` / `_strip_manual_prefix` 删除手打前缀，避免双编号。

3. 编号层级规划与回写
- `_apply_cn_report_template` 产出 `numbering_plan`。
- 保存 docx 后执行 `_patch_numbering_in_saved_docx`，直接改写 OOXML 编号结构，提升稳定性。

4. 缩进与编号冲突治理
- 新增 `_extract_non_empty_paragraph_indents` 与 `_restore_paragraph_indent`，在必要时恢复源段落缩进。
- 在 `word/numbering.xml` 侧强制 `suff=space`，并清理 `lvl/pPr` 中可能引入偏移的列表层级缩进控制。
- 保留段落级 `pPr` 作为唯一缩进来源，避免列表模板重复施加缩进。

5. 页面与段落规则应用
- `_apply_page_setup`、`_apply_style_to_paragraph`、`_apply_bold_before_colon` 等方法用于模板化控制。
- 对“尽量保持原模板格式”的模式增加保护：仅做必要调整，不全量覆盖。

## 5. 迭代过程（按产物目录）

以下版本目录来自 `C:\MoltbotShare\out`：

- `20260209-205928-template-align-v2`
- `20260209-210200-template-align-v2`
- `20260209-211630-template-align-v3`
- `20260209-222054-template-align-v4`
- `20260209-222735-template-align-v5`
- `20260210-014739-template-align-v7-final`（当前最终可用）

说明：v6 产物已在用户确认后清理，不作为最终保留版本。

## 6. 最终产物与验证

### 6.1 最终产物

- DOCX：`C:\MoltbotShare\out\20260210-014739-template-align-v7-final\final.docx`
- PDF：`C:\MoltbotShare\out\20260210-014739-template-align-v7-final\final.pdf`

### 6.2 自动验证结果（v7）

来源：`c:\moltbot-secure\data\office-template-extract\template-finalize-verify-v7.json`

- `paragraph_count_src = 34`
- `paragraph_count_final = 34`
- `manual_prefix_left_count = 0`
- `level_mismatch_count = 0`
- `indent_mismatch_count = 0`
- `mismatch_samples = []`

结论：自动验证层面，编号残留/层级/缩进三项均为 0，不一致样本为空。

## 7. 用户侧验收反馈

- 用户反馈“字体和行间距基本正确”。
- 用户确认“标号问题主要来自手打编号，系统编号效果更好”。
- 用户对当前输出评价为“近乎完美”，并确认执行清理。

## 8. 清理记录（已执行）

在用户明确“确认清理”后完成：

- 已删除目录：`C:\MoltbotShare\out\20260209-223359-template-align-v6`
- 已删除文件：`c:\moltbot-secure\data\office-template-extract\template-finalize-verify-v6.json`

## 9. 风险与后续建议

1. 风险
- WPS 与 Word 在极端复杂列表场景下仍可能有渲染细差（尤其跨机器版本）。
- 当输入文本包含非规范前缀时，正则归一可能需要补充规则。

2. 建议
- 将当前 v7 规则固化为默认模板流程（含 profile 与验证脚本）。
- 在回归集加入更多“手打编号污染样本”与“混合缩进样本”。
- 保留 `template-finalize-verify-v7.json` 作为后续版本对比基线。

## 10. 回滚路径

- 若后续版本出现回归，可先回退到本次最终产物进行业务交付：
  - `C:\MoltbotShare\out\20260210-014739-template-align-v7-final\final.docx`
- 代码层可按 `skills/office` 仓库提交历史对 `host_worker/wps_word.py` 回滚对应变更点。

