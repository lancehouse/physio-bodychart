"""
File watcher for GTK body chart session JSON integration.

Monitors session_current.json for active-session changes and the active
session_file for GTK content updates. Calls callbacks for session switches
and chart updates.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Callable, Awaitable

SESSION_CURRENT = Path.home() / ".local/share/physio-bodychart/session_current.json"
POLL_INTERVAL = 1.0  # seconds


class BodyChartWatcher:
    """
    Watches session_current.json for active-session changes,
    then watches the active session_file for GTK content updates.

    Calls on_session_switch(session_data) and on_chart_update(session_data).
    """

    def __init__(
        self,
        on_session_switch: Callable[[dict], Awaitable[None]],
        on_chart_update: Callable[[dict], Awaitable[None]],
    ):
        self.on_session_switch = on_session_switch
        self.on_chart_update = on_chart_update
        self._current_session_file: Path | None = None
        self._task: asyncio.Task | None = None
        self._last_mtime: dict[Path, float] = {}
        self.logger = logging.getLogger(__name__)

    def start(self):
        """Start the polling loop."""
        if self._task:
            return
        self._task = asyncio.get_event_loop().create_task(self._poll_loop())

    def stop(self):
        """Stop the polling loop."""
        if self._task:
            self._task.cancel()
            self._task = None

    async def _poll_loop(self):
        """Main polling loop: check both files every POLL_INTERVAL seconds."""
        while True:
            try:
                await self._check(SESSION_CURRENT, self._handle_session_current)
                if self._current_session_file:
                    await self._check(
                        self._current_session_file, self._handle_session_file
                    )
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in watcher poll loop: {e}")

            await asyncio.sleep(POLL_INTERVAL)

    async def _check(self, path: Path, handler: Callable[[dict], Awaitable[None]]):
        """Check if file has been modified and call handler if so."""
        try:
            mtime = path.stat().st_mtime
            if self._last_mtime.get(path) != mtime:
                self._last_mtime[path] = mtime
                data = json.loads(path.read_text())
                await handler(data)
        except FileNotFoundError:
            pass
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse JSON from {path}: {e}")

    async def _handle_session_current(self, data: dict):
        """Handle session_current.json change: detect session switch."""
        session_file = data.get("session_file")
        if not session_file:
            return

        new_path = Path(session_file)
        if new_path != self._current_session_file:
            self._current_session_file = new_path
            self._last_mtime[new_path] = 0  # force read on next poll
            await self.on_session_switch(data)

    async def _handle_session_file(self, data: dict):
        """Handle session_file change: GTK updated chart data."""
        await self.on_chart_update(data)
