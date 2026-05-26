# 文献阅读工作流 Skill

[English](README.md)

这是一个 Codex workflow skill，用来快速阅读论文方法、和 Codex 讨论 pipeline、管理多来源文献，并生成个性化 HTML 论文笔记。

你只需要选一个论文文件夹，剩下交给 Codex。

## Quickstart

安装：

```bash
mkdir -p ~/.codex/skills
git clone https://github.com/hwang847/literature-workflow-skill.git ~/.codex/skills/literature-workflow
```

重启 Codex App，或开启新的 Codex CLI 会话。

打开你想作为论文库的文件夹，或者在终端 `cd` 到这个文件夹，然后对 Codex 说：

```text
使用 $literature-workflow，帮我配置这个论文阅读工作区。
```

你不需要手动建目录、初始化索引、制作或维护 `AGENTS.md`、检查 Python 包。Codex 会准备工作区，并持续把本地规则维护得尽量精简。

然后把 PDF 放进这个文件夹，继续说：

```text
刷新索引
带我读这篇论文
解释它的方法 pipeline
为这篇生成 HTML 笔记
```

## Codex 会准备什么

```text
your-workspace/
├── papers/                 # 可选，已整理 PDF
├── notes/                  # HTML 笔记
│   └── assets/             # 截图
├── references/             # 索引和 source registry
└── AGENTS.md               # 本地 Codex 偏好
```

新 PDF 可以直接放在工作区根目录作为 inbox。已经放在 `papers/` 下的 PDF 也可以直接使用。

## 个性化

把你的偏好告诉 Codex：

```text
我的笔记重点关注实现细节和 pipeline 复现。
HTML 笔记越简洁越好。
默认跳过实验，除非我问。
阅读和笔记使用中文。
项目页和 GitHub repo 也要作为 source 关联起来。
```

Codex 会把稳定偏好整理到本地 `AGENTS.md`，并在你的工作流变化后继续更新它，不用你自己改配置。

## Source 模型

阅读对象是 entity：`paper`、`tech_doc`、`repo`、`spec`、`dataset`、`slides`、`unknown`。

source 是指向 entity 的入口：PDF、arXiv、DOI、URL、GitHub repo、本地文档、项目页、slides 等。

一个 entity 可以有多个 source。例如同一篇论文可以同时有本地 PDF、arXiv、DOI、项目页和代码仓库。

## 维护者测试

在本仓库根目录运行：

```bash
python3 tests/smoke_test.py
python3 tests/privacy_scan.py
```
