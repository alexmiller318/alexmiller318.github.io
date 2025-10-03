#!/usr/bin/env python3
"""Sort Telegram screenshots chronologically based on in-image timestamps.

The script performs the following steps:

1. Reads every image inside an input directory.
2. Extracts all textual content with Tesseract OCR.
3. Detects time stamps (and optionally dates) present in the screenshot text.
4. Combines the most relevant date/time pair to determine an absolute timestamp.
5. Drops duplicate screenshots by comparing OCR text hashes and perceptual image hashes.
6. Writes a CSV manifest sorted by timestamp and optionally copies (or moves)
   the screenshots to a target directory using an ordered prefix.

Run ``python tools/sort_telegram_screenshots.py --help`` for usage details.

Requirements
------------
- Python 3.9+
- Pillow
- pytesseract
- ImageHash
- The Tesseract OCR binary installed and available on your PATH.

Install the Python dependencies with ``pip install -r tools/requirements-sort_telegram_screenshots.txt``.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import logging
import re
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

from PIL import Image
import pytesseract
from shutil import copy2, move as shutil_move


LOG = logging.getLogger("telegram_sorter")

# Regex patterns for date detection.
MONTH_NAMES = (
    "january",
    "february",
    "march",
    "april",
    "may",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
)

MONTH_PATTERN = re.compile(
    r"\b(?:"
    + "|".join(
        f"{name[:3]}(?:{name[3:]})?" if len(name) > 3 else name for name in MONTH_NAMES
    )
    + r")\s+\d{1,2}(?:,\s*\d{4})?\b",
    flags=re.IGNORECASE,
)
NUMERIC_DATE_PATTERNS = [
    re.compile(r"\b\d{4}-\d{1,2}-\d{1,2}\b"),
    re.compile(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b"),
    re.compile(r"\b\d{1,2}\.\d{1,2}\.\d{2,4}\b"),
]
RELATIVE_DATE_PATTERN = re.compile(r"\b(today|yesterday)\b", flags=re.IGNORECASE)

# Regex pattern for 12h/24h times with optional AM/PM.
TIME_PATTERN = re.compile(
    r"\b((?:[01]?\d|2[0-3]):[0-5]\d)(?:\s*([APap][Mm]))?\b"
)


@dataclass
class ScreenshotRecord:
    """Metadata extracted for a single screenshot."""

    source_path: Path
    text_hash: str
    image_hash: str
    text: str
    timestamp: Optional[datetime]
    time_candidates: Sequence[time]
    date_candidates: Sequence[date]
    output_path: Optional[Path] = None

    @property
    def has_timestamp(self) -> bool:
        return self.timestamp is not None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "input_dir",
        type=Path,
        help="Directory containing Telegram screenshots (PNG/JPEG/WEBP).",
    )
    parser.add_argument(
        "output",
        type=Path,
        help=(
            "Target directory where the sorted screenshots will be copied. "
            "A CSV manifest named 'sorted_manifest.csv' is written alongside."
        ),
    )
    parser.add_argument(
        "--default-date",
        type=lambda s: datetime.strptime(s, "%Y-%m-%d").date(),
        help="Fallback date (YYYY-MM-DD) used when a screenshot does not contain an explicit date.",
    )
    parser.add_argument(
        "--assume-year",
        type=int,
        help=(
            "Year to use when month/day mentions omit a year. "
            "Defaults to the year from --today-date, then --default-date, then the current year."
        ),
    )
    parser.add_argument(
        "--today-date",
        type=lambda s: datetime.strptime(s, "%Y-%m-%d").date(),
        help="Concrete date to associate with the word 'Today'. 'Yesterday' uses the day before this date.",
    )
    parser.add_argument(
        "--move",
        action="store_true",
        help="Move files to the output directory instead of copying them.",
    )
    parser.add_argument(
        "--prefix",
        default="img",
        help="Filename prefix to use for sorted screenshots (default: 'img').",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging verbosity (default: INFO).",
    )
    parser.add_argument(
        "--require-timestamps",
        action="store_true",
        help="Exit with an error if any screenshot lacks an in-image timestamp.",
    )
    parser.add_argument(
        "--skip-missing-timestamps",
        action="store_true",
        help="Drop screenshots that do not yield an in-image timestamp instead of placing them at the end.",
    )
    return parser.parse_args()


def normalize_text(text: str) -> str:
    """Normalize OCR text for comparison."""

    simplified = re.sub(r"\s+", " ", text.strip().lower())
    return simplified


def hash_text(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def average_hash(image: Image.Image, hash_size: int = 8) -> str:
    """Compute a perceptual average hash for duplicate detection."""

    if hasattr(Image, "Resampling"):
        resample = Image.Resampling.LANCZOS
    else:  # pragma: no cover - backwards compatibility for Pillow < 9
        resample = Image.LANCZOS

    grayscale = image.convert("L").resize((hash_size, hash_size), resample=resample)
    pixels = list(grayscale.getdata())
    if not pixels:
        return "0"
    avg = sum(pixels) / len(pixels)

    bits = 0
    for pixel in pixels:
        bits = (bits << 1) | (1 if pixel >= avg else 0)
    width = hash_size * hash_size // 4
    return f"{bits:0{width}x}"


def extract_dates(
    text: str,
    *,
    today_date: Optional[date],
    assume_year: Optional[int],
) -> List[date]:
    dates: List[date] = []
    default_year = assume_year
    if default_year is None and today_date is not None:
        default_year = today_date.year

    for match in MONTH_PATTERN.finditer(text):
        value = match.group(0)
        for fmt in ("%B %d, %Y", "%b %d, %Y", "%B %d", "%b %d"):
            try:
                parsed = datetime.strptime(value, fmt)
                if "%Y" in fmt or "%y" in fmt:
                    year = parsed.year
                else:
                    year = default_year if default_year is not None else datetime.now().year
                dates.append(date(year, parsed.month, parsed.day))
                break
            except ValueError:
                continue

    for pattern in NUMERIC_DATE_PATTERNS:
        for match in pattern.finditer(text):
            value = match.group(0)
            for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d/%m/%y", "%m/%d/%y", "%d.%m.%Y", "%d.%m.%y"):
                try:
                    parsed = datetime.strptime(value, fmt)
                    parsed_date = parsed.date()
                    if "%Y" not in fmt and "%y" not in fmt:
                        year = default_year if default_year is not None else datetime.now().year
                        parsed_date = parsed_date.replace(year=year)
                    dates.append(parsed_date)
                    break
                except ValueError:
                    continue

    if today_date:
        for match in RELATIVE_DATE_PATTERN.finditer(text):
            token = match.group(1).lower()
            if token == "today":
                dates.append(today_date)
            elif token == "yesterday":
                dates.append(today_date - timedelta(days=1))

    unique_dates = sorted(set(dates))
    return unique_dates


def extract_times(text: str) -> List[time]:
    times: List[time] = []
    for match in TIME_PATTERN.finditer(text):
        hhmm, ampm = match.groups()
        hour, minute = map(int, hhmm.split(":"))
        if ampm:
            ampm = ampm.lower()
            if ampm == "pm" and hour != 12:
                hour += 12
            if ampm == "am" and hour == 12:
                hour = 0
        times.append(time(hour, minute))
    unique_times = sorted(set(times))
    return unique_times


def combine_timestamp(
    dates: Sequence[date],
    times: Sequence[time],
    *,
    default_date: Optional[date],
) -> Optional[datetime]:
    if not times:
        return None
    base_date: Optional[date] = None
    if dates:
        base_date = dates[-1]  # assume the last mentioned date matches the screenshot messages.
    elif default_date:
        base_date = default_date

    if base_date is None:
        return None

    chosen_time = max(times)
    return datetime.combine(base_date, chosen_time)


def gather_records(
    image_paths: Iterable[Path],
    *,
    default_date: Optional[date],
    today_date: Optional[date],
    assume_year: Optional[int],
) -> List[ScreenshotRecord]:
    records: List[ScreenshotRecord] = []
    seen_text_hashes: Dict[str, Path] = {}
    seen_image_hashes: Dict[str, Path] = {}

    for path in image_paths:
        LOG.info("Processing %s", path.name)
        with Image.open(path) as img:
            image = img.convert("RGB")
            text = pytesseract.image_to_string(image)
            image_hash = average_hash(image)

        normalized = normalize_text(text)
        text_hash = hash_text(normalized)

        if text_hash in seen_text_hashes:
            LOG.warning(
                "Skipping duplicate screenshot %s based on OCR text match with %s",
                path.name,
                seen_text_hashes[text_hash].name,
            )
            continue

        if image_hash in seen_image_hashes:
            LOG.warning(
                "Skipping duplicate screenshot %s based on perceptual image hash match with %s",
                path.name,
                seen_image_hashes[image_hash].name,
            )
            continue

        dates = extract_dates(text, today_date=today_date, assume_year=assume_year)
        times = extract_times(text)
        timestamp = combine_timestamp(dates, times, default_date=default_date)

        record = ScreenshotRecord(
            source_path=path,
            text_hash=text_hash,
            image_hash=image_hash,
            text=text,
            timestamp=timestamp,
            time_candidates=times,
            date_candidates=dates,
        )
        records.append(record)
        seen_text_hashes[text_hash] = path
        seen_image_hashes[image_hash] = path

    return records


def copy_or_move(record: ScreenshotRecord, target: Path, index: int, prefix: str, move: bool) -> Path:
    suffix = record.source_path.suffix.lower()
    new_name = f"{prefix}_{index:03d}{suffix}"
    destination = target / new_name
    counter = 1
    while destination.exists():
        new_name = f"{prefix}_{index:03d}_{counter}{suffix}"
        destination = target / new_name
        counter += 1

    if move:
        shutil_move(str(record.source_path), str(destination))
    else:
        copy2(record.source_path, destination)
    return destination


def write_manifest(records: Sequence[ScreenshotRecord], manifest_path: Path) -> None:
    with manifest_path.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([
            "ordered_index",
            "output_filename",
            "timestamp",
            "source_path",
            "output_path",
            "date_candidates",
            "time_candidates",
            "text_hash",
            "image_hash",
        ])
        for idx, record in enumerate(records, start=1):
            writer.writerow([
                idx,
                record.output_path.name if record.output_path else record.source_path.name,
                record.timestamp.isoformat() if record.timestamp else "",
                str(record.source_path),
                str(record.output_path) if record.output_path else "",
                ";".join(d.isoformat() for d in record.date_candidates),
                ";".join(t.isoformat() for t in record.time_candidates),
                record.text_hash,
                record.image_hash,
            ])


def main() -> None:
    args = parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level))

    if not args.input_dir.is_dir():
        raise SystemExit(f"Input directory not found: {args.input_dir}")

    args.output.mkdir(parents=True, exist_ok=True)

    image_paths = sorted(
        path
        for path in args.input_dir.iterdir()
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
    )
    if not image_paths:
        raise SystemExit("No supported image files found in the input directory.")

    if args.skip_missing_timestamps and args.require_timestamps:
        raise SystemExit("--skip-missing-timestamps and --require-timestamps cannot be combined.")

    assume_year = args.assume_year
    if assume_year is None:
        if args.today_date is not None:
            assume_year = args.today_date.year
        elif args.default_date is not None:
            assume_year = args.default_date.year

    records = gather_records(
        image_paths,
        default_date=args.default_date,
        today_date=args.today_date,
        assume_year=assume_year,
    )

    records_with_timestamps = [r for r in records if r.timestamp]
    records_without_timestamps = [r for r in records if not r.timestamp]

    if args.require_timestamps and records_without_timestamps:
        raise SystemExit(
            "At least one screenshot did not yield an in-image timestamp. "
            "Provide a --default-date, adjust OCR, or rerun with --skip-missing-timestamps."
        )

    if args.skip_missing_timestamps and records_without_timestamps:
        LOG.warning(
            "%d screenshots are missing timestamps and will be omitted due to --skip-missing-timestamps.",
            len(records_without_timestamps),
        )
        sorted_records = sorted(records_with_timestamps, key=lambda r: r.timestamp)
    else:
        if records_without_timestamps:
            LOG.warning(
                "%d screenshots are missing timestamps and will be placed at the end of the ordering.",
                len(records_without_timestamps),
            )
        sorted_records = sorted(records_with_timestamps, key=lambda r: r.timestamp) + records_without_timestamps

    manifest_path = args.output / "sorted_manifest.csv"

    for idx, record in enumerate(sorted_records, start=1):
        original_name = record.source_path.name
        destination = copy_or_move(record, args.output, idx, args.prefix, args.move)
        LOG.info("%s -> %s", original_name, destination.name)
        record.output_path = destination

    write_manifest(sorted_records, manifest_path)
    LOG.info("Wrote manifest to %s", manifest_path)


if __name__ == "__main__":
    main()
