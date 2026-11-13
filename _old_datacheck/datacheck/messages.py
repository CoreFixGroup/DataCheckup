EXCEL_HELP = "In Excel, choose File > Save As > CSV UTF-8 (Comma delimited), then check that file."

PATH_NOT_TEXT = "The path must be a file name such as 'data.csv'."
FILE_NOT_FOUND = "File not found: '{path}'. Check the file name and the folder."
IS_A_FOLDER = "'{path}' is a folder, not a file."
EXCEL_NOT_SUPPORTED = "Excel files are not supported yet. " + EXCEL_HELP
UNSUPPORTED_TYPE = "'{suffix}' files are not supported. Use a .csv or .json file."
NO_EXTENSION = "The file has no extension. Use a .csv or .json file."
NO_PERMISSION = "No permission to read '{path}'."
CSV_UNREADABLE = (
    "The CSV file could not be read ({reason}). "
    "Check the file for a quote mark (\") that was opened but never closed."
)

EXCEL_WITH_OTHER_NAME = "This looks like an Excel file saved with another extension. " + EXCEL_HELP
LOOKS_LIKE_PDF = "This looks like a PDF file, not a CSV or JSON file."
NOT_A_TEXT_FILE = "This does not look like a text file, so it cannot be read as CSV or JSON."
ENCODING_UNKNOWN = (
    "The text encoding of this file is not recognised. "
    "Open it in Excel and save it as CSV UTF-8, then try again."
)
FILE_EMPTY = "The file is empty."

JSON_INVALID = "The file is not valid JSON: {reason} (line {line}, column {column})."
JSON_IS_OBJECT = (
    "The JSON file contains one object, but DataCheck needs a list of records "
    "like [{...}, {...}]. If your records are inside a key such as \"data\", "
    "move them to the top level."
)
JSON_NOT_LIST = "The JSON file must contain a list of records like [{...}, {...}]."
JSON_BAD_RECORD = (
    "Record {number} is not a record with named fields. "
    "Every item in the list must look like {{'Name': 'Ravi'}}."
)

COLUMN_WITHOUT_NAME = "Column has no name"
COLUMN_WITHOUT_NAME_FIX = "Give this column a name in the header row"
DUPLICATE_COLUMN = "Duplicate column name '{name}'"
DUPLICATE_COLUMN_FIX = "Give each column a different name"
EMPTY_ROW = "Row is completely empty"
EMPTY_ROW_FIX = "Delete the empty row"
WRONG_VALUE_COUNT = "Row has {found} values but the header has {expected} columns"
WRONG_VALUE_COUNT_FIX = "Check for a missing or extra separator in this row"

RULES_NOT_DICT = "Rules must be a dictionary of column names"
COLUMN_RULES_NOT_DICT = "Rules for '{column}' must be a dictionary"
UNKNOWN_RULE = "Unknown rule {names} for column '{column}'"
UNKNOWN_TYPE = "Unknown type '{value}' for column '{column}'"
UNKNOWN_FORMAT = "Unknown format '{value}' for column '{column}'"
LIMIT_NEEDS_NUMBER_TYPE = "'{limit}' needs type 'integer' or 'number' for column '{column}'"
LIMIT_NOT_A_NUMBER = "'{limit}' must be a number for column '{column}'"
PATTERN_NOT_TEXT = "The pattern for column '{column}' must be text."
PATTERN_INVALID = "The pattern for column '{column}' is not a valid pattern: {reason}"
ALLOWED_NOT_LIST = "'allowed' for column '{column}' must be a list with at least one value, for example ['Male', 'Female']"
MESSAGE_NOT_TEXT = "'message' for column '{column}' must be text."
UNKNOWN_COLUMN_RULE = (
    "Rules were given for column '{column}', but the file has no column with that name. "
    "Columns found: {columns}."
)
CUSTOM_RULES_APPLIED = "Your own rules were applied to: {columns}. All other columns use the detected rules."

PATTERN_MISMATCH = "Value does not match the required pattern {pattern}"
PATTERN_FIX = "Change the value so it follows the rule set for this column"
NOT_ALLOWED = "Value is not one of the allowed values"
NOT_ALLOWED_FIX = "Use one of: {values}"

MISSING_COLUMN = "Required column is missing from the file"
MISSING_COLUMN_FIX = "Add a column named '{column}'"
MISSING_VALUE = "Missing value"
MISSING_VALUE_FIX = "Enter a value for {column}"
WRONG_TYPE = "Invalid data type, expected {expected}"
WRONG_TYPE_FIX = "Use a number like 30000"
EXPECTED_NUMBER = "a number"
EXPECTED_WHOLE_NUMBER = "a whole number"
BELOW_MINIMUM = "Value is below the minimum of {limit}"
BELOW_MINIMUM_FIX = "Use a value of {limit} or more"
ABOVE_MAXIMUM = "Value is above the maximum of {limit}"
ABOVE_MAXIMUM_FIX = "Use a value of {limit} or less"
WRONG_FORMAT = "Invalid {format} format"
DUPLICATE_VALUE = "Duplicate value (first seen in row {row})"
DUPLICATE_VALUE_FIX = "Make sure each value is unique"
DUPLICATE_ROW = "Duplicate row (same as row {row})"
DUPLICATE_ROW_FIX = "Remove the repeated record"

FORMAT_FIX = {
    "email": "Use a format like name@example.com",
    "phone": "Use 10 to 13 digits, for example 9876543210",
    "date": "Use a real date like 2026-11-10 or 10-11-2026 (day first)",
}
FORMAT_NAMES = {
    "email": "email",
    "phone": "phone number",
    "date": "date",
}

NO_RECORDS = "The file has no records, so there is nothing to check."
TOO_FEW_RECORDS = (
    "Only {found} records found. At least {needed} are needed "
    "to detect rules, so only repeated rows were checked."
)
NAME_SUGGESTS = (
    "Column '{column}' has a name that suggests {kind} values, "
    "but most values do not match, so its format was not checked."
)

EXPORT_SAME_FILE = "The export file must be different from the original file. The original is never changed."
EXPORT_BAD_TYPE = "The export file name must end with .csv or .json."
EXPORT_FOLDER_MISSING = "The folder '{folder}' does not exist."
EXPORT_WRITE_FAILED = "Could not write '{path}': {reason}."

ERROR_LABELS = {
    "structure": "File-structure errors",
    "missing": "Missing-value errors",
    "duplicate": "Duplicate errors",
    "duplicate_row": "Duplicate-row errors",
    "invalid_format": "Invalid-format errors",
    "invalid_type": "Data-type errors",
    "out_of_range": "Out-of-range errors",
    "not_allowed": "Not-allowed-value errors",
    "schema": "Schema errors",
}
