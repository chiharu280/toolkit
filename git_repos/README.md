# git_repos

跨平台扫描目录树中的 Git 仓库，并汇总当前分支、未提交条目数、已跟踪文件改动、未跟踪文件以及暂存、未暂存条目。适用于 Windows、Linux 和 macOS，要求 Python 3.9+ 与 Git 已安装且在 `PATH` 中；不依赖第三方 Python 包。

## 使用

```text
python git_repos.py                 # 扫描当前用户主目录
python git_repos.py ~/work ~/src    # Linux/macOS：指定多个目录
python git_repos.py C:\work D:\src # Windows：指定多个目录
```

可将脚本放到常用目录并为其建立 shell alias 或 Windows 命令入口。默认范围是用户主目录；需要扫描其他磁盘或目录时显式传入路径。路径可含空格或非 ASCII 字符。

工具只读取仓库状态，不会 fetch、pull、切换分支或修改文件。扫描不会跟随目录符号链接；Git worktree 和 submodule 会按独立仓库发现，嵌套仓库也会分别列出。Git 状态由本地索引和工作区决定；不提供与远端的领先/落后信息。全盘扫描可能很慢，也可能因权限跳过目录。

## 关联知识

原理、状态字段解释和扫描边界见知识库：[Git 仓库批量扫描与状态汇总](../../knowledgeBase/03-Workflow-Tools/Shell-And-Scripts/Git仓库批量扫描与状态汇总.md)。
