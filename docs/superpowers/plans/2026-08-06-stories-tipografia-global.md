# Stories Global Typography Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add one persistent, global serif/sans typography choice to Stories previews and PNG exports.

**Architecture:** Store `typography` on the existing Stories document object. A single resolver returns the CSS and Canvas font stacks; the inspector changes the document value, re-renders slides, and records an undo mutation.

**Tech Stack:** Static HTML, CSS, browser JavaScript, Canvas 2D, Python unittest.

## Global Constraints

- Modify only Stories; Tweet is unchanged.
- Serif remains the default.
- Sans uses native system fallbacks and no new external font download.
- The same selected typeface must drive DOM and Canvas PNG output.

---

### Task 1: Cover the typography contract

**Files:**
- Modify: `tests/test_editor_undo.py`
- Modify: `tests/test_editor_shell.py`
- Modify: `templates/stories_editor.html`

**Interfaces:**
- Produces `doc.typography` with values `serif` or `sans`.
- Consumes the existing `saveDoc`, undo snapshot, DOM renderer, and Canvas renderer.

- [ ] **Step 1: Write failing tests**

```python
def test_stories_global_typography_is_persistent_and_undoable(self) -> None:
    html = TEMPLATES["stories"]
    for marker in (
        "typography: doc.typography || 'serif'",
        "function setStoriesTypography(nextTypography)",
        "recordEditorMutation('typography')",
        "doc.typography = nextTypography",
    ):
        self.assertIn(marker, html)
```

```python
def test_stories_typography_selector_matches_canvas_export(self) -> None:
    html = (PROJECT_ROOT / "templates" / "stories_editor.html").read_text(encoding="utf-8")
    for marker in (
        'id="stories-typography"',
        'value="serif"',
        'value="sans"',
        "function getStoriesTypeface()",
        "fontFamily: getStoriesTypeface().canvasFamily",
    ):
        self.assertIn(marker, html)
```

- [ ] **Step 2: Run the focused tests and verify they fail**

Run: `.venv/bin/python -m unittest tests.test_editor_undo tests.test_editor_shell -v`

Expected: failures because the global typography state and selector do not yet exist.

- [ ] **Step 3: Implement the smallest global state and UI change**

Add the selector to the Stories Documento inspector, a typeface resolver, document migration/default, snapshot capture/restore, DOM application, and Canvas style resolution.

- [ ] **Step 4: Run the focused tests and verify they pass**

Run: `.venv/bin/python -m unittest tests.test_editor_undo tests.test_editor_shell -v`

Expected: PASS.

- [ ] **Step 5: Run regression verification**

Run: `.venv/bin/python -m unittest discover -s tests -v && .venv/bin/python -m py_compile scripts/*.py && git diff --check`

Expected: full suite, compiler check, and diff check pass.
