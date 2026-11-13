from .checks import run_checks
from .detector import detect_rules
from .errors import DataCheckError
from .reader import read_file
from .report import Report
from .rules import combine_rules, load_rules


def check(path, rules=None):
    custom = load_rules(rules, partial=True) if rules is not None else {}
    columns, records, problems = read_file(path)
    detected, notes = detect_rules(columns, records)
    final, custom_notes = combine_rules(detected, custom, columns)
    errors = run_checks(columns, records, final, problems)
    return Report(path, columns, records, errors, final, True, notes + custom_notes)


def check_with_rules(path, rules):
    rules = load_rules(rules)
    columns, records, problems = read_file(path)
    errors = run_checks(columns, records, rules, problems)
    return Report(path, columns, records, errors, rules, False, [])


__all__ = ["check", "Report", "DataCheckError"]
