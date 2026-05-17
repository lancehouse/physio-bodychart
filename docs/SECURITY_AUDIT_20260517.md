# Security Audit — PhysioChart TUI
**Date:** 2026-05-17
**Scope:** physio-assessment Python TUI (`physio_assessment/`)
**Auditor:** Claude Code (Sonnet 4.6)

---

## Summary

No significant vulnerabilities found. The app is an offline, single-user clinical tool with no network exposure. The threat surface is very small. All subprocess calls are safe, no unsafe deserialization is used, and patient data is protected by standard Linux home directory permissions.

---

## Checks Performed

### 1. Shell / Command Injection — CLEAR

All `subprocess` calls use **list form** — arguments are separate list elements, never concatenated into a shell string. `shell=True` is not used anywhere.

Three subprocess callsites:

| Location | Command | Args source |
|---|---|---|
| `tui.py:59` | `kitty @ --to <socket> focus-window` | Socket path from `session_current.json` (local IPC only) |
| `tui.py:624` | `physio-bodychart --session <path>` | Session file path from known directory scan |
| `storage.py:save_docx_report` | `pandoc <md_path> -o <docx_path>` | Paths constructed from `Path.stem` of a trusted session file |

None are vulnerable to injection.

### 2. Unsafe Deserialization — CLEAR

Only `json.loads()` is used throughout. No `pickle`, `marshal`, `yaml.load`, `shelve`, or `__reduce__`. JSON parsing cannot execute arbitrary code.

### 3. Code Execution in Data Path — CLEAR

No `eval`, `exec`, or dynamic `__import__` in any data-handling code path.

### 4. Network Exposure — CLEAR

No sockets, no HTTP server, no outbound HTTP clients. The `tui_socket` field in `session_current.json` is a **Unix domain socket path** for kitty terminal remote control (local IPC, not a network port). No ports are opened by the TUI.

### 5. File Permissions on Patient Data — CLEAR (by home dir)

Session JSON files are created with `0644` permissions (world-readable at file level). However, the home directory itself is `0700` (`drwx------`), so other local accounts cannot traverse into `~/Physio-Bodychart/` or `~/.local/share/physio-bodychart/` at all. The inner file permissions are effectively irrelevant.

```
drwx------  /home/lance/                    ← other users blocked here
drwxr-xr-x  /home/lance/Physio-Bodychart/  ← unreachable from outside
-rw-r--r--  .../*_assessment.json           ← 0644, but protected by above
```

If multi-user access to this machine ever became a concern, setting session directories to `0700` and files to `0600` would be the fix. Not required currently.

### 6. Atomic Write Safety — CLEAR

All JSON saves use the atomic pattern:

```python
tmp = path.with_suffix(".json.tmp")
tmp.write_text(json.dumps(data, indent=2))
tmp.replace(path)   # POSIX atomic rename
```

A crash mid-write leaves a `.json.tmp` file orphan but never a partially-written `.json` file. The existing data is never touched until the rename succeeds.

### 7. Path Traversal — CLEAR

Session file paths are discovered by directory scan of `~/Physio-Bodychart/` — the app looks for `{dir}/{dir}_session.json` by pattern. Derived paths (`_assessment.json`, `_objective.json`, `_report.md`, etc.) are constructed by `Path.stem` manipulation from those discovered paths. No user-supplied strings are used to construct file paths.

### 8. SQL Injection — N/A

No SQL anywhere. JSON files are the permanent storage format by design. No database engine is used at runtime.

### 9. Patient Identity Exposure — LOW / ACCEPTABLE

Session directory names follow the pattern `{initials}_{date}_{time}` (e.g. `TP_12_05_2026_1019`). This encodes patient initials in the filesystem. Since the home directory is `0700`, this is only visible to the account owner. Acceptable for a single-user tool.

---

## Issues Fixed During Audit

Two code quality issues were corrected (not security vulnerabilities, but removed potential for future confusion):

1. **`import re` in two function bodies** — moved to module top of `storage.py`
2. **`import subprocess` inside `save_docx_report`** — moved to module top of `storage.py`

These had no security impact but are cleaner at module level.

A separate cleanup pass in the same session also removed ~490 lines of dead code (legacy per-section `save_*`/`load_*` functions that wrote to the GTK-owned `_session.json` instead of the TUI-owned `_assessment.json` — a latent boundary violation that was harmless only because no code called those functions).

---

## Verdict

**No action required.** For an offline, single-user, LAN-isolated clinical tool running under a single Linux account with a `0700` home directory, the security posture is appropriate and proportionate to the threat model.

If the threat model ever changes (e.g. multi-user machine, network share, web-accessible deployment), the primary things to review would be:

- Set session directories/files to `0700`/`0600`
- Review the pandoc subprocess call if session names ever accept untrusted input
- Add authentication if the app gains any network-facing component
