"""Discovery and loading of raw sales Excel files."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.constants import OPTIONAL_COLUMNS, REQUIRED_COLUMNS
from src.exceptions import DataDiscoveryError, DataLoadError, NoDataFoundError
from src.models import FileInfo

EXCEL_EXTENSIONS = (".xlsx", ".xlsm", ".xls")


def discover_files(input_folder: Path) -> list[Path]:
    """Return a sorted list of Excel files inside *input_folder*.

    Raises:
        DataDiscoveryError: if the folder does not exist or is not a directory.
        NoDataFoundError: if the folder exists but contains no Excel files.
    """
    if not input_folder.exists():
        raise DataDiscoveryError(
            f"Input folder does not exist: {input_folder}. "
            "Create it or run `python run.py --generate-data` first."
        )
    if not input_folder.is_dir():
        raise DataDiscoveryError(f"Input path is not a directory: {input_folder}")

    files = sorted(p for p in input_folder.glob("*") if p.suffix.lower() in EXCEL_EXTENSIONS)
    if not files:
        raise NoDataFoundError(
            f"No Excel files found in {input_folder}. "
            "Run `python run.py --generate-data` to create sample data."
        )
    return files


def _find_worksheet(path: Path) -> str | None:
    """Pick the best worksheet in a workbook.

    Prefers a sheet named ``Sales``; otherwise the first sheet with the most
    required columns.
    """
    try:
        sheets = pd.ExcelFile(path).sheet_names
    except Exception as exc:  # noqa: BLE001 - delegate to the caller's error handling
        raise DataLoadError(f"Could not open workbook {path.name}: {exc}") from exc

    if "Sales" in sheets:
        return "Sales"

    best_sheet: str | None = None
    best_score = -1
    for sheet in sheets:
        try:
            sample = pd.read_excel(path, sheet_name=sheet, nrows=5)
        except Exception:
            continue
        score = sum(1 for col in REQUIRED_COLUMNS if col in sample.columns)
        if score > best_score:
            best_score = score
            best_sheet = sheet
    return best_sheet


def load_file(path: Path) -> tuple[pd.DataFrame, str]:
    """Load a single workbook into a DataFrame.

    Returns a tuple of ``(frame, sheet_name)``. Raises ``DataLoadError`` if the
    file cannot be read or the required columns are missing.
    """
    sheet = _find_worksheet(path)
    if sheet is None:
        raise DataLoadError(f"No readable worksheet found in {path.name}")

    try:
        frame = pd.read_excel(path, sheet_name=sheet, dtype=object)
    except Exception as exc:  # noqa: BLE001
        raise DataLoadError(f"Failed to read {path.name} (sheet {sheet!r}): {exc}") from exc

    missing = [col for col in REQUIRED_COLUMNS if col not in frame.columns]
    if missing:
        raise DataLoadError(
            f"{path.name}: missing required columns: {', '.join(missing)}"
        )

    frame["Source File"] = path.name
    return frame, sheet


def load_files(files: list[Path]) -> tuple[pd.DataFrame, list[FileInfo]]:
    """Load all discovered files and combine them into one DataFrame.

    A file that fails to load is logged and recorded in the returned metadata
    rather than aborting the whole run. If every file fails, ``DataLoadError``
    is raised.
    """
    frames: list[pd.DataFrame] = []
    file_infos: list[FileInfo] = []

    for path in files:
        try:
            frame, sheet = load_file(path)
        except DataLoadError as exc:
            file_infos.append(FileInfo(path=path, rows_loaded=0, sheet_used="", status="error", message=str(exc)))
            continue
        frames.append(frame)
        file_infos.append(FileInfo(path=path, rows_loaded=len(frame), sheet_used=sheet))

    if not frames:
        problems = [f"  - {info.path.name}: {info.message}" for info in file_infos]
        raise DataLoadError(
            "All input files failed to load:\n" + "\n".join(problems)
        )

    combined = pd.concat(frames, ignore_index=True)
    return combined, file_infos
