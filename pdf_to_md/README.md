# pdf_to_md.py

把 PDF 转成分章节的 Markdown。专门针对**中文 PDF 字体 ToUnicode 映射损坏**这一类问题而写。

来源：Google C++ Style Guide 中文版整理任务。

## 用途

解决「PDF 里的中文提取出来是乱码或丢字」的问题。

以 `Google C++ Style Guide` 中文版 PDF 为例：所有标题使用 SimHei 字体，而该字体在 PDF 中的 ToUnicode CMap 有 4 个子集是坏的。常见工具因此失效：

- `pdftotext` / `pandoc`：输出乱码（`3.11. ᆎ<0a0c><19dd><086c>`）
- `pymupdf4llm` / `pymupdf`：静默丢字，例如「1.3. #define 保护」的「保」丢失

本工具的解法：用 pdfplumber 保留未映射字符为 `(cid:N)`，利用 N 就是字形 id 这一事实，按 `真实字符 = N + 0x49CA` 反查回来，再逐字符渲染比对验证。在结构上，字号决定标题层级，整栏宽横线界定 `Tip:` 提示框，横线间距界定表格，等宽字符宽度反推代码缩进。

### 使用

```bash
pip install pdfplumber pymupdf

python pdf_to_md.py <input.pdf> <out_dir>
```

输出为多个 `.md`（按章节拆分）加一个 `index.md` 目录索引。

## 局限

**这是针对单份 PDF 定制的脚本，不是通用转换器。** 换一份 PDF 基本需要重调；直接复用前请确认以下几点。

- **字体修复规则写死**：`FIX_OFFSET = 0x49CA`、`SPECIAL_CIDS`（`、（）南` 四个例外字形）只对这份 PDF 的 SimHei 子集成立。换字体、换子集即失效。
- **结构假设写死**：字号阈值（9 / 10.5 / 12 / 14.3 / 17pt）、等宽字符宽度 `4.7072pt`、行距阈值 `17pt`、横线坐标 `43.7 / 551.6` 都来自这份 PDF 的 LaTeX 排版。其他排版工具生成的 PDF 需要重新测量。
- **章节映射写死**：`CHAPTER_FILES` 把章号映射到固定文件名（`00-front` … `10-end`），只覆盖 0–10 章。
- **假定第 1 页是标题页**并被无条件丢弃（`r.page > 1`）。
- **只处理 PDF 文本层**：扫描件 / 图片型 PDF（无文本层）无法使用，需要先 OCR。
- **代码块统一标注为 `cpp`**，即使个别代码块实际是 C 或纯文本。
- **依赖字体信息**：纯文本型 PDF（无 `(cid:N)`）走不到修复分支，虽然能跑但收益为 0，用通用工具即可。

## 相关

同源任务中还有一个 `rst_to_md.py`（把 reStructuredText 经 pandoc 转 Markdown，并改写 Sphinx `:ref:` 交叉引用），当前未收入本目录。
