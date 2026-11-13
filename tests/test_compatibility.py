import json
import os
import tempfile
import unittest
from pathlib import Path

from datacheckup import check

try:
    import numpy as np
    import pandas as pd
except ImportError:
    np = None
    pd = None


def found(report):
    return [(e["row"], e["column"], e["error_type"]) for e in report.errors]


@unittest.skipIf(pd is None, "pandas and numpy are not installed")
class PandasNumpyTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.frame = self.make_frame()

    def path(self, name):
        return os.path.join(self.folder.name, name)

    def make_frame(self):
        ids = np.arange(1, 201)
        frame = pd.DataFrame({
            "Student Id": ids,
            "Name": [f"Student {i}" for i in ids],
            "Email": [f"student{i}@college.edu" for i in ids],
            "Marks": np.arange(200) % 60 + 40,
        })
        frame.loc[9, "Email"] = "broken-email"
        frame.loc[19, "Name"] = None
        frame.loc[29, "Student Id"] = 5
        return frame

    def test_csv_written_by_pandas(self):
        path = self.path("students.csv")
        self.frame.to_csv(path, index=False)
        report = check(path)
        self.assertEqual(report.summary["total_records"], len(pd.read_csv(path)))
        self.assertEqual(found(report), [
            (11, "Email", "invalid_format"),
            (21, "Name", "missing"),
            (31, "Student Id", "duplicate"),
        ])

    def test_path_object_is_accepted(self):
        path = self.path("students.csv")
        self.frame.to_csv(path, index=False)
        self.assertEqual(len(check(Path(path)).errors), 3)

    def test_json_written_by_pandas(self):
        path = self.path("students.json")
        self.frame.to_json(path, orient="records")
        report = check(path)
        self.assertEqual(report.summary["total_records"], 200)
        self.assertEqual(found(report), [
            (10, "Email", "invalid_format"),
            (20, "Name", "missing"),
            (30, "Student Id", "duplicate"),
        ])

    def test_forgotten_index_is_reported_clearly(self):
        path = self.path("with_index.csv")
        self.frame.to_csv(path)
        report = check(path)
        structure = [e for e in report.errors if e["error_type"] == "structure"]
        self.assertEqual(len(structure), 1)
        self.assertEqual((structure[0]["row"], structure[0]["column"]), (1, "Column 1"))
        self.assertEqual(structure[0]["reason"], "Column has no name")

    def test_export_can_be_read_back_by_pandas(self):
        path = self.path("students.csv")
        self.frame.to_csv(path, index=False)
        report = check(path)
        out = self.path("problems.csv")
        self.assertEqual(report.export(out), 3)
        back = pd.read_csv(out)
        self.assertEqual(list(back["File Row"]), [11, 21, 31])
        self.assertIn("Problems", back.columns)
        out_json = self.path("problems.json")
        self.assertEqual(report.export(out_json), 3)
        with open(out_json, encoding="utf-8") as f:
            self.assertEqual(len(json.load(f)), 3)

    def test_numpy_numbers_work_as_limits(self):
        path = self.path("students.csv")
        self.frame.to_csv(path, index=False)
        report = check(path, rules={"Marks": {"max": np.int64(60), "min": np.float64(40.0)}})
        expected = int((self.frame["Marks"] > 60).sum())
        marks_errors = [e for e in report.errors if e["column"] == "Marks"]
        self.assertEqual(len(marks_errors), expected)
        self.assertTrue(all(e["error_type"] == "out_of_range" for e in marks_errors))

    def test_pandas_values_work_as_allowed_list(self):
        path = self.path("students.csv")
        self.frame.to_csv(path, index=False)
        allowed = self.frame["Name"].dropna().unique()
        report = check(path, rules={"Name": {"allowed": allowed}})
        self.assertNotIn("not_allowed", [e["error_type"] for e in report.errors])
        report = check(path, rules={"Name": {"allowed": np.array(["Student 1"])}})
        self.assertGreater(
            len([e for e in report.errors if e["error_type"] == "not_allowed"]), 100
        )

    def test_original_file_is_not_changed(self):
        path = self.path("students.csv")
        self.frame.to_csv(path, index=False)
        with open(path, "rb") as f:
            before = f.read()
        report = check(path)
        report.export(self.path("problems.csv"))
        with open(path, "rb") as f:
            self.assertEqual(f.read(), before)


if __name__ == "__main__":
    unittest.main()
