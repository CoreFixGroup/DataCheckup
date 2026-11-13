import re

from . import messages, settings
from .checks import is_empty
from .rules import FORMAT_CHECKS, parse_number


def column_words(name):
    spaced = re.sub(r"([a-z])([A-Z])", r"\1 \2", str(name))
    return {word.lower() for word in re.findall(r"[A-Za-z]+", spaced)}


def share(values, test):
    if len(values) > settings.SAMPLE_SIZE:
        values = values[:: len(values) // settings.SAMPLE_SIZE + 1]
    return sum(1 for value in values if test(value)) / len(values)


def detect_format(name, values):
    words = column_words(name)
    hinted = [fmt for fmt, hints in settings.NAME_HINTS.items() if words & hints]
    for fmt in hinted:
        if share(values, FORMAT_CHECKS[fmt]) >= settings.NAME_MATCH:
            return fmt, None
    if hinted:
        kind = messages.FORMAT_NAMES[hinted[0]]
        return None, messages.NAME_SUGGESTS.format(column=name, kind=kind)
    for fmt in ("email", "date"):
        if share(values, FORMAT_CHECKS[fmt]) >= settings.AGREE:
            return fmt, None
    return None, None


def detect_type(values):
    if share(values, lambda v: parse_number(v, "integer") is not None) >= settings.AGREE:
        return "integer"
    if share(values, lambda v: parse_number(v, "number") is not None) >= settings.AGREE:
        return "number"
    return None


def looks_like_id(column, values):
    if not column_words(column) & settings.ID_WORDS:
        return False
    return len(set(values)) / len(values) >= settings.DISTINCT


def column_values(column, records):
    return [
        str(record.get(column)).strip()
        for _, record in records
        if not is_empty(record.get(column))
    ]


def detect_column(column, values, total):
    rule = {}
    notes = []
    if len(values) / total >= settings.AGREE:
        rule["required"] = True
    fmt, note = detect_format(column, values)
    if note:
        notes.append(note)
    if fmt:
        rule["format"] = fmt
    else:
        kind = detect_type(values)
        if kind:
            rule["type"] = kind
    if looks_like_id(column, values):
        rule["unique"] = True
    return rule, notes


def detect_rules(columns, records):
    if not records:
        return {}, [messages.NO_RECORDS]
    if len(records) < settings.MIN_RECORDS:
        note = messages.TOO_FEW_RECORDS.format(found=len(records), needed=settings.MIN_RECORDS)
        return {}, [note]
    rules = {}
    notes = []
    for column in columns:
        values = column_values(column, records)
        if len(values) < settings.MIN_VALUES:
            continue
        rule, column_notes = detect_column(column, values, len(records))
        notes += column_notes
        if rule:
            rules[column] = rule
    return rules, notes
