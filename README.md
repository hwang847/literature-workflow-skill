# Literature Workflow Skill

[中文说明](README.zh-CN.md)

A seed Codex workflow skill for fast paper reading, method-pipeline discussion, source management, and personalized HTML notes.

This repository gives you the starting point: a basic working structure and a basic reading workflow. Your personal preferences and richer workflow should evolve through conversation with Codex in your own workspace.

## Quickstart

Install:

```bash
mkdir -p ~/.codex/skills
git clone https://github.com/hwang847/literature-workflow-skill.git ~/.codex/skills/literature-workflow
```

Restart Codex App or open a new Codex CLI session.

Open the folder you want to use as your literature workspace, or `cd` into it, then tell Codex:

```text
Use $literature-workflow to set up this literature workspace.
```

You do not need to create folders, initialize indexes, write or maintain `AGENTS.md`, or check Python packages yourself. Codex will prepare the workspace and keep the local rules compact over time.

Then drop PDFs into the workspace and talk naturally:

```text
Refresh the index.
Read this paper with me.
Explain the method pipeline.
Generate an HTML note.
```

## What Codex Prepares

```text
your-workspace/
├── papers/                 # optional organized PDFs
├── notes/                  # HTML notes
│   └── assets/             # screenshots
├── references/             # index and source registry
└── AGENTS.md               # local Codex preferences
```

New PDFs can stay in the workspace root as inbox items. Codex can also work with PDFs already placed under `papers/`.

## Personalize It

Tell Codex what you care about:

```text
My notes should focus on implementation details and pipeline reconstruction.
Prefer concise HTML notes.
Skip experiments unless I ask.
Use Chinese for reading and notes.
Track project pages and GitHub repos as sources.
```

Codex will turn stable preferences into local `AGENTS.md` rules, and update them later when your workflow changes. Think of this skill as the seed; your local `AGENTS.md` is where the workflow becomes yours.

## Source Model

A read target is an entity: `paper`, `tech_doc`, `repo`, `spec`, `dataset`, `slides`, or `unknown`.

A source points to an entity: PDF, arXiv, DOI, URL, GitHub repo, local document, project page, slides, etc.

One entity can have multiple sources. For example, a paper may have a local PDF, arXiv URL, DOI, project page, and GitHub repo.

## For Maintainers

Run tests from this repository root:

```bash
python3 tests/smoke_test.py
python3 tests/privacy_scan.py
```
