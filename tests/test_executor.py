from pathlib import Path

import executor.executor as executor
from brain.planner import Decision


def test_execute_open_folder(monkeypatch):
    opened = []
    existing_path = Path.cwd()

    monkeypatch.setattr(executor, "_resolve_folder_path", lambda name: existing_path)
    monkeypatch.setattr(executor, "open_path", lambda path: opened.append(path))

    response = executor.execute_plan(
        Decision(route="action", intent="open_folder", action="open_folder", target="downloads")
    )

    assert response == "Opening downloads"
    assert opened == [str(existing_path)]


def test_execute_open_folder_missing(monkeypatch):
    monkeypatch.setattr(executor, "_resolve_folder_path", lambda name: None)

    response = executor.execute_plan(
        Decision(route="action", intent="open_folder", action="open_folder", target="project_folder")
    )

    assert response == "I couldn't find project folder."


def test_execute_open_file(monkeypatch):
    def fake_open_matching_file(query, workspace=None):
        return {
            "status": "opened",
            "query": query,
            "match": {"name": "resume.pdf", "path": Path("resume.pdf"), "score": 100},
            "matches": [],
        }

    monkeypatch.setattr(executor, "open_matching_file", fake_open_matching_file)

    response = executor.execute_plan(
        Decision(route="action", intent="open_file", action="open_file", query="resume")
    )

    assert response == "Opening resume.pdf"


def test_execute_open_file_multiple(monkeypatch):
    def fake_open_matching_file(query, workspace=None):
        return {
            "status": "multiple",
            "query": query,
            "matches": [
                {"name": "resume.pdf", "path": Path("resume.pdf"), "score": 100},
                {"name": "resume.docx", "path": Path("resume.docx"), "score": 100},
            ],
        }

    monkeypatch.setattr(executor, "open_matching_file", fake_open_matching_file)

    response = executor.execute_plan(
        Decision(route="action", intent="open_file", action="open_file", query="resume")
    )

    assert response == "I found multiple matching files: resume.pdf, resume.docx. Please be more specific."


def test_execute_open_file_missing(monkeypatch):
    monkeypatch.setattr(
        executor,
        "open_matching_file",
        lambda query, workspace=None: {"status": "not_found", "query": query, "matches": []},
    )

    response = executor.execute_plan(
        Decision(route="action", intent="open_file", action="open_file", query="invoice")
    )

    assert response == "I couldn't find a file matching invoice."
