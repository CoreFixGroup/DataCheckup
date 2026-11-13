# datacheckup

A small Python library that reads a CSV or JSON file and tells you the exact row and column of every error, with a plain-words reason and a fix. It finds the rules for each column by itself, lets you override only the ones you choose, and never changes your original file. It needs nothing but the Python standard library.

## Install

```
pip install datacheckup
```

## Use

```python
from datacheckup import check

report = check("students.csv")
report.show()
```

## Override rules for chosen columns

Name only the columns you want to change. Every other column stays automatic.

```python
from datacheckup import check

rules = {
    "Marks": {"min": 10, "max": 80},
}

report = check("students.csv", rules=rules)
report.show()
```

## Good to know

- Rules found automatically are smart guesses. Use your own rules for columns that matter.
- The whole file is loaded into memory, so very large files need a lot of RAM.
- Excel (.xlsx) files must be saved as CSV first.
- Requires Python 3.11 or newer.

## Licence

MIT
