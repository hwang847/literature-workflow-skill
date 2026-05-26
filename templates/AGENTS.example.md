@README.md

# Literature Workspace Rules

- This file is a local example for Codex. Edit it for your own literature folder.
- Users may describe personal preferences in natural language; Codex should infer intent and keep only compact durable rules here.
- Use `$literature-workflow` as the executable workflow.
- Workspace root is the current directory containing this `AGENTS.md`.
- This is a paper/document library, not an app; do not start servers, build UI, move, rename, or delete files unless explicitly asked.
- New PDFs belong in the root inbox by default; organized PDFs may live under `papers/`.
- After new files appear, refresh the index.
- Treat readable objects as entities: `paper`, `tech_doc`, `repo`, `spec`, `dataset`, `slides`, or `unknown`.
- Treat PDF/arXiv/DOI/URL/GitHub/local docs as sources; use `references/source_registry.jsonl` through the workflow for multi-source entities or non-paper documents.
- Prefer local evidence. Use web only when asked, approved, or needed to download a requested source.
- Reading focus: translate or summarize the abstract first when present, then explain thesis, high-value ideas, method/pipeline, and implementation implications.
- Skip experiments/results unless explicitly asked.
- Avoid reusable prose templates. Headings and note structure should follow the document, the discussion, and the user's current question.
- Mark missing details clearly; label nontrivial interpretation as inference.
- HTML notes require an explicit note trigger, use the workflow filename rule, stay minimal, and should be updated if later discussion changes the understanding.
