from datacheckup import check

report = check("tests/data/students.csv")
report.show()

count = report.export("problems.csv")
print()
print(f"{count} problem records saved to problems.csv")
