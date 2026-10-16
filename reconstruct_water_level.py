"""Reconstruct 10-minute water-level readings from hourly Excel worksheets.
Pair worksheets by position (not names). Matched old worksheets define their
individual time windows. Extra new worksheets use the overall earliest-to-latest
time window seen in ALL old worksheets. Each new worksheet supplies its own
measured values; PCHIP estimates the intervening 10-minute readings.
"""

from pathlib import Path
from datetime import datetime, time, timedelta
import re

import numpy as np
import pandas as pd
from scipy.interpolate import PchipInterpolator


# ---------------------------- USER SETTINGS -----------------------------
OLD_FILE = Path("water_level.xlsx")
NEW_FILE = Path("water_level_Sept.xlsx")
OUTPUT_DIR = Path("water_level_output3")
OUTPUT_EXCEL = OUTPUT_DIR / "reconstructed_water_levels.xlsx"
TIME_COLUMN = "TIME"
LEVEL_COLUMN = "WATER LEVEL (m) CD"
INTERVAL_MINUTES = 10
# ------------------------------------------------------------------------


def to_minutes(value):
    """Parse common 24-hour/AM-PM/Excel time cells into minutes since midnight."""
    if pd.isna(value):
        return np.nan
    if isinstance(value, (datetime, pd.Timestamp, time)):
        return value.hour * 60 + value.minute + value.second / 60
    if isinstance(value, timedelta):
        return value.total_seconds() / 60
    if isinstance(value, (float, int, np.integer, np.floating)) and not isinstance(value, bool):
        v = float(value)
        if 0 <= v < 1:  # Excel time as fraction of one day
            return v * 1440
        return np.nan
    s = str(value).strip()
    if not s:
        return np.nan
    # Explicit formats eliminate ambiguity in e.g. 12:00:00 AM/PM.
    for fmt in ("%H:%M", "%H:%M:%S", "%I:%M %p", "%I:%M:%S %p"):
        try:
            t = datetime.strptime(s, fmt)
            return t.hour * 60 + t.minute + t.second / 60
        except ValueError:
            continue
    return np.nan


def clean_sheet(frame, name):
    df = frame.copy()
    df.columns = [str(col).strip() for col in df.columns]
    for col in (TIME_COLUMN, LEVEL_COLUMN):
        if col not in df.columns:
            raise ValueError(f"Worksheet '{name}' is missing column '{col}'. Found: {list(df.columns)}")
    df["_minute"] = df[TIME_COLUMN].map(to_minutes)
    df["_level"] = pd.to_numeric(df[LEVEL_COLUMN], errors="coerce")
    df = df.dropna(subset=["_minute", "_level"])
    if df.empty:
        raise ValueError(f"Worksheet '{name}' contains no valid time and water-level pairs")
    # Repeated timestamps must not cause interpolation failure.
    return (df.groupby("_minute", as_index=False)["_level"]
              .mean().sort_values("_minute").reset_index(drop=True))


def hhmm(minute):
    minute = int(round(minute))
    return f"{minute // 60:02d}:{minute % 60:02d}"


def make_times(start, stop, step):
    """Generate 10-minute ticks anchored at old-sheet start, inclusive if aligned."""
    count = int(np.floor((stop - start + 1e-8) / step)) + 1
    return start + np.arange(max(count, 0), dtype=float) * step


def main():
    for file in (OLD_FILE, NEW_FILE):
        if not file.is_file():
            raise FileNotFoundError(f"Excel file not found: {file.resolve()}")

    old_sheets = list(pd.read_excel(OLD_FILE, sheet_name=None, engine="openpyxl").items())
    new_sheets = list(pd.read_excel(NEW_FILE, sheet_name=None, engine="openpyxl").items())
    if not old_sheets or not new_sheets:
        raise ValueError("Both workbooks must contain at least one worksheet")

    # Overall coverage from ALL historical worksheets, regardless of sheet names.
    old_cleaned = [(name, clean_sheet(raw, name)) for name, raw in old_sheets]
    overall_start = min(float(frame["_minute"].min()) for _, frame in old_cleaned)
    overall_stop = max(float(frame["_minute"].max()) for _, frame in old_cleaned)
    print(f"Old workbook: {len(old_sheets)} sheets; new workbook: {len(new_sheets)} sheets")
    print(f"Overall old-data time window: {hhmm(overall_start)}–{hhmm(overall_stop)}")
    if len(new_sheets) > len(old_sheets):
        print(f"Extra new sheets: {len(new_sheets) - len(old_sheets)}; "
              "using overall old-data time window")
    elif len(new_sheets) < len(old_sheets):
        print("Note: unmatched old worksheets will not generate outputs")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    csv_dir = OUTPUT_DIR / "csv"
    csv_dir.mkdir(exist_ok=True)
    summaries = []

    with pd.ExcelWriter(OUTPUT_EXCEL, engine="xlsxwriter") as writer:
        book = writer.book
        head_fmt = book.add_format({"bold": True, "bg_color": "#16365C", "font_color": "white", "border": 1})
        number_fmt = book.add_format({"num_format": "0.00"})

        for i, (new_name, new_raw) in enumerate(new_sheets, 1):
            new = clean_sheet(new_raw, new_name)
            if i <= len(old_cleaned):
                old_name, old = old_cleaned[i - 1]
                start, stop = float(old["_minute"].min()), float(old["_minute"].max())
                range_source = "Paired old worksheet"
            else:
                old_name = "ALL OLD SHEETS (overall range)"
                start, stop = overall_start, overall_stop
                range_source = "Overall old-data window"
            if len(new) < 2:
                raise ValueError(f"New worksheet #{i} ({new_name}) needs at least two distinct time readings")
            # Times are treated as occurring on the same calendar day.
            target = make_times(start, stop, INTERVAL_MINUTES)
            interpolator = PchipInterpolator(new["_minute"], new["_level"], extrapolate=False)
            estimate = interpolator(target)
            # Use rounded numbers for all downstream exports, keeping missing values missing.
            output = pd.DataFrame({
                TIME_COLUMN: [hhmm(m) for m in target],
                LEVEL_COLUMN: np.round(estimate, 2),
            })
            sheet = f"Sheet_{i:02d}"
            output.to_csv(csv_dir / f"{sheet}.csv", index=False, float_format="%.2f", na_rep="")
            output.to_excel(writer, sheet_name=sheet, index=False, startrow=5)
            ws = writer.sheets[sheet]
            ws.write("A1", "Old worksheet", head_fmt)
            ws.write("B1", old_name)
            ws.write("A2", "New worksheet", head_fmt)
            ws.write("B2", new_name)
            ws.write("A3", "Output time range", head_fmt)
            ws.write("B3", f"{hhmm(start)}–{hhmm(stop)}")
            ws.write("A4", "Method", head_fmt)
            ws.write("B4", "PCHIP interpolation")
            ws.write("A5", "Range source", head_fmt)
            ws.write("B5", range_source)
            ws.set_column("A:A", 20)
            ws.set_column("B:B", 24, number_fmt)
            ws.freeze_panes(6, 0)
            ws.autofilter(5, 0, 5 + len(output), 1)

            # Data headers are on Excel row 6. Data are rows 7..(6+n).
            first_row = 6  # zero-indexed
            last_row = first_row + len(output) - 1
            chart = book.add_chart({"type": "line"})
            chart.add_series({
                "name": "Estimated water level",
                "categories": [sheet, first_row, 0, last_row, 0],
                "values": [sheet, first_row, 1, last_row, 1],
                "line": {"color": "#147CB8", "width": 2},
                "marker": {"type": "none"},
            })
            chart.set_title({"name": f"Water Level – {sheet}"})
            chart.set_x_axis({"name": "Time (24-hour)", "num_font": {"rotation": -45}})
            chart.set_y_axis({"name": "Water level (m) CD", "major_gridlines": {"visible": True}})
            chart.set_legend({"position": "bottom"})
            chart.set_size({"width": 850, "height": 420})
            ws.insert_chart("D6", chart)

            missing = int(output[LEVEL_COLUMN].isna().sum())
            summaries.append({
                "Pair": i, "Old Sheet": old_name, "New Sheet": new_name,
                "Range Source": range_source, "Start": hhmm(start), "End": hhmm(stop),
                "Readings": len(output), "Missing (out of range)": missing,
            })
            print(f"Pair {i}: {old_name} -> {new_name}; {hhmm(start)}–{hhmm(stop)}; "
                  f"{len(output)} readings, {missing} unavailable")

        summary = pd.DataFrame(summaries)
        summary.to_excel(writer, sheet_name="Summary", index=False)
        ws = writer.sheets["Summary"]
        ws.set_column("A:A", 10)
        ws.set_column("B:C", 26)
        ws.set_column("D:D", 27)
        ws.set_column("E:F", 12)
        ws.set_column("G:H", 25)
        ws.freeze_panes(1, 0)
        for col, name in enumerate(summary.columns):
            ws.write(0, col, name, head_fmt)

    print(f"\nExcel with embedded graphs: {OUTPUT_EXCEL.resolve()}")
    print(f"CSV worksheets: {csv_dir.resolve()}")
    print("Note: blank estimates mean new measurements do not cover that time.")
    print("Assumption: each worksheet represents one day and does not cross midnight.")


if __name__ == "__main__":
    main()
