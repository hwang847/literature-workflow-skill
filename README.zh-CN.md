# 文献阅读工作流 Skill

[English](README.md)

这个仓库定义了一套文献阅读工作流，并把它注册成 Codex skill，方便你直接在 Codex 中使用。

本仓库使用 Codex 开发并维护。

它适合配合你常用的 PDF 阅读器和本地论文文件夹使用。它可以帮助 Codex 定位 PDF、把复制来的论文标题映射到编号文件、管理同一文献的多个 source、渲染论文截图，和你讨论方法 pipeline，并根据对话生成简洁的 HTML 笔记。

它不是内置 PDF 阅读器。你仍然可以用 Zotero、Office、Preview、浏览器或任何你喜欢的阅读器看 PDF；Codex 负责可检索的工作区、交互式解读、source 管理和笔记生成。

## 如何配合

你需要做的事情很少：

- 安装一次 skill。
- 选择一个本地文件夹作为论文工作区。
- 把 PDF 放进去，不需要改文件名。
- 从 PDF 阅读器复制论文标题，然后让 Codex 带你读。
- 在需要时告诉 Codex 你的阅读和笔记偏好。

Codex 可以帮你做到：

- 配置工作区、建立 PDF 索引、记录相关 source。
- 把复制来的论文标题匹配到本地的 arXiv 编号、会议编号或普通下载文件名。
- 把复杂文献转写成更适合你阅读偏好的解释。
- 回答你关于方法、pipeline、实现细节、related work 或综述定位的追问。
- 根据论文和你们的讨论生成简洁 HTML 笔记；本地支持渲染时，还可以加入论文截图。

## 工作流边界

这个 skill 为 Codex 固化的是那些重复、容易出错、需要稳定脚本支持的部分：

- 工作区初始化和环境检查；
- PDF 索引和复制标题查找；
- PDF、arXiv、DOI、项目页、代码仓库、文档、slides 的 source registry；
- 阅读材料准备；
- 为笔记渲染论文截图；
- HTML 笔记文件名规范化。

Codex 本身通过对话处理更灵活的部分：

- 按你的语言和阅读风格解释论文；
- 调整阅读重点，例如方法 pipeline、实现细节或 related work；
- 当你的偏好稳定后，更新当前工作区的 `AGENTS.md`；
- 只有在你明确要求时，才清理、移动、重命名或分类文件。

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

Codex 会创建目录结构、初始化索引、检查本地能力，并维护一个精简的 `AGENTS.md` 来记录你的偏好。你不需要手动建目录或检查 Python 包。

然后把 PDF 放进这个文件夹，继续说：

```text
刷新索引
带我读这篇论文
解释它的方法 pipeline
为这篇生成 HTML 笔记
```

## 日常用法

你不需要把下载下来的 PDF 从 arXiv 编号、会议编号或下载名改成论文标题。像 `2508.05002v1.pdf`、`2025.findings-naacl.245.pdf`、`download.pdf` 这样的文件名都可以直接使用。

工作区配置好之后：

1. 把新的 PDF 放进工作区根目录或 `papers/`。
2. 用你的 PDF 阅读器打开论文。
3. 复制论文标题。
4. 对 Codex 说：

```text
使用 $literature-workflow，带我读这篇文献：
APEX-SQL: Talking to the data via Agentic Exploration for Text-to-SQL
```

Codex 会在需要时刷新索引，把复制的论文标题匹配到本地 PDF，准备阅读材料，然后开始交互式阅读。你可以继续追问方法、pipeline、实现细节、related work，或任何你关心的部分。

当你觉得已经讨论清楚后，再让 Codex 生成 HTML 笔记。笔记会结合论文内容和你们的讨论，所以它应该更贴近你的关注点，而不是通用摘要。

## 工作区

```text
your-workspace/
├── papers/                 # 可选，由你自己整理的 PDF
├── notes/                  # HTML 笔记
│   └── assets/             # 截图
├── references/             # 索引和 source registry
└── AGENTS.md               # 本地 Codex 偏好
```

新 PDF 可以直接放在工作区根目录作为 inbox。已经放在 `papers/` 下的 PDF 也可以直接使用。

这个 skill 不会强制规定文件分类方式，也不会自动移动你的 PDF。之后如果你想清理文件夹、重命名或分类，直接让 Codex 按你的想法处理即可。

## 自定义

把你的偏好告诉 Codex：

```text
我的笔记重点关注实现细节和 pipeline 复现。
HTML 笔记越简洁越好。
默认跳过实验，除非我问。
阅读和笔记使用中文。
我正在做文献综述，所以更关注 related work 和论文定位。
项目页和 GitHub repo 也要作为 source 关联起来。
```

Codex 会把稳定偏好整理到本地 `AGENTS.md`，并在你的工作流变化后继续更新它。

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
