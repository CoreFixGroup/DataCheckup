import csv
import os
import tempfile
import unittest

from datacheckup import DataCheckupError, check


def error_types(report):
    return [error["error_type"] for error in report.errors]


class OverrideTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)

    def make_file(self, header, rows, name="data.csv"):
        path = os.path.join(self.folder.name, name)
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(rows)
        return path

    def marks_file(self, marks):
        rows = [[i, f"Student{i}", mark] for i, mark in enumerate(marks, start=1)]
        return self.make_file(["Roll No", "Name", "Marks"], rows)

    def test_empty_rules_change_nothing(self):
        path = self.marks_file([55, 60, 65, 70, 75, 80, 85, 90, 95, 150])
        plain = check(path)
        with_empty = check(path, rules={})
        self.assertEqual(plain.errors, with_empty.errors)
        self.assertEqual(plain.rules, with_empty.rules)
        self.assertEqual(plain.notes, with_empty.notes)

    def test_added_limit_is_applied(self):
        path = self.marks_file([55, 60, 65, 70, 75, 80, 85, 90, 95, 150])
        self.assertEqual(check(path).errors, [])
        report = check(path, rules={"Marks": {"max": 100}})
        self.assertEqual(len(report.errors), 1)
        error = report.errors[0]
        self.assertEqual((error["row"], error["column"]), (11, "Marks"))
        self.assertEqual(error["error_type"], "out_of_range")
        self.assertIn("above the maximum of 100", error["reason"])

    def test_other_columns_stay_automatic(self):
        path = self.marks_file([55, 60, 65, 70, 75, 80, 85, 90, 95, 150])
        report = check(path, rules={"Marks": {"max": 100}})
        self.assertTrue(report.rules["Roll No"]["unique"])
        self.assertTrue(report.rules["Roll No"]["required"])
        self.assertEqual(report.rules["Marks"]["type"], "integer")
        self.assertEqual(report.rules["Marks"]["max"], 100)

    def test_notes_name_the_customised_columns(self):
        path = self.marks_file([55, 60, 65, 70, 75, 80, 85, 90, 95, 150])
        report = check(path, rules={"Marks": {"max": 100}})
        self.assertTrue(any("Your own rules were applied to: Marks" in n for n in report.notes))

    def test_commas_not_allowed_with_own_message(self):
        rows = [[i, f"Street {i}"] for i in range(1, 6)] + [[6, "Near Sivalayam, Kadagudur"]]
        path = self.make_file(["Id", "Address"], rows)
        rules = {"Address": {"pattern": r"[^,]*", "message": "Commas are not allowed in Address"}}
        report = check(path, rules=rules)
        self.assertEqual(len(report.errors), 1)
        error = report.errors[0]
        self.assertEqual((error["row"], error["column"]), (7, "Address"))
        self.assertEqual(error["reason"], "Commas are not allowed in Address")
        self.assertEqual(error["error_type"], "invalid_format")

    def test_pattern_without_own_message_shows_the_pattern(self):
        rows = [[i, f"AB{i}"] for i in range(1, 6)] + [[6, "xyz"]]
        path = self.make_file(["Id", "Code"], rows)
        report = check(path, rules={"Code": {"pattern": r"[A-Z]{2}[0-9]+"}})
        self.assertEqual(len(report.errors), 1)
        self.assertIn("[A-Z]{2}[0-9]+", report.errors[0]["reason"])

    def test_allowed_values(self):
        genders = ["Male", "Female", "Male", "Female", "Male", "M"]
        path = self.make_file(["Id", "Gender"], [[i, g] for i, g in enumerate(genders, start=1)])
        report = check(path, rules={"Gender": {"allowed": ["Male", "Female"]}})
        self.assertEqual(error_types(report), ["not_allowed"])
        error = report.errors[0]
        self.assertEqual(error["row"], 7)
        self.assertEqual(error["suggestion"], "Use one of: Male, Female")
        self.assertIn("Not-allowed-value errors", report.to_text())

    def test_turn_off_a_detected_type(self):
        marks = [55, 60, 65, 70, 75, 80, 85, 90, 95, "abc"]
        path = self.marks_file(marks)
        self.assertEqual(error_types(check(path)), ["invalid_type"])
        report = check(path, rules={"Marks": {"type": "text"}})
        self.assertEqual(report.errors, [])

    def test_turn_off_required(self):
        names = ["A", "B", "C", "D", "E", "F", "G", "H", "I", ""]
        rows = [[i, name] for i, name in enumerate(names, start=1)]
        path = self.make_file(["Id", "Name"], rows)
        self.assertEqual(error_types(check(path)), ["missing"])
        report = check(path, rules={"Name": {"required": False}})
        self.assertEqual(report.errors, [])

    def test_turn_off_a_detected_format(self):
        emails = [f"user{i}@example.com" for i in range(1, 10)] + ["not-an-email"]
        rows = [[i, e] for i, e in enumerate(emails, start=1)]
        path = self.make_file(["Id", "Email"], rows)
        self.assertEqual(error_types(check(path)), ["invalid_format"])
        report = check(path, rules={"Email": {"format": None}})
        self.assertEqual(report.errors, [])

    def test_limit_on_an_undetected_column_makes_it_a_number_column(self):
        scores = [10, 20, 30, 40, 50, 60, 70, "n/a", "none", "-"]
        rows = [[i, s] for i, s in enumerate(scores, start=1)]
        path = self.make_file(["Id", "Score"], rows)
        self.assertEqual(check(path).errors, [])
        report = check(path, rules={"Score": {"min": 0}})
        self.assertEqual(error_types(report), ["invalid_type"] * 3)

    def test_sensitive_values_are_hidden(self):
        path = self.marks_file([55, 60, 65, 70, 75, 80, 85, 90, 95, 150])
        report = check(path, rules={"Marks": {"max": 100, "sensitive": True}})
        shown = report.errors[0]["value"]
        self.assertIn("*", shown)
        self.assertNotEqual(shown, "150")

    def test_report_describes_the_custom_rules(self):
        path = self.make_file(["Id", "Gender"], [[i, "Male"] for i in range(1, 7)])
        report = check(path, rules={"Gender": {"allowed": ["Male"], "pattern": r"[A-Za-z]+"}})
        text = report.to_text()
        self.assertIn("allowed values only", text)
        self.assertIn("custom pattern", text)

    def test_rules_for_a_missing_column_give_a_note(self):
        path = self.marks_file([55, 60, 65, 70, 75, 80, 85, 90, 95, 100])
        report = check(path, rules={"Marks2": {"max": 5}})
        joined = " ".join(report.notes)
        self.assertIn("'Marks2'", joined)
        self.assertIn("no column with that name", joined)
        self.assertIn("Columns found: Roll No, Name, Marks", joined)
        self.assertEqual(report.errors, [])

    def test_required_column_that_is_missing_is_an_error(self):
        path = self.marks_file([55, 60, 65, 70, 75, 80, 85, 90, 95, 100])
        report = check(path, rules={"Phone": {"required": True}})
        self.assertEqual(error_types(report), ["schema"])
        self.assertIn("Required column is missing", report.errors[0]["reason"])

    def test_custom_rules_work_on_small_files_too(self):
        path = self.make_file(["Id", "Marks"], [[1, 50], [2, 150]])
        report = check(path, rules={"Marks": {"max": 100}})
        self.assertEqual(error_types(report), ["out_of_range"])

    def test_custom_rules_work_on_json(self):
        import json
        path = os.path.join(self.folder.name, "data.json")
        records = [{"id": i, "marks": m} for i, m in enumerate([50, 60, 70, 80, 90, 150], start=1)]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(records, f)
        report = check(path, rules={"marks": {"max": 100}})
        self.assertEqual(error_types(report), ["out_of_range"])
        self.assertEqual(report.errors[0]["row"], 6)


class OverrideMistakeTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = os.path.join(self.folder.name, "data.csv")
        with open(self.path, "w", encoding="utf-8") as f:
            f.write("Id,Marks\n1,50\n2,60\n3,70\n4,80\n5,90\n")

    def assert_rejected(self, rules, text):
        with self.assertRaisesRegex(DataCheckupError, text):
            check(self.path, rules=rules)

    def test_rules_must_be_a_dictionary(self):
        self.assert_rejected([("Marks", 100)], "Rules must be a dictionary")

    def test_rules_for_a_column_must_be_a_dictionary(self):
        self.assert_rejected({"Marks": 100}, "Rules for 'Marks' must be a dictionary")

    def test_unknown_rule_word(self):
        self.assert_rejected({"Marks": {"maxx": 100}}, "Unknown rule .*maxx.* for column 'Marks'")

    def test_unknown_type(self):
        self.assert_rejected({"Marks": {"type": "decimal"}}, "Unknown type 'decimal'")

    def test_unknown_format(self):
        self.assert_rejected({"Marks": {"format": "emial"}}, "Unknown format 'emial'")

    def test_limit_must_be_a_number(self):
        self.assert_rejected({"Marks": {"max": "100"}}, "'max' must be a number for column 'Marks'")

    def test_limit_with_text_type(self):
        self.assert_rejected(
            {"Marks": {"type": "text", "min": 0}},
            "'min' needs type 'integer' or 'number' for column 'Marks'",
        )

    def test_pattern_must_be_text(self):
        self.assert_rejected({"Marks": {"pattern": 5}}, "pattern for column 'Marks' must be text")

    def test_pattern_must_be_valid(self):
        self.assert_rejected({"Marks": {"pattern": "[a-"}}, "pattern for column 'Marks' is not a valid pattern")

    def test_allowed_must_be_a_list(self):
        self.assert_rejected({"Marks": {"allowed": "Male"}}, "'allowed' for column 'Marks' must be a list")

    def test_allowed_must_not_be_empty(self):
        self.assert_rejected({"Marks": {"allowed": []}}, "'allowed' for column 'Marks' must be a list")

    def test_message_must_be_text(self):
        self.assert_rejected({"Marks": {"message": 5}}, "'message' for column 'Marks' must be text")

    def test_bad_rules_are_reported_before_the_file_is_read(self):
        with self.assertRaisesRegex(DataCheckupError, "Rules must be a dictionary"):
            check("this_file_does_not_exist.csv", rules=["x"])


if __name__ == "__main__":
    unittest.main()
