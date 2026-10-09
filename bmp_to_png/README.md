# bmp_to_png

把符合脚本格式假设的 24/32 位 BMP 截图转为 PNG。来自 `Azul_SDL2/scripts/bmp_to_png.py`，归档副本与源文件保持一致；仅使用 Python 标准库。

## 使用

```bash
python3 bmp_to_png/bmp_to_png.py /path/to/screenshot.bmp
python3 bmp_to_png/bmp_to_png.py /path/to/bmp_directory
```

输出写在输入旁边、扩展名改为 `.png`。目录参数只处理该目录顶层的 `*.bmp`。

## 局限

- 只接受 24/32 位、压缩字段为 0 或 3 的 BMP，并按 BGR(A) 字节顺序读取；脚本不解析位掩码，压缩、调色板和其他像素布局可能失败或颜色错误。
- **已有同名 PNG 会被覆盖**。运行前先检查输出路径，并保留需要的旧文件。
- 逐文件读入内存，大图或大量图片转换时注意内存占用。
- 不提供递归扫描或批量失败回滚。出现错误时，此前已生成的 PNG 会保留。

2026-10-09 使用临时生成的 2×1、24 位 BMP 验证了转换、像素颜色和输出 PNG 可读取；未测试全部 BMP 变体。
