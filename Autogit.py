#!/usr/bin/env python3
"""
GitHub Auto-Commit Bot
Watches local VSCode project folders, scans changes, and auto-commits to GitHub.

Requirements:
    pip install gitpython watchdog requests python-dotenv

Setup:
    1. Create a .env file with your config (see CONFIG section below)
    2. Run: python github_bot.py
"""

import os
import sys
import time
import json
import logging
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional

# --- Install check ---
try:
    import git
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    from dotenv import load_dotenv
except ImportError:
    print("Missing dependencies. Run: pip install gitpython watchdog python-dotenv")
    sys.exit(1)

# ─────────────────────────────────────────────
# CONFIG — edit these or use a .env file
# ─────────────────────────────────────────────
load_dotenv()

CONFIG = {
    # Folders to watch (list of absolute paths)
    "watch_dirs": os.getenv("WATCH_DIRS", "").split(",") if os.getenv("WATCH_DIRS") else [],

    # How long to wait after last change before committing (seconds)
    "debounce_seconds": int(os.getenv("DEBOUNCE_SECONDS", "30")),

    # Auto-push to GitHub after committing
    "auto_push": os.getenv("AUTO_PUSH", "true").lower() == "true",

    # GitHub branch to push to
    "branch": os.getenv("GIT_BRANCH", "main"),

    # Files/folders to ignore (on top of .gitignore)
    "ignore_patterns": [
        "__pycache__", ".DS_Store", "node_modules",
        ".env", "*.pyc", "*.log", ".vscode",
        "dist", "build", ".next", "venv", ".git"
    ],

    # Log file location
    "log_file": os.getenv("LOG_FILE", "github_bot.log"),
}

# ─────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(CONFIG["log_file"]),
        logging.StreamHandler(sys.stdout),
    ]
)
log = logging.getLogger("GitBot")


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def should_ignore(path: str) -> bool:
    """Check if a path matches any ignore pattern."""
    p = Path(path)
    for part in p.parts:
        for pattern in CONFIG["ignore_patterns"]:
            if pattern.startswith("*."):
                if part.endswith(pattern[1:]):
                    return True
            elif part == pattern:
                return True
    return False


def generate_commit_message(repo: git.Repo) -> str:
    """Generate a descriptive commit message based on staged changes."""
    try:
        diff = repo.git.diff("--cached", "--stat")
        changed_files = []
        added = modified = deleted = 0

        for item in repo.index.diff("HEAD"):
            if item.change_type == "A":
                added += 1
                changed_files.append(f"add {Path(item.a_path).name}")
            elif item.change_type == "M":
                modified += 1
                changed_files.append(f"update {Path(item.a_path).name}")
            elif item.change_type == "D":
                deleted += 1

        # Also check for new untracked files that were staged
        for item in repo.index.diff(None):
            pass  # already counted above

        parts = []
        if added:
            parts.append(f"add {added} file{'s' if added > 1 else ''}")
        if modified:
            parts.append(f"update {modified} file{'s' if modified > 1 else ''}")
        if deleted:
            parts.append(f"remove {deleted} file{'s' if deleted > 1 else ''}")

        summary = ", ".join(parts) if parts else "update project files"

        # Add top-level detail
        if changed_files:
            detail = ", ".join(changed_files[:3])
            if len(changed_files) > 3:
                detail += f" (+{len(changed_files) - 3} more)"
            msg = f"{summary}: {detail}"
        else:
            msg = summary

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        return f"[auto] {msg} — {timestamp}"

    except Exception:
        return f"[auto] update files — {datetime.now().strftime('%Y-%m-%d %H:%M')}"


def get_repo(path: str) -> Optional[git.Repo]:
    """Find the git repo for a given path."""
    try:
        return git.Repo(path, search_parent_directories=True)
    except git.InvalidGitRepositoryError:
        log.warning(f"No git repo found at: {path}")
        return None


def stage_and_commit(repo: git.Repo, project_path: str) -> bool:
    """Stage all changes and commit."""
    try:
        # Stage all changes (respects .gitignore)
        repo.git.add(A=True)

        # Check if there's anything to commit
        if not repo.is_dirty(index=True, untracked_files=True):
            log.info(f"Nothing to commit in: {project_path}")
            return False

        # Check staged changes
        staged = repo.index.diff("HEAD") if repo.head.is_valid() else repo.index.diff(None)
        if not staged and not repo.untracked_files:
            log.info(f"No staged changes in: {project_path}")
            return False

        msg = generate_commit_message(repo)
        repo.index.commit(msg)
        log.info(f"✅ Committed: {msg}")
        return True

    except Exception as e:
        log.error(f"Commit failed: {e}")
        return False


def push_to_github(repo: git.Repo, branch: str) -> bool:
    """Push commits to GitHub."""
    try:
        origin = repo.remote(name="origin")
        origin.push(refspec=f"{branch}:{branch}")
        log.info(f"🚀 Pushed to GitHub ({branch})")
        return True
    except Exception as e:
        log.error(f"Push failed: {e}")
        return False


def scan_and_report(project_path: str) -> dict:
    """Scan a project directory and return a summary."""
    summary = {
        "path": project_path,
        "files": [],
        "languages": {},
        "total_lines": 0,
    }

    ext_map = {
        ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
        ".jsx": "React", ".tsx": "React/TS", ".html": "HTML",
        ".css": "CSS", ".scss": "SCSS", ".json": "JSON",
        ".md": "Markdown", ".go": "Go", ".rs": "Rust",
        ".java": "Java", ".cpp": "C++", ".c": "C",
    }

    for root, dirs, files in os.walk(project_path):
        # Skip ignored directories in-place
        dirs[:] = [d for d in dirs if not should_ignore(os.path.join(root, d))]

        for file in files:
            fpath = os.path.join(root, file)
            if should_ignore(fpath):
                continue

            ext = Path(file).suffix.lower()
            lang = ext_map.get(ext)
            if lang:
                summary["languages"][lang] = summary["languages"].get(lang, 0) + 1
                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        lines = sum(1 for _ in f)
                    summary["total_lines"] += lines
                    summary["files"].append({"name": file, "lang": lang, "lines": lines})
                except Exception:
                    pass

    return summary


# ─────────────────────────────────────────────
# WATCHER
# ─────────────────────────────────────────────

class ProjectWatcher(FileSystemEventHandler):
    """Watches a project folder and debounces commits."""

    def __init__(self, project_path: str):
        self.project_path = project_path
        self.repo = get_repo(project_path)
        self._last_event = 0
        self._timer = None
        self._pending = False

    def on_any_event(self, event):
        if event.is_directory:
            return
        if should_ignore(event.src_path):
            return

        self._last_event = time.time()

        if not self._pending:
            self._pending = True
            self._schedule_commit()

    def _schedule_commit(self):
        """Wait for debounce period, then commit."""
        import threading

        def _run():
            while True:
                time.sleep(1)
                elapsed = time.time() - self._last_event
                if elapsed >= CONFIG["debounce_seconds"]:
                    self._do_commit()
                    self._pending = False
                    break

        t = threading.Thread(target=_run, daemon=True)
        t.start()

    def _do_commit(self):
        if not self.repo:
            return

        log.info(f"📁 Processing changes in: {self.project_path}")

        # Scan project
        report = scan_and_report(self.project_path)
        langs = ", ".join(f"{l}({c})" for l, c in report["languages"].items())
        log.info(f"   Languages: {langs or 'none detected'}")
        log.info(f"   Total lines: {report['total_lines']}")

        # Commit
        committed = stage_and_commit(self.repo, self.project_path)

        # Push
        if committed and CONFIG["auto_push"]:
            push_to_github(self.repo, CONFIG["branch"])


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def add_project(path: str):
    """Add a new project to watch list."""
    path = os.path.abspath(os.path.expanduser(path))
    if path not in CONFIG["watch_dirs"]:
        CONFIG["watch_dirs"].append(path)
        log.info(f"Added project: {path}")
    return path


def run():
    """Start the bot."""
    if not CONFIG["watch_dirs"]:
        # Interactive setup if no dirs configured
        print("\n🤖 GitHub Auto-Commit Bot")
        print("─" * 40)
        print("No projects configured. Let's add some!\n")

        while True:
            path = input("Enter project folder path (or press Enter to finish): ").strip()
            if not path:
                break
            full_path = os.path.abspath(os.path.expanduser(path))
            if os.path.isdir(full_path):
                add_project(full_path)
                print(f"  ✓ Added: {full_path}")
            else:
                print(f"  ✗ Directory not found: {full_path}")

        if not CONFIG["watch_dirs"]:
            print("No projects added. Exiting.")
            sys.exit(0)

    # Validate repos
    valid_projects = []
    for p in CONFIG["watch_dirs"]:
        p = p.strip()
        if not p:
            continue
        if not os.path.isdir(p):
            log.warning(f"Directory not found, skipping: {p}")
            continue
        repo = get_repo(p)
        if not repo:
            log.warning(f"Not a git repo (run 'git init' first): {p}")
            continue
        valid_projects.append(p)

    if not valid_projects:
        log.error("No valid git projects found. Exiting.")
        sys.exit(1)

    # Start watchers
    observer = Observer()
    watchers = []

    for project_path in valid_projects:
        log.info(f"👀 Watching: {project_path}")
        report = scan_and_report(project_path)
        langs = ", ".join(f"{l}({c})" for l, c in report["languages"].items())
        log.info(f"   {len(report['files'])} source files | {report['total_lines']} lines | {langs}")

        handler = ProjectWatcher(project_path)
        watchers.append(handler)
        observer.schedule(handler, project_path, recursive=True)

    observer.start()
    log.info(f"\n✅ Bot running! Watching {len(valid_projects)} project(s).")
    log.info(f"   Debounce: {CONFIG['debounce_seconds']}s | Auto-push: {CONFIG['auto_push']}")
    log.info("   Press Ctrl+C to stop.\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log.info("Stopping bot...")
        observer.stop()

    observer.join()
    log.info("Bot stopped.")


if __name__ == "__main__":
    # Allow passing project paths as CLI args
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            add_project(arg)

    run()