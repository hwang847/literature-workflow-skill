# 文献阅读工作流 Skill

[English](README.md)

这是一个面向 Codex App / Codex CLI 的文献阅读工作流。更准确地说，它是一个 **Codex literature workflow skill**：帮助你快速定位论文、读懂方法 pipeline、和 Codex 讨论细节，并把讨论结果生成个性化 HTML 论文笔记。

开源版默认使用英文说明和英文示例；中文说明是可选辅助。如果你希望 Codex 默认用中文带读、讨论和写笔记，把这个偏好告诉 Codex，让它记录到你本地的 `AGENTS.md`。

它不是一个普通脚本，也不是一份固定 prompt；它是一套让 Codex 在本地文献文件夹中工作的 workflow。

## 这一般叫什么

可以叫：

- **Codex skill**：最通用。
- **Codex workflow skill**：强调它是一套可执行工作流。
- **Literature workflow skill**：最贴近本项目。
- **Paper-reading workflow skill**：更口语，用户容易理解。

本项目推荐叫 **Codex literature workflow skill**。

## 安装

直接 clone 到 Codex skills 目录：

```bash
mkdir -p ~/.codex/skills
git clone <repo-url> ~/.codex/skills/literature-workflow
```

或者下载后复制到：

```text
~/.codex/skills/literature-workflow
```

然后重启 Codex App，或开启新的 Codex CLI 会话。

## 准备文献文件夹

你可以创建任意本地文件夹：

```text
my-literature/
├── papers/
├── notes/
└── references/
```

也可以从空文件夹开始，Codex 会按需创建 `notes/` 和 `references/`。

新 PDF 最简单的放法：直接拖到文献文件夹根目录，作为 inbox。

```text
my-literature/
├── 2602.16720v1.pdf
├── papers/
├── notes/
└── references/
```

已经整理好的 PDF 可以放在 `papers/` 的任意子目录。

不要把 PDF 放进 `notes/`、`references/`、`scripts/`、`skills/`。

## 如何和 Codex 交互

打开你的文献文件夹，然后直接说：

```text
刷新索引
带我读 APEX-SQL
带我读 2602.16720v1
先解释摘要，再讲方法 pipeline
为这篇生成 HTML 笔记
这个 URL 是同一篇论文的项目页，关联到 APEX-SQL
这是技术文档，不是 paper，登记后带我读
```

Codex 会使用 `$literature-workflow` 处理底层细节。

## 本地 AGENTS.md

`AGENTS.md` 不应该作为通用文件强塞给所有用户。它应该由 Codex 针对用户自己的文献库和运行环境生成或调整。

你可以参考 [templates/AGENTS.example.md](templates/AGENTS.example.md)，也可以直接对 Codex 说：

```text
使用 $literature-workflow，为这个文献文件夹创建一个极简 AGENTS.md。
```

你也可以把自己的个性化需求告诉 Codex，例如阅读顺序、笔记风格、研究重点、命名规则、不要做什么。Codex 会自己理解意图，删除废话，只把稳定、必要、精简的规则记录到你本地的 `AGENTS.md`。

如果你有自己的本地运行配置、profile、私有规则文件，可以只留在自己的工作区里，不要放进开源 skill。

## 输出

- HTML 笔记：`notes/<paper-name>.html`
- 论文截图：`notes/assets/`
- 搜索索引：`references/paper_index.jsonl`
- source registry：`references/source_registry.jsonl`

HTML 笔记会结合你和 Codex 的讨论，不是固定模板。

## Source 模型

阅读对象是 entity：`paper`、`tech_doc`、`repo`、`spec`、`dataset`、`slides`、`unknown`。

source 是指向 entity 的入口：PDF、arXiv、DOI、URL、GitHub repo、本地文档、项目页、slides 等。

一个 entity 可以有多个 source。例如同一篇论文可以同时有本地 PDF、arXiv、DOI、项目页和代码仓库。

## 手动命令

通常不需要手动运行脚本，Codex 会帮你调。但也可以自己运行：

```bash
python3 ~/.codex/skills/literature-workflow/scripts/paper_workflow.py --root "$PWD" doctor
python3 ~/.codex/skills/literature-workflow/scripts/paper_workflow.py --root "$PWD" refresh
python3 ~/.codex/skills/literature-workflow/scripts/paper_workflow.py --root "$PWD" find "<论文标题>"
python3 ~/.codex/skills/literature-workflow/scripts/paper_workflow.py --root "$PWD" readpack "<论文标题>"
python3 ~/.codex/skills/literature-workflow/scripts/paper_workflow.py --root "$PWD" render-page "<论文标题>" --page 3 --output notes/assets/pipeline.png --dpi auto
python3 ~/.codex/skills/literature-workflow/scripts/paper_workflow.py --root "$PWD" source link "<论文标题>" --url "<项目页>" --repo "<代码仓库>"
```

## 依赖

必须：

- Python 3.10+

推荐：

- `pypdf`、PyMuPDF 或系统 `pdftotext`：用于 PDF 文本提取
- Ghostscript 或 PyMuPDF：用于 PDF 页面截图
- Pillow：仅在裁剪截图时需要

## 测试

在项目根目录运行：

```bash
python3 tests/smoke_test.py
python3 tests/privacy_scan.py
```

## 隐私

开源仓库不应包含个人论文库、私人笔记、绝对用户路径、本地 runtime profile、生成的索引文件。

测试中包含基础隐私扫描。
