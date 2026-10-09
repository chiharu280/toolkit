# rst_to_md.py

把 reStructuredText（RST）源文件转成 Markdown。专门针对 **Sphinx 项目**：pandoc 本身处理不了的 Sphinx 专有语法，由本脚本补齐。

来源：Google C++ Style Guide 中文版整理任务。

## 用途

把 Sphinx 文档站的 RST 源转成可直接阅读的 Markdown，并修好两类 pandoc 原生不认识的 Sphinx 构造：

- `:ref:`label`` / `:ref:`文字 <label>`` 交叉引用 —— pandoc 的 RST reader 不认识 `:ref:` 角色，只会把 label 原样打印出来，对读者毫无意义。本脚本先把 `:ref:` 改写成 pandoc 能识别的 RST 外链语法，从而在输出里生成真正的 Markdown 链接（含 `#锚点`，锚点算法仿 GitHub）。
- `.. tip::` / `.. note::` / `.. warning::` 提示块 —— pandoc 输出为 `> [!TIP]` 形式，本脚本再改写成 `> **Tip：** ` 的中文加粗标签。

这在以 PDF 为终端的场景里可以跟 `pdf_to_md` 互补：PDF 是渲染后的 2017 版，RST 源能拿到最新版内容。

### 使用

```bash
pip install pypandoc_binary   # 自带 pandoc 二进制，无需系统另装

# 先在本地准备好 RST 源，再转换
git clone --depth 1 https://github.com/zh-google-styleguide/zh-google-styleguide.git /tmp/zgsg
python rst_to_md.py /tmp/zgsg/google-cpp-styleguide <out_dir>
```

输出为按文件拆分的 `.md` 加一个 `index.md` 目录。

## 局限

- **文件名清单写死**：`FILES` 硬编码了 12 个源文件名（`index.rst` … `end.rst`）。源目录里若缺其中任何一个文件，脚本直接报错退出；反过来，清单外的文件会被完全忽略。
- **输出文件名固定**：`00-front` / `01-headers` … `11-end` 由 `FILES` 写死，与 `pdf_to_md` 的编号并不一致（upstream 版多一章「函数」，故编号整体后移）。
- **仅修两类 Sphinx 构造**：其他 Sphinx 专有指令（`.. toctree::`、`:doc:`、`:mod:`、`.. code-block::` 的选项等）不处理，交给 pandoc 后可能丢失或变形。
- **未解析的引用会退化**：`collect_labels` 只能解析「紧邻标题上方的 `.. _label:`」。引用指向清单外的文件、或 label 在标题后较远处时，链接会退化成纯文本 `` `label` ``。
- **标题锚点算法是近似**：`gfm_slug` 模仿 GitHub 但不等价，标题含特殊符号时锚点可能对不上。
- **整份转换依赖 pandoc**：`pypandoc` 只是壳，真正的转换由 pandoc 完成。因此受 pandoc 的 RST reader 能力上限约束，并需要 pandoc 可执行文件（推荐装 `pypandoc_binary`）。
- **文本层面的全局替换有副作用**：`\\#` → `#`、`\\+` → `+` 会作用于全文，正文中本应保留转义的地方可能被误改。
