import difflib
import os
import re
from pathlib import Path


def open_notepad():
    os.system("notepad")

def close_notepad():
    os.system("taskkill /f /im notepad.exe")

def open_calculator():
    os.system("calc")

def close_calculator():
    os.system("taskkill /f /im CalculatorApp.exe")

def open_chrome():
    os.system("start chrome")

def close_chrome():
    result = os.system("taskkill /f /im chrome.exe /t")
    if result != 0:
        os.system("taskkill /f /im msedge.exe /t")


def open_path(path):
    os.startfile(path)


COMMON_FILE_EXTENSIONS = {
    ".csv",
    ".doc",
    ".docx",
    ".gif",
    ".jpeg",
    ".jpg",
    ".md",
    ".pdf",
    ".png",
    ".ppt",
    ".pptx",
    ".py",
    ".rtf",
    ".txt",
    ".webp",
    ".xls",
    ".xlsx",
}

SKIPPED_SEARCH_DIRS = {
    ".git",
    ".pytest_cache",
    ".venv",
    "__pycache__",
    "node_modules",
}


def open_matching_file(query: str, workspace: str | Path | None = None):
    matches = find_matching_files(query, workspace=workspace)
    if not matches:
        return {
            "status": "not_found",
            "query": query,
            "matches": [],
        }

    if _should_ask_which_file(matches):
        return {
            "status": "multiple",
            "query": query,
            "matches": matches[:5],
        }

    open_path(str(matches[0]["path"]))
    return {
        "status": "opened",
        "query": query,
        "match": matches[0],
        "matches": matches[:5],
    }


def find_matching_files(query: str, workspace: str | Path | None = None, limit: int = 8):
    normalized_query = _normalize_file_name(query)
    if not normalized_query:
        return []

    matches = []
    seen_paths = set()
    for root in _common_search_roots(workspace):
        for path in _iter_common_files(root):
            try:
                resolved_path = path.resolve()
            except OSError:
                continue
            if resolved_path in seen_paths:
                continue
            seen_paths.add(resolved_path)
            score = _file_match_score(normalized_query, path)
            if score <= 0:
                continue
            matches.append({
                "path": path,
                "name": path.name,
                "score": score,
            })

    matches.sort(key=lambda item: (-item["score"], len(str(item["path"])), item["name"].lower()))
    return matches[:limit]


def _common_search_roots(workspace: str | Path | None = None):
    roots = []
    home = Path.home()
    user_profile = Path(os.environ.get("USERPROFILE", home))

    for base in {home, user_profile}:
        roots.extend([base / "Desktop", base / "Documents", base / "Downloads"])

    if workspace:
        roots.append(Path(workspace))

    for one_drive in _one_drive_roots(home, user_profile):
        roots.append(one_drive)
        roots.extend([one_drive / "Desktop", one_drive / "Documents", one_drive / "Downloads"])

    unique_roots = []
    seen = set()
    for root in roots:
        try:
            resolved = root.expanduser().resolve()
        except OSError:
            continue
        if resolved in seen or not resolved.exists() or not resolved.is_dir():
            continue
        seen.add(resolved)
        unique_roots.append(resolved)

    return unique_roots


def _one_drive_roots(home: Path, user_profile: Path):
    roots = []
    for key in ("OneDrive", "OneDriveConsumer", "OneDriveCommercial"):
        value = os.environ.get(key)
        if value:
            roots.append(Path(value))

    for base in {home, user_profile}:
        try:
            roots.extend(path for path in base.glob("OneDrive*") if path.is_dir())
        except OSError:
            continue

    return roots


def _iter_common_files(root: Path):
    for current, dirs, files in os.walk(root):
        dirs[:] = [
            directory for directory in dirs
            if directory not in SKIPPED_SEARCH_DIRS and not directory.startswith(".")
        ]

        for filename in files:
            path = Path(current) / filename
            if path.suffix.lower() in COMMON_FILE_EXTENSIONS:
                yield path


def _file_match_score(normalized_query: str, path: Path) -> int:
    stem = _normalize_file_name(path.stem)
    full_name = _normalize_file_name(path.name)
    if not stem:
        return 0

    if stem == normalized_query or full_name == normalized_query:
        return 100

    query_tokens = normalized_query.split()
    if all(token in stem.split() for token in query_tokens):
        return 85 + min(10, len(query_tokens))

    if normalized_query in stem:
        return 80

    if all(token in stem for token in query_tokens):
        return 70

    ratio = difflib.SequenceMatcher(None, normalized_query, stem).ratio()
    return int(ratio * 60) if ratio >= 0.62 else 0


def _normalize_file_name(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"\b(file|document|doc|pdf|ppt|pptx|presentation|notes?)\b", " ", value)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def _should_ask_which_file(matches) -> bool:
    if len(matches) < 2:
        return False

    best = matches[0]["score"]
    second = matches[1]["score"]
    if best >= 100 and second < 100:
        return False

    return best - second <= 5
