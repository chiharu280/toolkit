# toolkit

用过的工具的归档目录。目的是把散落在各个项目里的脚本集中起来，方便以后查找和复用。

## 约定

每个工具一个独立文件夹，文件夹内包含：

- 工具本体（脚本 / 程序）
- `README.md` 使用说明，至少说明 **用途** 和 **局限**

从其他项目归档的工具，其原始文件仍留在各自的项目里；改 bug 请改源仓库再同步过来。直接在本目录创建的工具以本目录为维护位置。

## 工具列表

| 工具 | 用途 | 来源 |
| --- | --- | --- |
| [pdf_to_md](pdf_to_md/) | 把 PDF 转成分章节 Markdown，专门修复中文 PDF 字体 ToUnicode 映射损坏导致的乱码/丢字 | Google C++ Style Guide 中文版整理任务 |
| [rst_to_md](rst_to_md/) | 把 Sphinx 的 reStructuredText 源转成 Markdown，补齐 pandoc 不支持的 `:ref:` 交叉引用和提示块 | Google C++ Style Guide 中文版整理任务 |
| [camera_capture](camera_capture/) | 用 OpenCV 从摄像头拍一张照片，或按指定帧率拍摄指定张数 | 本目录新建 |

> 上面两个工具来自同一个任务（Google C++ Style Guide 中文版的 PDF 版与上游 RST 版互相补充），可以配套使用。
