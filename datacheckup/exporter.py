import csv
import json
from pathlib import Path

from . import messages, settings
from .errors import DataCheckupError
from .rules import parse_number


def safe_cell(value):
    text = "" if value is None else str(value)
    if text.startswith(settings.FORMULA_STARTS):
        return "'" + text
    if text.startswith(settings.SIGN_STARTS) and parse_number(text) is None:
        return "'" + text
    return text


def check_export_path(path, source):
    if path.resolve() == Path(source).resolve():
        raise DataCheckupError(messages.EXPORT_SAME_FILE)
    if path.suffix.lower() not in settings.EXPORT_SUFFIXES:
        raise DataCheckupError(messages.EXPORT_BAD_TYPE)
    if not path.parent.exists():
        raise DataCheckupError(messages.EXPORT_FOLDER_MISSING.format(folder=path.parent))


def group_by_row(errors):
    problems = {}
    for error in errors:
        if error["row"] is not None:
            problems.setdefault(error["row"], []).append(error)
    return problems


def export_problem_records(source, columns, records, errors, path):
    path = Path(path)
    check_export_path(path, source)
    problems = group_by_row(errors)
    rows = [(row, record) for row, record in records if row in problems]
    try:
        if path.suffix.lower() == ".csv":
            write_csv(path, columns, rows, problems)
        else:
            write_json(path, columns, rows, problems)
    except OSError as error:
        raise DataCheckupError(messages.EXPORT_WRITE_FAILED.format(path=path, reason=error.strerror)) from None
    return len(rows)


def write_csv(path, columns, rows, problems):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([safe_cell(c) for c in ["File Row"] + columns + ["Problems"]])
        for row, record in rows:
            summary = "; ".join(f"{e['column']}: {e['reason']}" for e in problems[row])
            cells = [row] + [record.get(c, "") for c in columns] + [summary]
            writer.writerow([safe_cell(cell) for cell in cells])


def write_json(path, columns, rows, problems):
    output = []
    for row, record in rows:
        output.append({
            "row": row,
            "record": {c: record.get(c) for c in columns},
            "problems": [
                {"column": e["column"], "reason": e["reason"], "suggestion": e["suggestion"]}
                for e in problems[row]
            ],
        })
    with open(path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
