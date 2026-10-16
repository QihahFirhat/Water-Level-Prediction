# Water Level Analysis and Reconstruction

A Python project for visualizing historical water-level measurements and estimating missing **10-minute readings** in newer datasets recorded at **hourly intervals**.

The project uses historical water-level data to study changes between hourly observations. It supports exploratory analysis and reconstruction, but **estimated values are not measured values** and should not be treated as ground truth.

## Repository structure

```text
.
├── graphs/                      # Graphs from historical data analysis
├── water_level_outputf3/       # Reconstructed data and related outputs
├── analyze_water_level.py      # Plots historical water levels by sheet/date
├── reconstruct_water_level.py  # Estimates 10-minute readings from hourly data
├── water_level.xlsx            # Historical dataset (typically every 10 minutes)
├── water_level_Sept.xlsx       # New dataset (typically every hour)
└── README.md
```

## What the scripts do

### `analyze_water_level.py`
- Reads the sheets in the historical Excel workbook.
- Plots water level against time for each sheet.
- Labels graphs using the sheet names.
- Saves plots to the `graphs/` folder.

### `reconstruct_water_level.py`
- Uses historical 10-minute observations to learn or evaluate patterns between hourly measurements.
- Processes new hourly observations and estimates intermediate 10-minute water levels.
- Preserves original hourly observations; intermediate readings are **estimates**.
- Exports reconstructed readings as CSV and XLSX files, with graphs embedded in the Excel output if supported by the script version.
- Stores the generated results in `water_level_outputf3/` when that output path is configured in the script.

The exact model, evaluation procedure, output filenames, and workbook layout depend on the implementation in `reconstruct_water_level.py`. Check the script's configuration and terminal messages for the settings actually used.

## Techniques used

This project combines **time-series data preprocessing, data visualization, interpolation, and supervised machine learning**.

| Technique | Where it is used | Purpose |
| --- | --- | --- |
| **Time-series preprocessing** (pandas) | Both scripts | Parses 12-hour/24-hour times, converts water levels to numeric values, sorts readings chronologically, and handles invalid rows. |
| **Exploratory data analysis (EDA) and line charts** (Matplotlib / Excel charts) | Historical analysis and reconstruction | Visualizes daily changes in water level and compares reconstructed curves with actual hourly readings. |
| **Linear interpolation** | Reconstruction | Establishes a baseline estimate at 10, 20, 30, 40, and 50 minutes between two observed hourly values. |
| **Random Forest Regression** (scikit-learn) | Reconstruction, when enabled and validated | Learns corrections to the linear-interpolation estimate from historical 10-minute data. It uses the two bounding hourly levels, their difference, the within-hour position, and time-of-day features. |
| **Cyclical time-of-day encoding** (sine/cosine) | Random Forest features | Represents the repeating 24-hour clock without an artificial discontinuity between late night and midnight. |
| **Historical holdout validation** | Model evaluation | Simulates hourly-only measurements from historical 10-minute records and tests estimates against the withheld intermediate measurements. Days are separated between training and validation to reduce data leakage. |
| **Mean Absolute Error (MAE)** | Model evaluation | Measures the average absolute difference between estimated and actual readings, in metres. |
| **Hybrid model selection** | Reconstruction | Uses the learned Random Forest correction only when validation demonstrates sufficient improvement over linear interpolation; otherwise uses the simpler interpolation baseline. |

### Reconstruction method

For two consecutive measured hourly levels, the starting estimate at a fraction `f` of the hour is:

```text
Linear estimate = starting level + f × (ending level − starting level)
```

If the learned correction model performs better in validation:

```text
Reconstructed level = linear estimate + predicted Random Forest correction
```

The **original hourly measurements remain unchanged**. Only the five intermediate 10-minute values within an observed, consecutive one-hour interval are estimated. This approach does **not** recover unobserved rapid fluctuations with certainty.

> **Model verification:** The description above reflects the reconstruction approach developed for this project. Check the committed `reconstruct_water_level.py` for the final hyperparameters, validation split, model-selection threshold, and output settings, as these may differ between versions.

## Input data format

Each Excel worksheet should represent **one date**. Worksheets can have different date-based names. Both workbooks should include these column headers:

| TIME | WATER LEVEL (m) CD |
| --- | ---: |
| 00:00 | 0.60 |
| 00:10 | 0.62 |
| 00:20 | 0.64 |

**Historical file (`water_level.xlsx`):** ideally contains measurements every **10 minutes**, with time in 24-hour format (e.g. `13:10`).

**New file (`water_level_Sept.xlsx`):** contains measurements every **hour**, with time possibly formatted as 12-hour AM/PM (e.g. `12:00:00 AM`, `01:00:00 PM`).

Requirements:
- Use an Excel workbook (`.xlsx`), **not CSV**, if the dataset contains multiple worksheets. CSV files do not support sheets.
- Keep the column headers consistent: `TIME` and `WATER LEVEL (m) CD`.
- Use valid numeric values in the water-level column (units: metres relative to Chart Datum, **m CD**).
- Avoid duplicate times within the same day.
- Keep dates separate by worksheet. Check how missing observations and midnight boundaries are handled by the scripts.

## Setup (VS Code)

1. Install **Python 3** and open this repository folder in VS Code.
2. Open **Terminal → New Terminal**.
3. Install the required packages:

```bash
python -m pip install pandas numpy matplotlib scikit-learn openpyxl xlsxwriter
```

> On some systems, use `py -m pip` instead of `python -m pip`.

## How to run

**1. Visualize the historical readings**

```bash
python analyze_water_level.py
```

Check the generated graphs in `graphs/`.

**2. Reconstruct 10-minute readings for the new dates**

```bash
python reconstruct_water_level.py
```

Check the files in `water_level_outputf3/` (or the output folder configured in the script). Open an XLSX result in Excel to inspect its data and embedded chart, where applicable.

## Using your own data

**Both example datasets can be replaced with your own Excel files.** They are not required to have the names shown in this repository.

1. Prepare an **old/historical workbook** with preferably complete 10-minute readings across multiple days.
2. Prepare a **new workbook** with hourly readings for the dates you want to reconstruct.
3. Keep the required column headers and consistent units.
4. Change the input filenames or file paths in the Python scripts to match your files. Also update the output directory if desired.
5. Run the analysis script, followed by the reconstruction script.

If your files have different column names, change the column references in the code or rename the columns in Excel. If the time format or sampling frequency differs, review the time-parsing and interval settings before running.

## Important limitations

- **Predictions are estimates, not sensor readings.** Do not use reconstructed values as verified measurements for safety-critical, regulatory, or engineering decisions without independent validation.
- The model cannot reliably recover sudden water-level fluctuations that occurred between hourly measurements without other supporting data.
- Accuracy depends on the historical dataset's quality and how representative it is of the new conditions.
- Compare model predictions against held-out historical 10-minute readings (for example, using **MAE** in metres), and compare them against simple interpolation before trusting the model.
- Original hourly readings should remain unchanged; flag estimated observations separately wherever possible.
- Do not extrapolate beyond the first and last actual hourly measurement unless a separate, justified method is used.
- Output folders contain generated files and may be safely regenerated if the underlying scripts and input files remain available.

## Notes on sharing the repository

The included Excel workbooks are **sample/project datasets and can be changed**. Before publishing them, confirm you have permission to share the measurements and remove any confidential site or station information. Document the data source, measurement location, datum definition, acquisition method, date range, and any known sensor quality issues when that information is available.

## Technology

Python · pandas · NumPy · Matplotlib · scikit-learn · openpyxl · XlsxWriter
