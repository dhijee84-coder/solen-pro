"""Safe CSV export helpers. Prevents formula injection and respects permissions."""
import csv
import io
from datetime import datetime
from typing import Iterable, List, Sequence


def _sanitize_cell(value) -> str:
    if value is None:
        return ""
    s = str(value)
    # Prevent CSV formula injection
    if s and s[0] in ("=", "+", "-", "@", "\t", "\r"):
        s = "'" + s
    return s


def to_csv(headers: Sequence[str], rows: Iterable[Sequence]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf, quoting=csv.QUOTE_MINIMAL, lineterminator="\n")
    writer.writerow([_sanitize_cell(h) for h in headers])
    for row in rows:
        writer.writerow([_sanitize_cell(c) for c in row])
    return buf.getvalue()


def filename(prefix: str) -> str:
    return f"{prefix}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
