# disk_usage

只读查询 Linux 文件系统容量，以及指定文件或目录的实际磁盘占用。目录模式列出其**直接子项**（包括普通文件），按占用从大到小排序；对大目录继续指定该目录运行即可逐层定位。依赖 Python 3 标准库和 GNU `du`，在本目录维护。

```bash
python3 disk_usage.py                         # 用户主目录
python3 disk_usage.py ~/patacwork --top 20    # 指定目录，显示前 20 项
python3 disk_usage.py /var/cache --top 0      # 显示全部直接子项
python3 disk_usage.py ~/patacwork --json      # 机器可读输出
```

使用 `du -x -B1` 统计已分配空间，限制在目标所在文件系统内，不跟随目录中的符号链接；`--json` 中保留原始字节数。文件系统总量与可用量来自 `shutil.disk_usage`。工具不会删除任何文件。

局限：默认只显示最大的 15 个直接子项；权限不足时会报告 `du` 的错误，统计可能不完整。硬链接、稀疏文件及打开但已删除的文件会使 `du` 与 `df` 的数字不同；子项占用也不一定能简单相加。扫描大型目录可能耗时。此脚本只回答“哪里占空间”，是否可以删除需结合文件用途判断；缓存建议可用 [`disk_cache_audit`](../disk_cache_audit/) 查看。
