import csv
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from datacheck import DataCheckError, check, check_with_rules
from datacheck.detector import column_words, detect_rules
from datacheck.reader import read_file
from datacheck.rules import is_date, is_email, is_phone, load_rules, parse_number

DATA = Path(__file__).parent / "data"
SAMPLE = DATA / "employees.csv"
STUDENTS = DATA / "students.csv"
SALES = DATA / "sales.json"

RULES = {
    "Employee ID": {"required": True, "unique": True},
    "Name": {"required": True},
    "Email": {"required": True, "format": "email"},
    "Phone": {"format": "phone"},
    "Salary": {"required": True, "type": "number", "min": 0},
}

STUDENT_ERRORS = {
    (13, "Mobile", "invalid_format"),
    (14, "Student Name", "missing"),
    (15, "Email", "invalid_format"),
    (16, "Date of Birth", "invalid_format"),
    (17, "Marks", "invalid_type"),
    (18, "Email", "missing"),
    (21, "Roll No", "duplicate"),
    (24, "Roll No", "duplicate"),
    (24, "(entire row)", "duplicate_row"),
}

SALES_ERRORS = {
    (9, "Price", "missing"),
    (11, "Customer Phone", "invalid_format"),
    (12, "Price", "invalid_type"),
    (13, "Quantity", "invalid_type"),
    (14, "Customer Phone", "missing"),
    (15, "Order ID", "duplicate"),
    (16, "Order Date", "invalid_format"),
}


def found(report):
    return {(e["row"], e["column"], e["error_type"]) for e in report.errors}


def write(folder, name, text):
    path = Path(folder) / name
    path.write_text(text, encoding="utf-8")
    return path


def write_bytes(folder, name, data):
    path = Path(folder) / name
    path.write_bytes(data)
    return path


class ReaderTests(unittest.TestCase):
    def test_csv_row_numbers_start_after_header(self):
        columns, records, problems = read_file(SAMPLE)
        self.assertEqual(columns, ["Employee ID", "Name", "Email", "Phone", "Salary"])
        self.assertEqual([row for row, _ in records], [2, 3, 4, 5])
        self.assertEqual(problems, [])

    def test_json_row_numbers_start_at_one(self):
        with tempfile.TemporaryDirectory() as folder:
            path = write(folder, "data.json", json.dumps([{"a": 1}, {"a": 2, "b": 3}]))
            columns, records, problems = read_file(path)
        self.assertEqual(columns, ["a", "b"])
        self.assertEqual([row for row, _ in records], [1, 2])
        self.assertEqual(problems, [])

    def test_other_separators_are_detected(self):
        with tempfile.TemporaryDirectory() as folder:
            for separator in [";", "\t", "|"]:
                text = f"Name{separator}Email\nRavi{separator}r@x.com\n"
                columns, records, _ = read_file(write(folder, "data.csv", text))
                self.assertEqual(columns, ["Name", "Email"])
                self.assertEqual(records[0][1]["Email"], "r@x.com")

    def test_quoted_commas_stay_inside_the_cell(self):
        with tempfile.TemporaryDirectory() as folder:
            path = write(folder, "data.csv", 'Name,City\n"Rao, Ravi",Guntur\n')
            columns, records, _ = read_file(path)
        self.assertEqual(records[0][1]["Name"], "Rao, Ravi")

    def test_excel_style_utf8_with_bom_and_windows_line_endings(self):
        with tempfile.TemporaryDirectory() as folder:
            path = write_bytes(folder, "data.csv", b"\xef\xbb\xbf" + "Roll No,Name\r\n1,A\r\n".encode())
            columns, records, _ = read_file(path)
        self.assertEqual(columns, ["Roll No", "Name"])
        self.assertEqual(len(records), 1)

    def test_windows_encoding_is_read(self):
        with tempfile.TemporaryDirectory() as folder:
            path = write_bytes(folder, "data.csv", "Name,City\nRavi,Zürich\n".encode("cp1252"))
            columns, records, _ = read_file(path)
        self.assertEqual(records[0][1]["City"], "Zürich")

    def test_excel_unicode_text_is_read(self):
        with tempfile.TemporaryDirectory() as folder:
            path = write_bytes(folder, "data.csv", "Name\tCity\nRavi\tZürich\n".encode("utf-16"))
            columns, records, _ = read_file(path)
        self.assertEqual(columns, ["Name", "City"])
        self.assertEqual(records[0][1]["City"], "Zürich")

    def test_json_with_bom_is_read(self):
        with tempfile.TemporaryDirectory() as folder:
            path = write_bytes(folder, "data.json", b"\xef\xbb\xbf" + b'[{"a": 1}]')
            columns, records, _ = read_file(path)
        self.assertEqual(columns, ["a"])

    def test_row_numbers_match_excel_with_multiline_cells_and_blank_lines(self):
        with tempfile.TemporaryDirectory() as folder:
            path = write(folder, "data.csv", 'A,B\n1,"line one\nline two"\n\n3,4\n')
            columns, records, problems = read_file(path)
        self.assertEqual([row for row, _ in records], [2, 4])
        self.assertEqual(len(problems), 1)
        self.assertEqual(problems[0]["row"], 3)
        self.assertIn("empty", problems[0]["reason"])

    def test_leading_blank_lines_before_the_header(self):
        with tempfile.TemporaryDirectory() as folder:
            path = write(folder, "data.csv", "\n\nA,B\n1,2\n")
            columns, records, problems = read_file(path)
        self.assertEqual(columns, ["A", "B"])
        self.assertEqual([row for row, _ in records], [4])
        self.assertEqual(problems, [])

    def test_rows_with_too_many_or_too_few_values(self):
        with tempfile.TemporaryDirectory() as folder:
            path = write(folder, "data.csv", "A,B,C\n1,2,3\n4,5\n6,7,8,9\n")
            columns, records, problems = read_file(path)
        self.assertEqual([p["row"] for p in problems], [3, 4])
        self.assertIn("2 values but the header has 3", problems[0]["reason"])
        self.assertIn("4 values but the header has 3", problems[1]["reason"])
        self.assertEqual(records[1][1], {"A": "4", "B": "5", "C": ""})

    def test_duplicate_and_blank_column_names(self):
        with tempfile.TemporaryDirectory() as folder:
            path = write(folder, "data.csv", "A,A,,B\n1,2,3,4\n")
            columns, records, problems = read_file(path)
        self.assertEqual(columns, ["A", "A (2)", "Column 3", "B"])
        self.assertEqual(records[0][1], {"A": "1", "A (2)": "2", "Column 3": "3", "B": "4"})
        reasons = [p["reason"] for p in problems]
        self.assertTrue(any("Duplicate column name 'A'" in r for r in reasons))
        self.assertTrue(any("no name" in r for r in reasons))
        self.assertTrue(all(p["row"] == 1 for p in problems))

    def test_completely_empty_rows_are_reported_not_counted(self):
        with tempfile.TemporaryDirectory() as folder:
            path = write(folder, "data.csv", "A,B\n1,2\n,\n3,4\n")
            columns, records, problems = read_file(path)
        self.assertEqual([row for row, _ in records], [2, 4])
        self.assertEqual([p["row"] for p in problems], [3])


class ReaderErrorTests(unittest.TestCase):
    def assert_error(self, source, pattern):
        with self.assertRaisesRegex(DataCheckError, pattern):
            read_file(source)

    def test_file_not_found(self):
        self.assert_error("no_such_file.csv", "File not found")

    def test_folder_instead_of_file(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assert_error(folder, "is a folder")

    def test_path_must_be_text_or_path(self):
        self.assert_error(None, "file name")
        self.assert_error(5, "file name")

    def test_excel_extension_gets_save_as_help(self):
        with tempfile.TemporaryDirectory() as folder:
            path = write_bytes(folder, "data.xlsx", b"PK")
            self.assert_error(path, "CSV UTF-8")

    def test_other_extensions(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assert_error(write(folder, "data.pdf", "x"), "'.pdf' files are not supported")
            self.assert_error(write(folder, "data", "x"), "no extension")

    def test_excel_file_with_csv_name(self):
        with tempfile.TemporaryDirectory() as folder:
            path = write_bytes(folder, "data.csv", b"PK\x03\x04" + b"\x00" * 50)
            self.assert_error(path, "Excel file saved with another extension")

    def test_pdf_file_with_csv_name(self):
        with tempfile.TemporaryDirectory() as folder:
            path = write_bytes(folder, "data.csv", b"%PDF-1.4 rest of file")
            self.assert_error(path, "PDF file")

    def test_binary_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = write_bytes(folder, "data.csv", bytes([0, 1, 2, 3] * 200))
            self.assert_error(path, "does not look like a text file")

    def test_empty_files(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assert_error(write(folder, "a.csv", ""), "empty")
            self.assert_error(write(folder, "b.json", "   \n"), "empty")

    def test_invalid_json_says_where(self):
        with tempfile.TemporaryDirectory() as folder:
            path = write(folder, "data.json", '[{"a": 1,}]')
            self.assert_error(path, "not valid JSON.*line 1")

    def test_json_object_instead_of_list(self):
        with tempfile.TemporaryDirectory() as folder:
            path = write(folder, "data.json", '{"data": []}')
            self.assert_error(path, "list of records.*\"data\"")

    def test_json_single_value(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assert_error(write(folder, "data.json", '"hello"'), "must contain a list of records")

    def test_json_item_that_is_not_a_record(self):
        with tempfile.TemporaryDirectory() as folder:
            path = write(folder, "data.json", '[{"a": 1}, 5]')
            self.assert_error(path, "Record 2")

    def test_errors_are_value_errors_too(self):
        self.assertTrue(issubclass(DataCheckError, ValueError))
        with self.assertRaises(ValueError):
            read_file("no_such_file.csv")


class RulesTests(unittest.TestCase):
    def test_valid_rules_are_accepted(self):
        self.assertEqual(load_rules(RULES), RULES)

    def test_unknown_format_is_rejected(self):
        with self.assertRaisesRegex(DataCheckError, "Unknown format 'emial'"):
            load_rules({"Email": {"format": "emial"}})

    def test_unknown_rule_is_rejected(self):
        with self.assertRaisesRegex(DataCheckError, "Unknown rule"):
            load_rules({"Email": {"requird": True}})

    def test_min_needs_a_number_type(self):
        with self.assertRaisesRegex(DataCheckError, "needs type"):
            load_rules({"Name": {"min": 1}})


class AcceptedStyleTests(unittest.TestCase):
    def test_number_styles(self):
        self.assertEqual(parse_number("30,000"), 30000)
        self.assertEqual(parse_number("₹40,000"), 40000)
        self.assertEqual(parse_number("1,00,000", "integer"), 100000)
        self.assertEqual(parse_number("Rs. 500"), 500)
        self.assertEqual(parse_number("-12.5"), -12.5)
        self.assertEqual(parse_number("85%"), 85)
        self.assertEqual(parse_number("30000.00", "integer"), 30000)
        self.assertEqual(parse_number("1 000"), 1000)

    def test_bad_numbers(self):
        for text in ["abc", "1,2", "1_000", "nan", "inf", "", "12.5.1", "%", "5%5"]:
            self.assertIsNone(parse_number(text), text)
        self.assertIsNone(parse_number("12.5", "integer"))

    def test_date_styles(self):
        for text in ["2026-11-10", "10/11/2026", "10-11-2026", "10.11.2026", "2026/11/10"]:
            self.assertTrue(is_date(text), text)
        for text in ["31/02/2026", "2026-13-45", "hello", "10/11/26"]:
            self.assertFalse(is_date(text), text)

    def test_dates_with_times(self):
        for text in ["2026-01-05 10:30", "2026-01-05T10:30:00Z", "2026-01-05 10:30:00+05:30",
                     "05/01/2026 10:30 PM", "2026-01-05T10:30:00.123"]:
            self.assertTrue(is_date(text), text)
        for text in ["2026-01-05 25:00", "2026-01-05 10:61", "2026-01-05 13:00 PM", "2026-01-05 10:30:61"]:
            self.assertFalse(is_date(text), text)

    def test_phone_styles(self):
        for text in ["9876543210", "+91 98765 43210", "98765-43210", "(987) 654-3210"]:
            self.assertTrue(is_phone(text), text)
        for text in ["12345", "abc", "98765432101234567"]:
            self.assertFalse(is_phone(text), text)

    def test_email_styles(self):
        self.assertTrue(is_email("a.b@example.co.in"))
        for text in ["arun@example", "no at sign", "a@b@c.com", "a@b..com", "a@.com"]:
            self.assertFalse(is_email(text), text)

    def test_column_words(self):
        self.assertEqual(column_words("Email ID"), {"email", "id"})
        self.assertEqual(column_words("DateOfBirth"), {"date", "of", "birth"})
        self.assertEqual(column_words("E-mail"), {"e", "mail"})


class EngineTests(unittest.TestCase):
    def test_sample_file_finds_exactly_the_known_errors(self):
        report = check_with_rules(SAMPLE, RULES)
        expected = {
            (3, "Email", "missing"),
            (4, "Email", "invalid_format"),
            (4, "Salary", "invalid_type"),
            (5, "Employee ID", "duplicate"),
        }
        self.assertEqual(found(report), expected)

    def test_summary_numbers(self):
        summary = check_with_rules(SAMPLE, RULES).summary
        self.assertEqual(summary["total_records"], 4)
        self.assertEqual(summary["records_with_issues"], 3)
        self.assertEqual(summary["records_without_issues"], 1)
        self.assertEqual(summary["total_errors"], 4)

    def test_sensitive_values_are_masked(self):
        report = check_with_rules(SAMPLE, RULES)
        bad_email = [e for e in report.errors if e["error_type"] == "invalid_format"][0]
        self.assertNotEqual(bad_email["value"], "arun@example")
        self.assertTrue(bad_email["value"].startswith("ar"))

    def test_duplicate_points_to_first_row(self):
        report = check_with_rules(SAMPLE, RULES)
        duplicate = [e for e in report.errors if e["error_type"] == "duplicate"][0]
        self.assertIn("row 2", duplicate["reason"])

    def test_missing_required_column(self):
        with tempfile.TemporaryDirectory() as folder:
            path = write(folder, "data.csv", "Name\nRavi\n")
            report = check_with_rules(path, {"Name": {"required": True}, "Email": {"required": True}})
        self.assertEqual(found(report), {(None, "Email", "schema")})

    def test_out_of_range(self):
        with tempfile.TemporaryDirectory() as folder:
            path = write(folder, "data.csv", "Salary\n-5\n100\n")
            report = check_with_rules(path, {"Salary": {"type": "number", "min": 0, "max": 50}})
        self.assertEqual(found(report), {(2, "Salary", "out_of_range"), (3, "Salary", "out_of_range")})

    def test_json_file_is_checked(self):
        with tempfile.TemporaryDirectory() as folder:
            path = write(folder, "data.json", json.dumps([
                {"Email": "a@b.com"},
                {"Email": ""},
                {"Email": "bad"},
            ]))
            report = check_with_rules(path, {"Email": {"required": True, "format": "email"}})
        self.assertEqual(found(report), {(2, "Email", "missing"), (3, "Email", "invalid_format")})

    def test_duplicate_rows(self):
        with tempfile.TemporaryDirectory() as folder:
            path = write(folder, "data.csv", "A,B\n1,x\n2,y\n1,x\n")
            report = check_with_rules(path, {"A": {"required": True}})
        self.assertEqual(found(report), {(4, "(entire row)", "duplicate_row")})

    def test_clean_file_has_no_errors(self):
        with tempfile.TemporaryDirectory() as folder:
            path = write(folder, "data.csv", "Name\nRavi\nSita\n")
            report = check_with_rules(path, {"Name": {"required": True}})
        self.assertFalse(report.has_errors())
        self.assertIn("No problems found.", report.to_text())


class DetectorTests(unittest.TestCase):
    def test_students_exact_errors(self):
        self.assertEqual(found(check(STUDENTS)), STUDENT_ERRORS)

    def test_students_summary(self):
        summary = check(STUDENTS).summary
        self.assertEqual(summary["total_records"], 25)
        self.assertEqual(summary["records_with_issues"], 8)
        self.assertEqual(summary["records_without_issues"], 17)
        self.assertEqual(summary["total_errors"], 9)

    def test_students_detected_rules(self):
        rules = check(STUDENTS).rules
        self.assertTrue(rules["Roll No"]["unique"])
        self.assertTrue(rules["Roll No"]["required"])
        self.assertEqual(rules["Email"]["format"], "email")
        self.assertEqual(rules["Mobile"]["format"], "phone")
        self.assertNotIn("type", rules["Mobile"])
        self.assertEqual(rules["Date of Birth"]["format"], "date")
        self.assertEqual(rules["Marks"]["type"], "number")
        self.assertNotIn("Remarks", rules)

    def test_sales_exact_errors(self):
        self.assertEqual(found(check(SALES)), SALES_ERRORS)

    def test_repeating_product_code_is_not_unique(self):
        rules = check(SALES).rules
        self.assertNotIn("unique", rules["Product Code"])
        self.assertTrue(rules["Order ID"]["unique"])

    def test_small_file_is_not_guessed(self):
        report = check(SAMPLE)
        self.assertEqual(report.errors, [])
        self.assertEqual(report.rules, {})
        self.assertTrue(any("Only 4 records" in note for note in report.notes))

    def test_file_with_no_records_says_so(self):
        with tempfile.TemporaryDirectory() as folder:
            for name, text in [("a.csv", "Name,Email\n"), ("b.json", "[]")]:
                report = check(write(folder, name, text))
                self.assertEqual(report.errors, [], name)
                self.assertEqual(report.summary["total_records"], 0, name)
                self.assertTrue(any("no records" in note for note in report.notes), name)

    def test_long_numbers_without_a_phone_name_are_not_phones(self):
        text = "Reference\n" + "\n".join(str(1000000000 + i) for i in range(10)) + "\n"
        with tempfile.TemporaryDirectory() as folder:
            rules = check(write(folder, "data.csv", text)).rules
        self.assertNotIn("format", rules["Reference"])
        self.assertEqual(rules["Reference"]["type"], "integer")

    def test_email_found_from_values_when_name_gives_no_hint(self):
        text = "Contact\n" + "\n".join(f"user{i}@example.com" for i in range(10)) + "\n"
        with tempfile.TemporaryDirectory() as folder:
            rules = check(write(folder, "data.csv", text)).rules
        self.assertEqual(rules["Contact"]["format"], "email")

    def test_name_hint_with_wrong_values_gives_a_note(self):
        text = "Email\nabc\ndef\nghi\njkl\nmno\na@b.com\n"
        with tempfile.TemporaryDirectory() as folder:
            report = check(write(folder, "data.csv", text))
        self.assertNotIn("format", report.rules["Email"])
        self.assertTrue(any("Email" in note for note in report.notes))

    def test_timestamps_in_a_date_column_are_not_errors(self):
        lines = ["Created Date"] + [f"2026-01-{day:02d} 10:30:00" for day in range(1, 11)]
        with tempfile.TemporaryDirectory() as folder:
            report = check(write(folder, "data.csv", "\n".join(lines) + "\n"))
        self.assertEqual(report.rules["Created Date"]["format"], "date")
        self.assertEqual(report.errors, [])

    def test_percentages_are_numbers(self):
        lines = ["Attendance"] + [f"{70 + i}%" for i in range(10)] + ["abc"]
        with tempfile.TemporaryDirectory() as folder:
            report = check(write(folder, "data.csv", "\n".join(lines) + "\n"))
        self.assertEqual(found(report), {(12, "Attendance", "invalid_type")})

    def test_structure_problems_are_reported_as_errors(self):
        lines = ["Name,Email"] + [f"N{i},n{i}@x.com" for i in range(8)] + ["Broken"] + [""]
        with tempfile.TemporaryDirectory() as folder:
            report = check(write(folder, "data.csv", "\n".join(lines) + "\n"))
        self.assertEqual(found(report), {
            (10, "(entire row)", "structure"),
            (11, "(entire row)", "structure"),
        })
        self.assertEqual(report.summary["total_records"], 9)
        self.assertEqual(report.summary["records_with_issues"], 1)
        self.assertEqual(report.summary["records_without_issues"], 8)

    def test_detect_rules_returns_rules_and_notes(self):
        columns, records, _ = read_file(STUDENTS)
        rules, notes = detect_rules(columns, records)
        self.assertIn("Roll No", rules)
        self.assertEqual(notes, [])


class ReportTests(unittest.TestCase):
    def test_long_and_multiline_values_stay_on_one_line(self):
        long_text = "x" * 100
        text = f'Name,Score\n"line one\nline two",1\n{long_text},2\n'
        with tempfile.TemporaryDirectory() as folder:
            path = write(folder, "data.csv", text)
            report = check_with_rules(path, {"Name": {"type": "number"}})
        output = report.to_text()
        self.assertIn("line one line two", output)
        self.assertNotIn("line one\nline two", output)
        self.assertNotIn(long_text, output)
        self.assertIn("...", output)


class ExportTests(unittest.TestCase):
    def test_export_csv_has_only_problem_rows(self):
        report = check_with_rules(SAMPLE, RULES)
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / "problems.csv"
            count = report.export(out)
            with open(out, newline="", encoding="utf-8") as f:
                rows = list(csv.reader(f))
        self.assertEqual(count, 3)
        self.assertEqual([r[0] for r in rows[1:]], ["3", "4", "5"])
        self.assertEqual(rows[0][0], "File Row")
        self.assertEqual(rows[0][-1], "Problems")

    def test_export_students_counts_problem_records(self):
        report = check(STUDENTS)
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / "problems.csv"
            self.assertEqual(report.export(out), 8)

    def test_export_json(self):
        report = check_with_rules(SAMPLE, RULES)
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / "problems.json"
            report.export(out)
            data = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual([item["row"] for item in data], [3, 4, 5])
        self.assertEqual(len(data[1]["problems"]), 2)

    def test_export_blocks_spreadsheet_formulas(self):
        text = "Name,Email\n=1+1,bad\n-5,bad2\n+91 98765 43210,bad3\n-1+1,bad4\n@cmd,bad5\n"
        with tempfile.TemporaryDirectory() as folder:
            source = write(folder, "data.csv", text)
            report = check_with_rules(source, {"Email": {"format": "email"}})
            out = Path(folder) / "problems.csv"
            report.export(out)
            with open(out, newline="", encoding="utf-8") as f:
                rows = list(csv.reader(f))
        names = [r[1] for r in rows[1:]]
        self.assertEqual(names, ["'=1+1", "-5", "+91 98765 43210", "'-1+1", "'@cmd"])

    def test_original_files_are_never_changed(self):
        for source in (SAMPLE, STUDENTS, SALES):
            before = hashlib.sha256(source.read_bytes()).hexdigest()
            report = check(source)
            with tempfile.TemporaryDirectory() as folder:
                report.export(Path(folder) / "problems.csv")
            after = hashlib.sha256(source.read_bytes()).hexdigest()
            self.assertEqual(before, after, source.name)

    def test_export_cannot_overwrite_the_original(self):
        report = check(STUDENTS)
        with self.assertRaisesRegex(DataCheckError, "different from the original"):
            report.export(STUDENTS)

    def test_export_rejects_other_file_types(self):
        report = check(STUDENTS)
        with self.assertRaisesRegex(DataCheckError, r"\.csv or \.json"):
            report.export("problems.txt")

    def test_export_to_a_missing_folder(self):
        report = check(STUDENTS)
        with self.assertRaisesRegex(DataCheckError, "does not exist"):
            report.export("no_such_folder/problems.csv")


if __name__ == "__main__":
    unittest.main()
