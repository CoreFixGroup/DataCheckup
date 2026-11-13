import math
import numbers
import re
from datetime import datetime

from . import messages, settings
from .errors import DataCheckupError


def is_email(text):
    return settings.EMAIL_PATTERN.match(text) is not None


def is_phone(text):
    digits = settings.PHONE_SEPARATORS.sub("", text)
    return settings.PHONE_PATTERN.match(digits) is not None


def time_is_valid(hour, minute, second, meridian):
    hour, minute = int(hour), int(minute)
    if meridian and not 1 <= hour <= 12:
        return False
    if not meridian and hour > 23:
        return False
    if minute > 59:
        return False
    return second is None or int(second) <= 59


def date_matches(text, style):
    try:
        datetime.strptime(text, style)
        return True
    except ValueError:
        return False


def is_date(text):
    match = settings.DATE_TIME.match(text)
    if match is None:
        return False
    date_part, hour, minute, second, meridian = match.groups()
    if hour is not None and not time_is_valid(hour, minute, second, meridian):
        return False
    return any(date_matches(date_part, style) for style in settings.DATE_STYLES)


FORMAT_CHECKS = {
    "email": is_email,
    "phone": is_phone,
    "date": is_date,
}


def clean_number_text(value):
    text = settings.CURRENCY_MARKS.sub("", str(value))
    text = settings.WHITESPACE.sub("", text)
    if text.endswith("%"):
        text = text[:-1]
    return text


def parse_number(value, kind="number"):
    text = clean_number_text(value)
    if not text or "_" in text:
        return None
    if "," in text:
        if not settings.GROUPED_NUMBER.match(text):
            return None
        text = text.replace(",", "")
    try:
        number = float(text)
    except ValueError:
        return None
    if not math.isfinite(number):
        return None
    if kind == "integer":
        return int(number) if number.is_integer() else None
    return number


def check_limit_type(column, rule, limit):
    if rule.get("type") not in settings.NUMBER_TYPES:
        raise DataCheckupError(messages.LIMIT_NEEDS_NUMBER_TYPE.format(limit=limit, column=column))


def check_limit_value(column, rule, limit):
    value = rule[limit]
    if isinstance(value, bool) or not isinstance(value, numbers.Real):
        raise DataCheckupError(messages.LIMIT_NOT_A_NUMBER.format(limit=limit, column=column))


def check_pattern(column, rule):
    pattern = rule["pattern"]
    if not isinstance(pattern, str):
        raise DataCheckupError(messages.PATTERN_NOT_TEXT.format(column=column))
    try:
        re.compile(pattern)
    except re.error as error:
        raise DataCheckupError(messages.PATTERN_INVALID.format(column=column, reason=error)) from None


def allowed_values(allowed):
    if hasattr(allowed, "tolist"):
        allowed = allowed.tolist()
    if isinstance(allowed, (list, tuple, set, frozenset)):
        return list(allowed)
    return []


def check_allowed(column, rule):
    if not allowed_values(rule["allowed"]):
        raise DataCheckupError(messages.ALLOWED_NOT_LIST.format(column=column))


def check_column_rule(column, rule, partial=False):
    if not isinstance(rule, dict):
        raise DataCheckupError(messages.COLUMN_RULES_NOT_DICT.format(column=column))
    unknown = set(rule) - settings.RULE_KEYS
    if unknown:
        raise DataCheckupError(messages.UNKNOWN_RULE.format(names=sorted(unknown), column=column))
    if "type" in rule and rule["type"] not in settings.RULE_TYPES:
        raise DataCheckupError(messages.UNKNOWN_TYPE.format(value=rule["type"], column=column))
    if rule.get("format") is not None and rule["format"] not in FORMAT_CHECKS:
        raise DataCheckupError(messages.UNKNOWN_FORMAT.format(value=rule["format"], column=column))
    for limit in ("min", "max"):
        if limit in rule:
            if not partial:
                check_limit_type(column, rule, limit)
            check_limit_value(column, rule, limit)
    if "pattern" in rule:
        check_pattern(column, rule)
    if "allowed" in rule:
        check_allowed(column, rule)
    if "message" in rule and not isinstance(rule["message"], str):
        raise DataCheckupError(messages.MESSAGE_NOT_TEXT.format(column=column))


def load_rules(rules, partial=False):
    if not isinstance(rules, dict):
        raise DataCheckupError(messages.RULES_NOT_DICT)
    cleaned = {}
    for column, rule in rules.items():
        check_column_rule(column, rule, partial)
        cleaned[column] = dict(rule)
        if "allowed" in rule:
            cleaned[column]["allowed"] = allowed_values(rule["allowed"])
    return cleaned


def combine_rules(detected, custom, columns):
    rules = {column: dict(rule) for column, rule in detected.items()}
    notes = []
    for column, rule in custom.items():
        merged = rules.setdefault(column, {})
        merged.update(rule)
        if ("min" in merged or "max" in merged) and merged.get("type") is None:
            merged["type"] = "number"
        for limit in ("min", "max"):
            if limit in merged:
                check_limit_type(column, merged, limit)
        if column not in columns and not rule.get("required"):
            notes.append(messages.UNKNOWN_COLUMN_RULE.format(column=column, columns=", ".join(columns)))
    if custom:
        notes.append(messages.CUSTOM_RULES_APPLIED.format(columns=", ".join(custom)))
    return rules, notes
