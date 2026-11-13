import csv
import json
import os
from pathlib import Path

from . import messages, settings
from .errors import DataCheckError


def read_file(path):
    path = check_path(path)
    try:
        if path.suffix.lower() == ".json":
            return read_json(path)
        return read_csv(path)
    except PermissionError:
        raise DataCheckError(messages.NO_PERMISSION.format(path=path)) from None
    except csv.Error as error:
        raise DataCheckError(messages.CSV_UNREADABLE.format(reason=error)) from None


def check_path(path):
    if not isinstance(path, (str, os.PathLike)):
        raise DataCheckError(messages.PATH_NOT_TEXT)
    path = Path(path)
    if not path.exists():
        raise DataCheckError(messages.FILE_NOT_FOUND.format(path=path))
    if path.is_dir():
        raise DataCheckError(messages.IS_A_FOLDER.format(path=path))
    check_file_type(path.suffix.lower())
    return path


def check_file_type(suffix):
    if suffix in settings.EXCEL_SUFFIXES:
        raise DataCheckError(messages.EXCEL_NOT_SUPPORTED)
    if suffix in settings.SUPPORTED_SUFFIXES:
        return
    if suffix:
        raise DataCheckError(messages.UNSUPPORTED_TYPE.format(suffix=suffix))
    raise DataCheckError(messages.NO_EXTENSION)


def read_head(path):
    with open(path, "rb") as f:
        return f.read(settings.HEAD_BYTES)


def reject_other_file_types(head):
    if head.startswith(settings.EXCEL_SIGNATURE):
        raise DataCheckError(messages.EXCEL_WITH_OTHER_NAME)
    if head.startswith(settings.PDF_SIGNATURE):
        raise DataCheckError(messages.LOOKS_LIKE_PDF)


def reject_binary(head):
    odd = sum(1 for byte in head if byte < 32 and byte not in settings.TEXT_CONTROL_BYTES)
    if head and (b"\x00" in head or odd / len(head) > settings.BINARY_LIMIT):
        raise DataCheckError(messages.NOT_A_TEXT_FILE)


def can_read(path, encoding):
    try:
        with open(path, encoding=encoding) as f:
            while f.read(settings.READ_CHUNK):
                pass
        return True
    except UnicodeDecodeError:
        return False


def find_encoding(path):
    head = read_head(path)
    reject_other_file_types(head)
    if head.startswith(settings.UTF16_MARKS):
        return "utf-16"
    reject_binary(head)
    for encoding in settings.ENCODINGS:
        if can_read(path, encoding):
            return encoding
    raise DataCheckError(messages.ENCODING_UNKNOWN)


def first_line(f):
    for _ in range(settings.HEADER_SEARCH_LINES):
        line = f.readline()
        if not line:
            return ""
        if line.strip():
            return line
    return ""


def find_delimiter(f):
    line = first_line(f)
    f.seek(0)
    best, best_count = ",", 1
    for candidate in settings.DELIMITERS:
        count = len(next(csv.reader([line], delimiter=candidate), []))
        if count > best_count:
            best, best_count = candidate, count
    return best


def make_problem(row, column, reason, suggestion):
    return {"row": row, "column": column, "reason": reason, "suggestion": suggestion}


def unique_name(name, seen):
    count = 2
    while f"{name} ({count})" in seen:
        count += 1
    return f"{name} ({count})"


def clean_header(header, row):
    columns = []
    problems = []
    seen = set()
    for index, raw in enumerate(header, start=1):
        name = raw.strip()
        if not name:
            name = f"Column {index}"
            problems.append(make_problem(
                row, name, messages.COLUMN_WITHOUT_NAME, messages.COLUMN_WITHOUT_NAME_FIX,
            ))
        elif name in seen:
            problems.append(make_problem(
                row, name, messages.DUPLICATE_COLUMN.format(name=name), messages.DUPLICATE_COLUMN_FIX,
            ))
            name = unique_name(name, seen)
        seen.add(name)
        columns.append(name)
    return columns, problems


def find_header(rows):
    for number, values in rows:
        if any(value.strip() for value in values):
            return number, values
    raise DataCheckError(messages.FILE_EMPTY)


def read_row(number, values, columns):
    if not any(value.strip() for value in values):
        problem = make_problem(number, settings.ENTIRE_ROW, messages.EMPTY_ROW, messages.EMPTY_ROW_FIX)
        return None, problem
    problem = None
    if len(values) != len(columns):
        problem = make_problem(
            number, settings.ENTIRE_ROW,
            messages.WRONG_VALUE_COUNT.format(found=len(values), expected=len(columns)),
            messages.WRONG_VALUE_COUNT_FIX,
        )
    padded = values + [""] * (len(columns) - len(values))
    return dict(zip(columns, padded)), problem


def read_csv(path):
    encoding = find_encoding(path)
    with open(path, newline="", encoding=encoding) as f:
        delimiter = find_delimiter(f)
        rows = enumerate(csv.reader(f, delimiter=delimiter), start=1)
        header_row, header = find_header(rows)
        columns, problems = clean_header(header, header_row)
        records = []
        for number, values in rows:
            record, problem = read_row(number, values, columns)
            if problem:
                problems.append(problem)
            if record is not None:
                records.append((number, record))
    return columns, records, problems


def read_text(path):
    encoding = find_encoding(path)
    with open(path, encoding=encoding) as f:
        return f.read()


def parse_json(text):
    try:
        return json.loads(text)
    except json.JSONDecodeError as error:
        raise DataCheckError(messages.JSON_INVALID.format(
            reason=error.msg, line=error.lineno, column=error.colno,
        )) from None


def check_json_shape(data):
    if isinstance(data, dict):
        raise DataCheckError(messages.JSON_IS_OBJECT)
    if not isinstance(data, list):
        raise DataCheckError(messages.JSON_NOT_LIST)
    for number, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            raise DataCheckError(messages.JSON_BAD_RECORD.format(number=number))


def find_json_columns(data):
    columns = []
    for item in data:
        for key in item:
            if key not in columns:
                columns.append(key)
    return columns


def read_json(path):
    text = read_text(path)
    if not text.strip():
        raise DataCheckError(messages.FILE_EMPTY)
    data = parse_json(text)
    check_json_shape(data)
    return find_json_columns(data), list(enumerate(data, start=1)), []
