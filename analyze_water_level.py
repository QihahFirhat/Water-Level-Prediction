import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from pathlib import Path
import re

# ==========================================
# 1. FILE CONFIGURATION
# ==========================================

BASE_DIR = Path(__file__).resolve().parent

excel_file = BASE_DIR / "water_level.xlsx"
output_folder = BASE_DIR / "graphs"

output_folder.mkdir(exist_ok=True)

# ==========================================
# 2. READ ALL EXCEL SHEETS
# ==========================================

excel = pd.ExcelFile(excel_file)

print(f"Total sheets found: {len(excel.sheet_names)}")
print("Sheets:", excel.sheet_names)

# ==========================================
# 3. PROCESS EACH SHEET
# ==========================================

for sheet_name in excel.sheet_names:

    print(f"\nProcessing: {sheet_name}")

    df = pd.read_excel(excel, sheet_name=sheet_name)

    # Remove extra whitespace in column names
    df.columns = df.columns.astype(str).str.strip()

    # Check required columns
    required_columns = ["TIME", "WATER LEVEL (m) CD"]

    if not all(col in df.columns for col in required_columns):
        print(f"Skipping {sheet_name}: Required columns missing.")
        continue

    # Keep relevant columns
    df = df[required_columns].copy()

    # ======================================
    # 4. CLEAN AND CONVERT DATA
    # ======================================

    # Convert water level to numeric
    df["WATER LEVEL (m) CD"] = pd.to_numeric(
        df["WATER LEVEL (m) CD"],
        errors="coerce"
    )

    # Convert Excel time values to HH:MM strings
    def format_time(value):
        if pd.isna(value):
            return None

        if isinstance(value, (int, float)):
            # Excel time stored as fraction of a day
            minutes = round((float(value) % 1) * 1440)
            return f"{(minutes // 60) % 24:02d}:{minutes % 60:02d}"

        if hasattr(value, "strftime"):
            return value.strftime("%H:%M")

        return str(value).strip()

    df["TIME"] = df["TIME"].apply(format_time)

    df["TIME"] = pd.to_datetime(
        df["TIME"],
        format="%H:%M",
        errors="coerce"
    )

    # Remove invalid rows
    df = df.dropna(
        subset=["TIME", "WATER LEVEL (m) CD"]
    )

    if df.empty:
        print(f"Skipping {sheet_name}: No valid data.")
        continue

    # Sort chronologically
    df = df.sort_values("TIME")

    # ======================================
    # 5. GENERATE LINE GRAPH
    # ======================================

    fig, ax = plt.subplots(figsize=(12, 5))

    ax.plot(
        df["TIME"],
        df["WATER LEVEL (m) CD"],
        color="royalblue",
        linewidth=1.8,
        label="Water Level"
    )

    ax.set_title(
        f"Water Level - {sheet_name}",
        fontsize=14,
        fontweight="bold"
    )

    ax.set_xlabel("Time (24-hour format)")
    ax.set_ylabel("Water Level (m CD)")

    # Time formatting
    ax.xaxis.set_major_locator(
        mdates.HourLocator(interval=2)
    )
    ax.xaxis.set_major_formatter(
        mdates.DateFormatter("%H:%M")
    )

    ax.set_xlim(
        df["TIME"].iloc[0],
        df["TIME"].iloc[-1]
    )

    # Graph styling
    ax.grid(True, linestyle="--", alpha=0.4)
    ax.legend()

    fig.autofmt_xdate(rotation=45)
    fig.tight_layout()

    # ======================================
    # 6. SAVE GRAPH
    # ======================================

    safe_name = re.sub(
        r'[<>:"/\\|?*]',
        "_",
        str(sheet_name)
    )

    output_file = output_folder / f"{safe_name}.png"

    fig.savefig(
        output_file,
        dpi=300,
        bbox_inches="tight"
    )

    plt.close(fig)

    print(f"Saved: {output_file.name}")

print("\nAll sheets processed.")