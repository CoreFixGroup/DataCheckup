import re

SUPPORTED_SUFFIXES = (".csv", ".json")
EXCEL_SUFFIXES = (".xlsx", ".xls", ".xlsm")
EXPORT_SUFFIXES = (".csv", ".json")

DELIMITERS = [",", ";", "\t", "|"]
ENCODINGS = ["utf-8-sig", "cp1252"]

UTF16_MARKS = (b"\xff\xfe", b"\xfe\xff")
EXCEL_SIGNATURE = b"PK\x03\x04"
PDF_SIGNATURE = b"%PDF"
TEXT_CONTROL_BYTES = (9, 10, 13)

HEAD_BYTES = 4096
READ_CHUNK = 1024 * 1024
HEADER_SEARCH_LINES = 100
BINARY_LIMIT = 0.05

ENTIRE_ROW = "(entire row)"

RULE_KEYS = {
    "required", "unique", "type", "format", "min", "max",
    "pattern", "allowed", "message", "sensitive",
}
RULE_TYPES = {"text", "integer", "number"}
NUMBER_TYPES = ("integer", "number")
SENSITIVE_FORMATS = {"email", "phone"}

DATE_STYLES = ["%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y", "%Y/%m/%d"]

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s.]+(\.[^@\s.]+)+$")
PHONE_PATTERN = re.compile(r"^\+?[0-9]{10,13}$")
PHONE_SEPARATORS = re.compile(r"[\s\-().]")
DATE_TIME = re.compile(
    r"^([0-9]{1,4}[-/.][0-9]{1,2}[-/.][0-9]{1,4})"
    r"(?:[ T]([0-9]{1,2}):([0-9]{2})(?::([0-9]{2})(?:\.[0-9]+)?)?\s?([AaPp][Mm])?"
    r"\s?(?:Z|[+-][0-9]{2}:?[0-9]{2})?)?$"
)

CURRENCY_MARKS = re.compile(r"rs\.?|inr|[₹$€£]", re.IGNORECASE)
GROUPED_NUMBER = re.compile(r"^[+-]?[0-9]{1,3}(,[0-9]{2,3})+(\.[0-9]+)?$")
WHITESPACE = re.compile(r"\s+")

MIN_RECORDS = 5
MIN_VALUES = 3
AGREE = 0.9
NAME_MATCH = 0.5
DISTINCT = 0.9
SAMPLE_SIZE = 2000

NAME_HINTS = {
    "email": {"email", "mail"},
    "phone": {"phone", "mobile", "cell", "whatsapp", "telephone"},
    "date": {"date", "dob", "birth"},
}
ID_WORDS = {"id", "no", "number", "num", "code", "roll", "sno"}

FORMULA_STARTS = ("=", "@", "\t", "\r")
SIGN_STARTS = ("+", "-")

SHORT_NAME = 40
SHORT_TEXT = 70
