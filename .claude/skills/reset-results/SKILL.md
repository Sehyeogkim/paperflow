---
name: reset-results
description: Clear ONE paperflow project's generated output so "Create Journal"/generate runs fresh again. Given a project name, deletes only that project's <project>/_paperflow_out/ (the compiled paper + plan/diagnose/claim-graph/figure/citation artifacts) while keeping all inputs. Use when a project was already generated and you want to re-run it from scratch. Never touches inputs.
argument-hint: "[project name, e.g. coronary_plaque_VI_demo]"
---

# /reset-results — wipe one project's generated output, keep inputs

A paperflow project shows its OLD result the moment you open it because the backend
sets `paper_ready = (<project>/_paperflow_out/paper.pdf exists)`. To watch a brand-new
generation, that output dir must be gone. This skill removes **only** `_paperflow_out/`
for the named project and leaves every input untouched.

## What gets deleted vs kept

- **DELETE** `<project>/_paperflow_out/` (everything: `paper.pdf`/`.tex`/`.aux`/`.log`,
  `claim_graph.json`, `contracts.json`, `figure_spec.json`, `reference_*.json`,
  `requirement_report.json`, `validation_report.json`, `run_manifest.json`, the section `.md`s).
- **KEEP** all inputs: `main/0_journal_info.md`, `main/1_coremessage.md`, `main/3_outline.md`,
  `main/answer.json`, `main/data_notes.json`, `main/_ui_state.json`, `main/project.json`,
  and the whole `data/` directory. Never delete these.

## Steps

1. **Resolve the project dir.** Base = `projects/paperflow/projects/`. Match `$ARGUMENTS`
   against the folder names case-insensitively (the macOS FS is case-insensitive, so
   `coronary_plaque_VI_demo` ↔ `coronary_plaque_vi_demo` are the same dir). If no match or
   the name is ambiguous, list `projects/*/` and ASK which one. Never guess across projects.

2. **Bail out safely if nothing to do.** If `<project>/_paperflow_out/` doesn't exist, say
   "이미 결과 없음 (fresh 상태)" and stop — don't touch inputs.

3. **Back up, then delete.** Copy `_paperflow_out/` to the session scratchpad first (cheap
   reversibility), then `rm -rf` it:
   ```bash
   PROJ="<abs path to project>"
   SP="<scratchpad>/reset_backup/$(basename "$PROJ")"
   mkdir -p "$SP" && cp -R "$PROJ/_paperflow_out" "$SP/" 2>/dev/null
   rm -rf "$PROJ/_paperflow_out"
   ```
   Note in the report whether it was git-tracked (recoverable via `git checkout`) or untracked.

4. **Verify.** Confirm `_paperflow_out/` is gone and the input files in step "KEEP" still exist.
   `paper_ready` is now false, so opening the project shows the input screen and Create Journal
   runs fresh.

5. **Refresh the UI if the server is up.** If `paperflow serve` is running (port 8765) and a
   browser is open on it, reload the page (or re-open the project card) so the dashboard reflects
   `paper_ready=false`. The browser's in-memory inputs are unaffected; everything is on disk.

## Guardrails

- Only ever remove `_paperflow_out/`. Do **not** delete `main/`, `data/`, or any input file.
- One project per invocation. If the user names several, confirm the list before deleting.
- Don't restart the server or change models — this skill only clears output.
