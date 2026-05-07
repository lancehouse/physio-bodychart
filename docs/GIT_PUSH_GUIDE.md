# How to Push Phase 1.11 to GitHub

## Before You Push: Verify Local State

```bash
# Check what's changed
git status

# Review diffs
git diff src/persistence.c
git diff src/canvas.h
git diff src/report.h
git diff src/window.c

# New files
git status --short | grep "^??"
```

## Make Your Commit

```bash
# Stage the C files
git add src/persistence.c src/canvas.h src/report.h src/window.c

# Stage the Python files
git add physio_assessment/watcher.py
git add physio_assessment/storage.py
git add physio_assessment/tui.py

# Stage documentation
git add SESSION_SUMMARY_20260508.md
git add ARCHITECTURE_20260508.md
git add GIT_PUSH_GUIDE.md
git add claude\ instructions.txt  # if it wasn't already tracked

# Create commit
git commit -m "Phase 1.11: Implement session JSON file watcher and GTK↔Python sync

Adds bidirectional file synchronization between GTK body chart and Python TUI:

GTK Changes:
- persistence_save(): Record timestamp for debouncing
- persistence_write_session_current(): Add session_file and session_label fields
- Three new functions: persistence_monitor_start/stop/reload_assessment()
- AppState: Add GFileMonitor and last_own_save_us for file watching
- ReportData: Add history, agg_factors, ease_factors, behaviour_24hr fields
- window.c: Wire monitor at session lifecycle points

Python Changes (NEW):
- watcher.py: BodyChartWatcher with 1-second polling
- storage.py: Atomic load/save for assessment block
- tui.py: Textual TUI with watcher integration

Schema Changes:
- session_current.json: Version 2, add session_file and session_label
- Full session JSON: New 'assessment' block (Python-owned)

Files modified: 4 (persistence.c, canvas.h, report.h, window.c)
Files created: 3 (watcher.py, storage.py, tui.py)
Schema versions bumped: 1 (session_current: 1→2)

Status: Compiles cleanly, ready for live testing. See SESSION_SUMMARY_20260508.md
and ARCHITECTURE_20260508.md for details."
```

## Push to GitHub

```bash
# Check remote
git remote -v

# Push to main (or your working branch)
git push origin main

# Or if using a feature branch
git push origin phase-1.11
```

## After Push: Verify

```bash
# Check GitHub web interface
open https://github.com/yourusername/physio-bodychart

# Or check via CLI
git log --oneline -5
git show HEAD:physio_assessment/watcher.py | head -20
```

## If You Have a Remote Upstream

```bash
# Fetch latest from upstream
git fetch upstream

# Rebase if you're behind
git rebase upstream/main

# Then push to your fork
git push origin main
```

## Emergency Rollback (if something goes wrong)

```bash
# See commit history
git log --oneline

# Revert last commit (keeps it in history)
git revert HEAD

# Or reset to previous state (careful — rewrites history)
git reset --hard HEAD~1
```

## Collaboration Notes

**For Claude Chat Web Review:**
- Push all changes to GitHub
- Share the commit SHA (first 7 chars: `git rev-parse --short HEAD`)
- Link to SESSION_SUMMARY_20260508.md for overview
- Link to ARCHITECTURE_20260508.md for technical details
- Claude Chat can review code directly from GitHub

**File Locations for Reference:**
- GTK source: `physio-bodychart/src/`
- Python source: `physio_assessment/`
- Docs: `SESSION_SUMMARY_20260508.md`, `ARCHITECTURE_20260508.md`
- Original instructions: `claude\ instructions.txt`

---

## One-Command Push (if you're confident)

```bash
git add -A && git commit -m "Phase 1.11: Session JSON file watcher and sync" && git push origin main
```

## Verify Build Still Works After Push

After pushing to GitHub, clone fresh on another machine to verify:

```bash
git clone https://github.com/yourusername/physio-bodychart
cd physio-bodychart/physio-bodychart
ninja -C build

cd ../physio_assessment
python3 -m py_compile watcher.py storage.py tui.py
```

Both should complete without errors.
