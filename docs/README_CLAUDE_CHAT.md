# How to Use These Docs for Claude Chat Web Review

## What to Copy/Paste to Claude Chat

### Option 1: Quick Review (15 minutes)

Paste **JUST THIS FILE** into Claude Chat:
```
CLAUDE_CHAT_ARCHITECTURE_REVIEW.md
```

This has everything Claude Chat needs to understand Phase 1.11:
- What problem it solves
- How file synchronization works
- Safety guarantees
- Architecture questions answered
- Readiness for Phase 2

---

### Option 2: Complete Review (30 minutes)

Paste these in order:

1. **CLAUDE_CHAT_ARCHITECTURE_REVIEW.md** — Overview + questions
2. **SESSION_SUMMARY_20260508.md** — Detailed what was implemented
3. **ARCHITECTURE_20260508.md** — System design + data flow

Then say: *"I've completed Phase 1.11 of the physiotherapy clinical app. This is the file watcher and GTK↔Python synchronization layer. Before I move to Phase 2 (assessment forms), I'd like your review on architecture alignment, safety, and whether we're ready to scale up."*

---

### Option 3: Code Review (45 minutes)

After the above, copy the actual source code files:

```
physio_assessment/watcher.py
physio_assessment/storage.py
physio_assessment/tui.py
```

Ask: *"Here's the Python implementation. Does this match the architecture? Any concerns with the polling strategy or async handling?"*

Then copy one or more of the modified GTK files:
```
src/persistence.c (lines 262-264, 740-813)  — File watcher + reload
src/canvas.h (lines 172-174)                 — AppState additions
src/report.h (lines 14-22)                   — ReportData additions
src/window.c (lines 1737-1740, 1747-1750, etc.) — Wiring
```

---

## Key Discussion Points for Claude Chat

### Architecture Validation

**Ask:** *"Does this file watcher architecture match the independence requirement from the original instructions? Are there any race conditions or coupling issues I should fix before Phase 2?"*

**Context to provide:** Schema ownership model (GTK owns subjective/objective, Python owns assessment).

### Reliability Concerns

**Ask:** *"I'm using polling (1-second interval) instead of inotify. Is this sufficient for a clinical tool? What should I be worried about?"*

**Context:** Latency requirements, failover behavior, concurrent write safety.

### Scaling Questions

**Ask:** *"This works for single-session testing. Will it scale to 50+ sessions? 100+? Any architectural changes needed for that?"*

**Context:** How session scanning works, database integration plans.

### Phase 2 Readiness

**Ask:** *"Am I ready to start Phase 2.1 (assessment form wiring)? Should I do live testing first, or can I parallelize?"*

**Context:** What blockers exist, dependencies between phases.

---

## What Claude Chat Will Need to Know

**Background (from original instructions):**
```
Two independent apps:
- GTK body chart (C) — stylus drawing, pressure-sensitive
- Python TUI (Textual) — assessment + report generation

Shared via JSON file at ~/.local/share/physio-bodychart/session_current.json
Each app reads the active session file and syncs changes in real-time.
```

**What you built:**
```
File watcher that detects when either app writes the session file.
Debouncing prevents feedback loops (app ignores its own writes).
Atomic writes prevent corruption during concurrent access.
Clean ownership: no conflicting writes to same JSON block.
```

**What you need feedback on:**
```
- Is this safe for clinical use?
- Can it handle the full feature set without rewriting?
- Should I refine this before Phase 2?
- Are there security/privacy concerns I missed?
```

---

## Sample Prompt for Claude Chat

Here's a prompt you can paste verbatim:

---

**START PASTE HERE**

I'm building a specialist physiotherapy clinical tool (two-app system: GTK stylus body chart in C, and Python Textual assessment TUI). I've just completed Phase 1.11, which implements the synchronization layer between the two apps via shared session JSON files.

I want your architecture review on safety, reliability, and whether it's ready for Phase 2.

Here's the implementation overview:

[PASTE ARCHITECTURE_REVIEW.md content here]

**Key questions:**
1. Does the file-watcher + polling approach match the "independent apps" requirement from my instructions?
2. Are there race conditions I'm missing with concurrent GTK/Python writes?
3. Can this scale to 100+ patient sessions without major refactoring?
4. Should I do live testing before Phase 2, or can I proceed in parallel?

I can also provide the actual source code (Python watcher/storage, GTK file monitor, JSON schema changes) if you want to review implementation details.

---

**END PASTE**

Then wait for Claude Chat's feedback before pushing to GitHub.

---

## After Claude Chat Review

### If feedback is "looks good, proceed"
1. Do live testing (run both apps, verify file sync works)
2. Push to GitHub (see GIT_PUSH_GUIDE.md)
3. Start Phase 2.1

### If feedback is "refine X first"
1. Fix the issue
2. Re-test locally
3. Re-submit to Claude Chat for re-review
4. Then push to GitHub

### If feedback is "this is a risk"
1. Ask Claude Chat for specific mitigations
2. Implement mitigations
3. Document in code comments and architecture file
4. Re-test
5. Push to GitHub with risk mitigations noted

---

## File Locations (Share These Paths in Chat)

```
Documents for Review:
  /home/lance/Projects/physio-bodychart/CLAUDE_CHAT_ARCHITECTURE_REVIEW.md
  /home/lance/Projects/physio-bodychart/SESSION_SUMMARY_20260508.md
  /home/lance/Projects/physio-bodychart/ARCHITECTURE_20260508.md

Source Code for Review:
  /home/lance/Projects/physio-bodychart/physio_assessment/watcher.py
  /home/lance/Projects/physio-bodychart/physio_assessment/storage.py
  /home/lance/Projects/physio-bodychart/physio_assessment/tui.py

Original Instructions (Context):
  /home/lance/Projects/physio-bodychart/claude instructions.txt

Build Verification:
  ninja -C /home/lance/Projects/physio-bodychart/physio-bodychart/build
  cd /home/lance/Projects/physio-bodychart/physio_assessment && python3 -m py_compile watcher.py storage.py tui.py
```

---

## Quick Status Summary (Copy This to Claude Chat)

**What:** Phase 1.11 — Session JSON file watcher and GTK↔Python sync
**Status:** ✅ Code complete, compiles cleanly, not yet live tested
**What it does:** 
- GTK body chart and Python assessment TUI share data via JSON files
- 1-second polling detects when either app writes
- Atomic writes + debouncing prevent corruption and loops
- Clean ownership: GTK owns strokes/objectives, Python owns assessment text

**Before Phase 2:** Need live testing + Claude review + approval to proceed

---

## Why This Matters

The file watcher is the **critical backbone** of the entire system. If this isn't right:
- Data loss (concurrent writes corrupt JSON)
- Feedback loops (infinite save cycles)
- Data isolation failures (apps interfering with each other's data)

So getting architectural feedback **before** Phase 2 is essential. Phase 2 is 8 sections of assessment forms — all depend on this sync layer working perfectly.

---

## After You Get Feedback

Update your local memory:
```bash
# Add to /home/lance/.claude/projects/.../memory/phase_1_11_complete.md:

## Claude Chat Review Feedback (if applicable)

[Add feedback summary here, how you addressed it]
```

This creates a record for future sessions about what Claude Chat flagged and how you resolved it.

---

That's it! You're ready to get your architecture reviewed. 🎯
