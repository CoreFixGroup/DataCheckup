import importlib.util
import os
import subprocess
import sys
import tempfile
import time

SIZES = [10_000, 100_000, 500_000, 1_000_000]
COLUMNS = ["Roll No", "Name", "Email", "Mobile", "Date of Birth", "Marks", "City"]
CITIES = ["Hyderabad", "Vijayawada", "Guntur", "Chirala"]


def make_file(path, rows):
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(",".join(COLUMNS) + "\n")
        for i in range(1, rows + 1):
            email = "broken-email" if i % 1000 == 0 else f"student{i}@college.edu"
            marks = "abc" if i % 1500 == 0 else 40 + i % 60
            mobile = f"98765{i % 100000:05d}"
            birth = f"2004-05-{i % 28 + 1:02d}"
            f.write(f"R{i:08d},Student {i},{email},{mobile},{birth},{marks},{CITIES[i % 4]}\n")


def expected_errors(rows):
    return rows // 1000 + rows // 1500


def peak_memory_mb():
    import resource
    size = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return size / (1024 * 1024) if sys.platform == "darwin" else size / 1024


def measure(kind, path):
    if kind == "datacheckup":
        from datacheckup import check
        start = time.perf_counter()
        result = check(path).summary["total_errors"]
    else:
        import pandas
        read = pandas.read_json if path.endswith(".json") else pandas.read_csv
        start = time.perf_counter()
        result = len(read(path))
    seconds = time.perf_counter() - start
    print(f"{seconds:.3f} {result} {peak_memory_mb():.0f}")


def run_in_new_process(kind, path):
    command = [sys.executable, __file__, "--measure", kind, path]
    output = subprocess.run(command, capture_output=True, text=True, check=True).stdout.split()
    return float(output[0]), int(output[1]), int(output[2])


def show_row(label, size_mb, datacheckup, pandas_seconds, expected):
    seconds, errors, memory = datacheckup
    speed = f"{int(label_rows(label) / seconds):,}" if label_rows(label) else "-"
    pandas_text = "-" if pandas_seconds is None else f"{pandas_seconds:.2f}"
    verdict = "-" if expected is None else ("ok" if errors == expected else f"expected {expected}")
    print(f"{label:>12} | {size_mb:>7.1f} | {seconds:>10.2f} | {speed:>10} | {memory:>7} | {errors:>7} {verdict:<4} | {pandas_text:>10}")


def label_rows(label):
    digits = label.replace(",", "")
    return int(digits) if digits.isdigit() else 0


def main(paths):
    has_pandas = importlib.util.find_spec("pandas") is not None
    print(f"{'rows':>12} | {'file MB':>7} | {'DataCheckup s':>10} | {'rows/sec':>10} | {'peak MB':>7} | {'errors':>12} | {'pandas read s':>10}")
    print("-" * 95)
    with tempfile.TemporaryDirectory() as folder:
        jobs = []
        if paths:
            jobs = [(os.path.basename(p), p, None) for p in paths]
        else:
            for rows in SIZES:
                path = os.path.join(folder, f"students_{rows}.csv")
                make_file(path, rows)
                jobs.append((f"{rows:,}", path, expected_errors(rows)))
        for label, path, expected in jobs:
            size_mb = os.path.getsize(path) / (1024 * 1024)
            datacheckup = run_in_new_process("datacheckup", path)
            pandas_seconds = run_in_new_process("pandas", path)[0] if has_pandas else None
            show_row(label, size_mb, datacheckup, pandas_seconds, expected)
    print()
    print("DataCheckup checks every value. pandas only reads the file, so it is faster but checks nothing.")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--measure":
        measure(sys.argv[2], sys.argv[3])
    else:
        main(sys.argv[1:])
