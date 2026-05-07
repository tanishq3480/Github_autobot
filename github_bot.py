#!/usr/bin/env python3
"""
GitHub Auto-Commit Bot
Watches local VSCode project folders, scans changes, and auto-commits to GitHub.

Requirements:
    pip install gitpython watchdog python-dotenv

Setup:
    1. Create a .env file with your config (see CONFIG section below)
    2. Run: python github_bot.py
"""

import os
import sys
import time
import logging
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional

# ─── Fix Windows terminal Unicode (must be before any print/logging) ───
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

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
    "watch_dirs": os.getenv("WATCH_DIRS", "").split(",") if os.getenv("WATCH_DIRS") else [],
    "debounce_seconds": int(os.getenv("DEBOUNCE_SECONDS", "30")),
    "auto_push": os.getenv("AUTO_PUSH", "true").lower() == "true",
    "branch": os.getenv("GIT_BRANCH", "main"),
    "ignore_patterns": [
        "__pycache__", ".DS_Store", "node_modules",
        ".env", "*.pyc", "*.log", ".vscode",
        "dist", "build", ".next", "venv", ".git",
        ".venv", "*.egg-info",
    ],
    "log_file": os.getenv("LOG_FILE", "github_bot.log"),
}

# ─────────────────────────────────────────────
# LOGGING — UTF-8 safe on Windows
# ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(CONFIG["log_file"], encoding="utf-8"),
        logging.StreamHandler(stream=sys.stdout),
    ],
)
log = logging.getLogger("GitBot")


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def should_ignore(path: str) -> bool:
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
    try:
        changed_files = []
        added = modified = deleted = 0

        try:
            diffs = repo.index.diff("HEAD")
        except Exception:
            diffs = []

        for item in diffs:
            if item.change_type == "A":
                added += 1
                changed_files.append(f"add {Path(item.a_path).name}")
            elif item.change_type == "M":
                modified += 1
                changed_files.append(f"update {Path(item.a_path).name}")
            elif item.change_type == "D":
                deleted += 1

        parts = []
        if added:
            parts.append(f"add {added} file{'s' if added > 1 else ''}")
        if modified:
            parts.append(f"update {modified} file{'s' if modified > 1 else ''}")
        if deleted:
            parts.append(f"remove {deleted} file{'s' if deleted > 1 else ''}")

        summary = ", ".join(parts) if parts else "update project files"

        if changed_files:
            detail = ", ".join(changed_files[:3])
            if len(changed_files) > 3:
                detail += f" (+{len(changed_files) - 3} more)"
            msg = f"{summary}: {detail}"
        else:
            msg = summary

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        return f"[auto] {msg} - {timestamp}"

    except Exception:
        return f"[auto] update files - {datetime.now().strftime('%Y-%m-%d %H:%M')}"


def get_repo(path: str) -> Optional[git.Repo]:
    try:
        return git.Repo(path, search_parent_directories=True)
    except Exception:
        return None


def init_repo(path: str) -> Optional[git.Repo]:
    """Initialize a new git repo and create a default .gitignore."""
    try:
        repo = git.Repo.init(path)
        log.info(f"[git init] Initialized repo at: {path}")
        gitignore_path = os.path.join(path, ".gitignore")
        if not os.path.exists(gitignore_path):
            with open(gitignore_path, "w") as f:
                f.write(
                    "__pycache__/\n*.pyc\n*.pyo\n.env\n.venv/\nvenv/\n"
                    "node_modules/\ndist/\nbuild/\n.DS_Store\n*.log\n.vscode/\n"
                )
            log.info(f"[git init] Created default .gitignore")
        return repo
    except Exception as e:
        log.error(f"[git init] Failed at {path}: {e}")
        return None


def stage_and_commit(repo: git.Repo, project_path: str) -> bool:
    try:
        repo.git.add(A=True)

        if not repo.is_dirty(index=True, untracked_files=True):
            log.info(f"Nothing to commit in: {project_path}")
            return False

        msg = generate_commit_message(repo)
        repo.index.commit(msg)
        log.info(f"[OK] Committed: {msg}")
        return True

    except Exception as e:
        log.error(f"Commit failed: {e}")
        return False


def push_to_github(repo: git.Repo, branch: str) -> bool:
    try:
        origin = repo.remote(name="origin")
        origin.push(refspec=f"{branch}:{branch}")
        log.info(f"[OK] Pushed to GitHub ({branch})")
        return True
    except git.exc.GitCommandError as e:
        log.error(f"Push failed - {e.stderr.strip() if e.stderr else str(e)}")
        return False
    except Exception as e:
        log.error(f"Push failed: {e}")
        return False


def initial_sync(repo: git.Repo, project_path: str) -> None:
    """
    On startup, commit and push ALL existing uncommitted work in a project.
    Handles both brand-new repos (no commits yet) and repos with existing history.
    """
    name = Path(project_path).name
    print(f"  [SYNC] Scanning: {name} ...")

    try:
        # Stage everything
        repo.git.add(A=True)

        # Check if there is anything to commit
        has_untracked = bool(repo.untracked_files)
        try:
            is_dirty = repo.is_dirty(index=True, untracked_files=True)
        except Exception:
            is_dirty = False

        # For a brand-new repo with no commits yet, check the index directly
        try:
            head_valid = repo.head.is_valid()
        except Exception:
            head_valid = False

        nothing_staged = False
        if head_valid:
            staged = repo.index.diff("HEAD")
            nothing_staged = not staged and not has_untracked and not is_dirty
        else:
            # New repo — anything in the index counts
            nothing_staged = not repo.index.entries

        if nothing_staged:
            print(f"  [SYNC] {name}: already up to date, nothing to commit.")
            return

        # Build a richer initial commit message
        file_count = 0
        lang_counts = {}
        ext_map = {
            ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
            ".jsx": "React", ".tsx": "React/TS", ".html": "HTML",
            ".css": "CSS", ".scss": "SCSS", ".json": "JSON",
            ".md": "Markdown", ".go": "Go", ".rs": "Rust",
            ".java": "Java", ".cpp": "C++", ".c": "C",
        }
        for root, dirs, files in os.walk(project_path):
            dirs[:] = [d for d in dirs if not should_ignore(os.path.join(root, d))]
            for f in files:
                fpath = os.path.join(root, f)
                if should_ignore(fpath):
                    continue
                ext = Path(f).suffix.lower()
                lang = ext_map.get(ext)
                if lang:
                    file_count += 1
                    lang_counts[lang] = lang_counts.get(lang, 0) + 1

        lang_summary = ", ".join(f"{l}({c})" for l, c in lang_counts.items())
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

        if head_valid:
            msg = f"[auto-sync] commit existing work - {file_count} files ({lang_summary}) - {timestamp}"
        else:
            msg = f"[auto-sync] initial commit - {file_count} files ({lang_summary}) - {timestamp}"

        repo.index.commit(msg)
        log.info(f"[SYNC] Committed: {msg}")

        # Push if remote exists
        if CONFIG["auto_push"]:
            try:
                origin = repo.remote(name="origin")
                branch = CONFIG["branch"]
                # For new repos, set upstream tracking on first push
                if not head_valid:
                    repo.git.push("--set-upstream", "origin", branch)
                else:
                    origin.push(refspec=f"{branch}:{branch}")
                log.info(f"[SYNC] Pushed '{name}' to GitHub ({branch})")
            except git.exc.GitCommandError as e:
                err = e.stderr.strip() if e.stderr else str(e)
                log.warning(f"[SYNC] Push skipped for '{name}': {err}")
                print(f"  [!]  Could not push '{name}' - make sure remote 'origin' is set and branch '{CONFIG['branch']}' exists on GitHub.")
            except Exception as e:
                log.warning(f"[SYNC] Push skipped for '{name}': {e}")

    except Exception as e:
        log.error(f"[SYNC] Failed for '{name}': {e}")


def scan_and_report(project_path: str) -> dict:
    summary = {"path": project_path, "files": [], "languages": {}, "total_lines": 0}
    ext_map = {
        ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
        ".jsx": "React", ".tsx": "React/TS", ".html": "HTML",
        ".css": "CSS", ".scss": "SCSS", ".json": "JSON",
        ".md": "Markdown", ".go": "Go", ".rs": "Rust",
        ".java": "Java", ".cpp": "C++", ".c": "C",
    }
    for root, dirs, files in os.walk(project_path):
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
    def __init__(self, project_path: str, repo: git.Repo):
        self.project_path = project_path
        self.repo = repo
        self._last_event = 0
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
        import threading
        def _run():
            while True:
                time.sleep(1)
                if time.time() - self._last_event >= CONFIG["debounce_seconds"]:
                    self._do_commit()
                    self._pending = False
                    break
        threading.Thread(target=_run, daemon=True).start()

    def _do_commit(self):
        log.info(f"[>>] Processing changes in: {self.project_path}")
        report = scan_and_report(self.project_path)
        langs = ", ".join(f"{l}({c})" for l, c in report["languages"].items())
        log.info(f"     Languages: {langs or 'none detected'} | Lines: {report['total_lines']}")
        committed = stage_and_commit(self.repo, self.project_path)
        if committed and CONFIG["auto_push"]:
            push_to_github(self.repo, CONFIG["branch"])


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def add_project(path: str):
    path = os.path.abspath(os.path.expanduser(path))
    if path not in CONFIG["watch_dirs"]:
        CONFIG["watch_dirs"].append(path)
    return path


def run():
    print("\n=== GitHub Auto-Commit Bot ===")

    if not CONFIG["watch_dirs"]:
        print("No projects configured. Let's add some!\n")
        while True:
            path = input("Enter project folder path (or press Enter to finish): ").strip()
            if not path:
                break
            full_path = os.path.abspath(os.path.expanduser(path))
            if os.path.isdir(full_path):
                add_project(full_path)
                print(f"  [+] Added: {full_path}")
            else:
                print(f"  [!] Directory not found: {full_path}")

        if not CONFIG["watch_dirs"]:
            print("No projects added. Exiting.")
            sys.exit(0)

    # Validate / auto-init repos
    valid_projects = []
    skipped = []

    for p in CONFIG["watch_dirs"]:
        p = p.strip()
        if not p or not os.path.isdir(p):
            if p:
                log.warning(f"Directory not found, skipping: {p}")
            continue

        repo = get_repo(p)

        if not repo:
            name = Path(p).name
            print(f"\n[!] '{name}' has no git repo.")
            answer = input(f"    Run 'git init' here automatically? (y/n): ").strip().lower()
            if answer == "y":
                repo = init_repo(p)
                if repo:
                    print(f"    [+] Initialized git repo in: {p}")
                    remote = input(f"    Add GitHub remote URL? (paste URL or Enter to skip): ").strip()
                    if remote:
                        try:
                            repo.create_remote("origin", remote)
                            print(f"    [+] Remote 'origin' set to: {remote}")
                        except Exception as e:
                            print(f"    [!] Could not set remote: {e}")
                else:
                    skipped.append(p)
                    continue
            else:
                log.warning(f"Skipping (no git repo): {p}")
                skipped.append(p)
                continue

        valid_projects.append((p, repo))

    if not valid_projects:
        log.error("No valid git projects to watch. Exiting.")
        if skipped:
            print("\nTo fix skipped projects, run inside each folder:")
            for s in skipped:
                print(f"  cd \"{s}\" && git init")
        sys.exit(1)

    # Step 1: Initial sync - commit all existing uncommitted work
    print(f"\n[STEP 1/2] Syncing existing work in {len(valid_projects)} project(s)...")
    for project_path, repo in valid_projects:
        initial_sync(repo, project_path)
    print("[STEP 1/2] Initial sync complete.\n")

    # Step 2: Start file watchers for future changes
    observer = Observer()

    print(f"[STEP 2/2] Starting file watcher for ongoing changes.")
    print(f"  Debounce : {CONFIG['debounce_seconds']}s after last file change")
    print(f"  Auto-push: {CONFIG['auto_push']}")
    print(f"  Branch   : {CONFIG['branch']}")
    print("  Press Ctrl+C to stop.\n")

    for project_path, repo in valid_projects:
        report = scan_and_report(project_path)
        langs = ", ".join(f"{l}({c})" for l, c in report["languages"].items())
        log.info(f"[WATCH] {project_path}")
        log.info(f"        {len(report['files'])} files | {report['total_lines']} lines | {langs or 'no source files detected'}")
        handler = ProjectWatcher(project_path, repo)
        observer.schedule(handler, project_path, recursive=True)

    if skipped:
        print(f"[!] Skipped {len(skipped)} project(s) (no git repo):")
        for s in skipped:
            print(f"  - {s}")
        print()

    print(f"[BOT RUNNING] Watching {len(valid_projects)} project(s) for new changes.")
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log.info("Stopping bot...")
        observer.stop()

    observer.join()
    log.info("Bot stopped.")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            add_project(arg)
    run()