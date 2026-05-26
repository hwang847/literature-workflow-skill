# Literature Workflow Skill

[中文说明](README.zh-CN.md)

Default documentation and examples are in English. Chinese usage is optional and supported through [README.zh-CN.md](README.zh-CN.md) or a local `AGENTS.md` preference.

Literature Workflow Skill is a Codex workflow skill for reading papers and technical documents from a local folder.

It helps Codex find local PDFs, map copied titles to numbered files, manage multiple sources for the same work, discuss method pipelines, render paper figures, and generate concise personalized HTML notes from the conversation.

## What This Is Called

This project is best described as a **Codex literature workflow skill**:

- **Codex skill** because it is installed under `~/.codex/skills/`.
- **Workflow skill** because it gives Codex a repeatable process, not just a prompt.
- **Literature workflow** because it is designed for papers, technical docs, project pages, and related research sources.

## Install

Clone this repository directly into your Codex skills directory:

```bash
mkdir -p ~/.codex/skills
git clone <repo-url> ~/.codex/skills/literature-workflow
```

Or download the folder and copy it to:

```text
~/.codex/skills/literature-workflow
```

Restart Codex App or start a new Codex CLI session so the skill can be discovered.

## Prepare a Literature Folder

Create or open any local folder for your papers:

```text
my-literature/
├── papers/
├── notes/
└── references/
```

You may also start with an empty folder. Codex can create `notes/` and `references/` as needed.

Put new PDFs in the folder root as inbox items:

```text
my-literature/
├── 2602.16720v1.pdf
├── papers/
├── notes/
└── references/
```

Organized PDFs may live anywhere under `papers/`.

Do not put PDFs under `notes/`, `references/`, `scripts/`, or `skills/`.

## Use With Codex

Open the literature folder in Codex and speak naturally:

```text
Refresh the index.
Read APEX-SQL with me.
Read 2602.16720v1.
Explain the abstract first, then the method pipeline.
Generate an HTML note for this paper.
This URL is the project page for APEX-SQL; link it to the same entity.
This is a technical document, not a paper; register it and read it with me.
```

Codex will use `$literature-workflow` to handle the local mechanics.

## Local AGENTS.md

`AGENTS.md` is intentionally not bundled as a universal rule file. It should be generated or edited for each user's own literature folder and runtime environment.

Use [templates/AGENTS.example.md](templates/AGENTS.example.md) as a starting point, or ask Codex:

```text
Use $literature-workflow and create a minimal AGENTS.md for this literature folder.
```

You can also tell Codex your personal reading preferences, note style, research focus, naming rules, and constraints. Codex should understand the intent, remove noise, and record only the compact durable rules in your local `AGENTS.md`.

Private runtime imports such as local profile files should stay in your own workspace, not in this open-source skill.

English is the default language for the open-source skill. If you prefer Chinese or another language, tell Codex and let it record that preference in your local `AGENTS.md`.

## Output

- HTML notes: `notes/<paper-name>.html`
- Figure screenshots: `notes/assets/`
- Search index: `references/paper_index.jsonl`
- Source registry: `references/source_registry.jsonl`

HTML notes are intentionally concise and discussion-aware. They should reflect what you and Codex clarified, not a fixed review template.

## Source Model

A read target is an entity: `paper`, `tech_doc`, `repo`, `spec`, `dataset`, `slides`, or `unknown`.

A source points to an entity: PDF, arXiv, DOI, URL, GitHub repo, local document, project page, slides, etc.

One entity can have multiple sources. For example, a paper may have a local PDF, arXiv URL, DOI, project page, and GitHub repo.

## Manual CLI

Codex normally runs these for you, but manual commands are available:

```bash
python3 ~/.codex/skills/literature-workflow/scripts/paper_workflow.py --root "$PWD" doctor
python3 ~/.codex/skills/literature-workflow/scripts/paper_workflow.py --root "$PWD" refresh
python3 ~/.codex/skills/literature-workflow/scripts/paper_workflow.py --root "$PWD" find "<title>"
python3 ~/.codex/skills/literature-workflow/scripts/paper_workflow.py --root "$PWD" readpack "<title>"
python3 ~/.codex/skills/literature-workflow/scripts/paper_workflow.py --root "$PWD" render-page "<title>" --page 3 --output notes/assets/pipeline.png --dpi auto
python3 ~/.codex/skills/literature-workflow/scripts/paper_workflow.py --root "$PWD" source link "<title>" --url "<project-url>" --repo "<repo-url>"
```

## Dependencies

Required:

- Python 3.10+

Recommended:

- `pypdf`, PyMuPDF, or system `pdftotext` for PDF text extraction
- Ghostscript or PyMuPDF for PDF page screenshots
- Pillow only if image cropping is used

## Test

From this repository root:

```bash
python3 tests/smoke_test.py
python3 tests/privacy_scan.py
```

## Privacy

This repository should not include personal paper libraries, private notes, absolute user paths, local runtime profiles, or generated indexes.

The included tests scan for common private-path leaks.
