import re

from . import messages, settings
from .rules import FORMAT_CHECKS, parse_number


def is_empty(value):
    return value is None or str(value).strip() == ""


def mask_value(value):
    text = str(value).strip()
    if len(text) <= 4:
        return "*" * len(text)
    return text[:2] + "*" * (len(text) - 4) + text[-2:]


def display_value(value, rule):
    if value is None:
        return ""
    text = str(value).strip()
    if rule.get("sensitive") or rule.get("format") in settings.SENSITIVE_FORMATS:
        return mask_value(text)
    return text


def make_error(row, column, value, error_type, reason, suggestion=""):
    return {
        "row": row,
        "column": column,
        "value": value,
        "error_type": error_type,
        "reason": reason,
        "suggestion": suggestion,
    }


def check_structure(problems):
    return [
        make_error(p["row"], p["column"], "", "structure", p["reason"], p["suggestion"])
        for p in problems
    ]


def check_schema(columns, rules):
    errors = []
    for column, rule in rules.items():
        if column not in columns and rule.get("required"):
            errors.append(make_error(
                None, column, "", "schema",
                messages.MISSING_COLUMN,
                messages.MISSING_COLUMN_FIX.format(column=column),
            ))
    return errors


def check_missing(records, rules):
    errors = []
    for row, record in records:
        for column, rule in rules.items():
            if rule.get("required") and is_empty(record.get(column)):
                errors.append(make_error(
                    row, column, "", "missing",
                    messages.MISSING_VALUE,
                    messages.MISSING_VALUE_FIX.format(column=column),
                ))
    return errors


def check_number(row, column, rule, value):
    kind = rule["type"]
    shown = display_value(value, rule)
    number = parse_number(value, kind)
    if number is None:
        expected = messages.EXPECTED_WHOLE_NUMBER if kind == "integer" else messages.EXPECTED_NUMBER
        return [make_error(
            row, column, shown, "invalid_type",
            messages.WRONG_TYPE.format(expected=expected),
            messages.WRONG_TYPE_FIX,
        )]
    errors = []
    if "min" in rule and number < rule["min"]:
        errors.append(make_error(
            row, column, shown, "out_of_range",
            messages.BELOW_MINIMUM.format(limit=rule["min"]),
            messages.BELOW_MINIMUM_FIX.format(limit=rule["min"]),
        ))
    if "max" in rule and number > rule["max"]:
        errors.append(make_error(
            row, column, shown, "out_of_range",
            messages.ABOVE_MAXIMUM.format(limit=rule["max"]),
            messages.ABOVE_MAXIMUM_FIX.format(limit=rule["max"]),
        ))
    return errors


def check_types_and_ranges(records, rules):
    errors = []
    for row, record in records:
        for column, rule in rules.items():
            if rule.get("type") not in settings.NUMBER_TYPES:
                continue
            value = record.get(column)
            if not is_empty(value):
                errors += check_number(row, column, rule, value)
    return errors


def check_formats(records, rules):
    errors = []
    for row, record in records:
        for column, rule in rules.items():
            name = rule.get("format")
            value = record.get(column)
            if not name or is_empty(value):
                continue
            if not FORMAT_CHECKS[name](str(value).strip()):
                errors.append(make_error(
                    row, column, display_value(value, rule), "invalid_format",
                    messages.WRONG_FORMAT.format(format=name),
                    messages.FORMAT_FIX[name],
                ))
    return errors


def check_patterns(records, rules):
    errors = []
    for column, rule in rules.items():
        if "pattern" not in rule:
            continue
        pattern = re.compile(rule["pattern"])
        reason = rule.get("message") or messages.PATTERN_MISMATCH.format(pattern=rule["pattern"])
        for row, record in records:
            value = record.get(column)
            if is_empty(value) or pattern.fullmatch(str(value).strip()):
                continue
            errors.append(make_error(
                row, column, display_value(value, rule), "invalid_format",
                reason, messages.PATTERN_FIX,
            ))
    return errors


def check_allowed(records, rules):
    errors = []
    for column, rule in rules.items():
        if "allowed" not in rule:
            continue
        allowed = [str(item).strip() for item in rule["allowed"]]
        reason = rule.get("message") or messages.NOT_ALLOWED
        fix = messages.NOT_ALLOWED_FIX.format(values=", ".join(allowed))
        for row, record in records:
            value = record.get(column)
            if is_empty(value) or str(value).strip() in allowed:
                continue
            errors.append(make_error(
                row, column, display_value(value, rule), "not_allowed", reason, fix,
            ))
    return errors


def check_duplicates(records, rules):
    errors = []
    for column, rule in rules.items():
        if not rule.get("unique"):
            continue
        first_seen = {}
        for row, record in records:
            value = record.get(column)
            if is_empty(value):
                continue
            key = str(value).strip()
            if key in first_seen:
                errors.append(make_error(
                    row, column, display_value(value, rule), "duplicate",
                    messages.DUPLICATE_VALUE.format(row=first_seen[key]),
                    messages.DUPLICATE_VALUE_FIX,
                ))
            else:
                first_seen[key] = row
    return errors


def row_key(columns, record):
    return tuple("" if is_empty(record.get(c)) else str(record.get(c)).strip() for c in columns)


def check_duplicate_rows(columns, records):
    errors = []
    first_seen = {}
    for row, record in records:
        key = row_key(columns, record)
        if not any(key):
            continue
        if key in first_seen:
            errors.append(make_error(
                row, settings.ENTIRE_ROW, "", "duplicate_row",
                messages.DUPLICATE_ROW.format(row=first_seen[key]),
                messages.DUPLICATE_ROW_FIX,
            ))
        else:
            first_seen[key] = row
    return errors


def run_checks(columns, records, rules, problems=None):
    errors = check_structure(problems or [])
    errors += check_schema(columns, rules)
    present = {column: rule for column, rule in rules.items() if column in columns}
    errors += check_missing(records, present)
    errors += check_types_and_ranges(records, present)
    errors += check_formats(records, present)
    errors += check_patterns(records, present)
    errors += check_allowed(records, present)
    errors += check_duplicates(records, present)
    errors += check_duplicate_rows(columns, records)
    order = {column: index for index, column in enumerate(columns)}
    errors.sort(key=lambda e: (e["row"] if e["row"] is not None else 0, order.get(e["column"], 0)))
    return errors
