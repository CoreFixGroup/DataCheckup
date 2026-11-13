from . import messages, settings
from .exporter import export_problem_records


def tidy(text, limit):
    text = " ".join(str(text).split())
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def describe_rule(rule):
    parts = []
    if rule.get("required"):
        parts.append("required")
    if rule.get("unique"):
        parts.append("unique")
    kind = rule.get("type")
    if kind == "integer":
        parts.append("whole number")
    elif kind == "number":
        parts.append("number")
    if rule.get("format"):
        parts.append(f"{rule['format']} format")
    if "min" in rule:
        parts.append(f"min {rule['min']}")
    if "max" in rule:
        parts.append(f"max {rule['max']}")
    if rule.get("pattern"):
        parts.append("custom pattern")
    if rule.get("allowed"):
        parts.append("allowed values only")
    return ", ".join(parts)


class Report:
    def __init__(self, source, columns, records, errors, rules=None, detected=False, notes=None):
        self.source = str(source)
        self.columns = columns
        self.records = records
        self.errors = errors
        self.rules = rules or {}
        self.detected = detected
        self.notes = notes or []
        self.summary = self.build_summary()

    def build_summary(self):
        total = len(self.records)
        record_rows = {row for row, _ in self.records}
        bad_rows = {e["row"] for e in self.errors if e["row"] in record_rows}
        by_type = {}
        for error in self.errors:
            by_type[error["error_type"]] = by_type.get(error["error_type"], 0) + 1
        return {
            "total_records": total,
            "records_with_issues": len(bad_rows),
            "records_without_issues": total - len(bad_rows),
            "total_errors": len(self.errors),
            "errors_by_type": by_type,
        }

    def has_errors(self):
        return len(self.errors) > 0

    def summary_lines(self):
        s = self.summary
        lines = [
            "Dataset Summary",
            f"  Total records: {s['total_records']}",
            f"  Records with issues: {s['records_with_issues']}",
            f"  Records without issues: {s['records_without_issues']}",
            f"  Total errors: {s['total_errors']}",
        ]
        for key, label in messages.ERROR_LABELS.items():
            if s["errors_by_type"].get(key):
                lines.append(f"  {label}: {s['errors_by_type'][key]}")
        return lines

    def rules_lines(self):
        title = "Rules used (detected automatically)" if self.detected else "Rules used"
        if not self.rules:
            return [title, "  (none)"]
        names = {column: tidy(column, settings.SHORT_NAME) for column in self.rules}
        width = max(len(name) for name in names.values())
        lines = [title]
        for column, rule in self.rules.items():
            lines.append(f"  {names[column].ljust(width)} : {describe_rule(rule)}")
        return lines

    def notes_lines(self):
        return ["Notes"] + [f"  - {note}" for note in self.notes]

    def table_lines(self):
        header = ["File Row", "Column", "Problem", "Value", "Suggested fix"]
        table = [header]
        for e in self.errors:
            row = "-" if e["row"] is None else str(e["row"])
            table.append([
                row,
                tidy(e["column"], settings.SHORT_NAME),
                tidy(e["reason"], settings.SHORT_TEXT),
                tidy(e["value"], settings.SHORT_NAME),
                tidy(e["suggestion"], settings.SHORT_TEXT),
            ])
        widths = [max(len(r[i]) for r in table) for i in range(len(header))]
        lines = []
        for index, r in enumerate(table):
            lines.append("  " + " | ".join(r[i].ljust(widths[i]) for i in range(len(header))).rstrip())
            if index == 0:
                lines.append("  " + "-+-".join("-" * w for w in widths))
        return lines

    def to_text(self):
        lines = ["DataCheck Report", f"File: {self.source}", ""]
        lines += self.summary_lines()
        lines += [""] + self.rules_lines()
        if self.notes:
            lines += [""] + self.notes_lines()
        lines.append("")
        if self.errors:
            lines += self.table_lines()
        else:
            lines.append("No problems found.")
        return "\n".join(lines)

    def show(self):
        print(self.to_text())

    def export(self, path):
        return export_problem_records(self.source, self.columns, self.records, self.errors, path)
