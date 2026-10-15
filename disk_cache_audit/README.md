# disk_cache_audit

Linux 用户目录的**只读**磁盘占用与常见缓存检查工具。使用 Python 3 标准库及 GNU `du`，不删除文件，也不扫描符号链接指向的目录。脚本在本目录维护。

```bash
python3 disk_cache_audit.py
python3 disk_cache_audit.py --top 15 --json
python3 disk_cache_audit.py --home /path/to/home
```

输出用户目录一级目录占用、几个明确的缓存路径及处置等级。“可清理”表示一般可重建，仍应退出相应程序后操作；“需确认”表示可能影响离线数据、索引重建或运行时下载。脚本不会推荐删除整个 `.config`、Conda 环境、项目数据、下载目录或 Git 仓库。Conda 包缓存另用 `conda clean --all --dry-run --yes` 核对；清理时用 `conda clean --all --yes`，不要直接删除 `pkgs` 整个目录。

大小来自 `du -x -B1`，是已分配空间的估计。存在硬链接、共享数据或正在打开的文件时，各项数字相加不等于实际可释放空间；删除后以 `df` 复核。部分目录不可读时脚本跳过，结果并非全盘审计。飞书的 `Service Worker/CacheStorage` 虽名为缓存，可能保留离线内容，因此始终列为“需确认”。
