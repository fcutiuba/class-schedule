# Presentation Assignment System

This program assigns students to presentations (or classes) for multiple scheduling blocks (e.g., “Academic”, “Culture”, “Fest”). The goal is to maximize student satisfaction by honoring their ranked preferences while strictly respecting minimum and maximum capacity constraints for each presentation.

---

## Overview

The system processes data from four core CSV files located in the `files/` directory. For detailed information on the required format, column headers, and example data for these files, please refer to the **[CSV Input Structure Guide](CSV_STRUCTURE.md)**.

1. **All students.csv**: The authoritative roster of students.
2. **Presenter names.csv**: A list of students who are presenting and should be excluded from audience assignment.
3. **Audience Sign Up.csv**: Student preference rankings (1st through 5th choice) for various blocks.
4. **Presentations.csv**: The canonical list of available presentations, their categories, room numbers, and teacher advisors.

> **Note:** If these files are missing or incorrectly named, the system will fail validation.

---

## Key Features

### Advanced Optimization
- **Linear Programming (LP)**: Uses `scipy.optimize.linprog` to find the mathematically optimal assignment.
- **Non-Linear Costs**: Penalizes lower-ranked choices more heavily to prioritize high-satisfaction assignments.
- **Grade-Based Tie-Breakers**: Prioritizes younger students for high-demand classes when rankings are equal.
- **Filler Handling**: Automatically assigns students who did not sign up to remaining open spots.

### Data Robustness & Canonicalization
- **Flexible Headers**: Uses regex-based matching to find choice columns across different block names.
- **Title Normalization**: Automatically cleans presentation titles and maps aliases to canonical names.
- **Feasibility Validation**: Verifies that a valid assignment is possible before running the solver.

### Printable Outputs (PDF)
- **Class Rosters**: Generates individual PDFs for each presentation with teacher names, room numbers, and student lists.
- **Student Schedules**: Generates personalized PDF schedules for every student, listing all their assigned classes across blocks.

---

## Building and Running

### Prerequisites
Ensure you have Python 3.x installed along with the following libraries:
```bash
pip install pandas numpy scipy fpdf2
```

### Execution
Run the system from the project root.

**Launch the Graphical User Interface (Recommended):**
```bash
python -m scheduler.cli --gui
```

**CLI Usage:**
Run the system from the project root using `python -m scheduler.cli`.

**CLI Options:**
| Option | Description |
|--------|-------------|
| `--gui` | Launch the graphical user interface |
| `--category <name>` | Run for a specific block (default: Academic) |
| `--all` | Run for all categories found in the system |
| `--pdf` | Generate printable PDF rosters and schedules |
| `--validate` | Only validate CSV files without running assignment |
| `--min-cap <n>` | Set a custom minimum class capacity |
| `--max-cap <n>` | Set a custom maximum class capacity |

**Examples:**
```bash
# Run for all categories and generate everything
python -m scheduler.cli --all --pdf

# Run for a specific block with custom limits
python -m scheduler.cli --category Culture --min-cap 10 --max-cap 25

# Run in GUI mode
python -m scheduler.cli --gui
```

---

## Outputs

All generated files are organized within the `output/` directory:

- **Assignments & Rosters (CSV)**:
  - `output/csv/batch/assignments/`: Assignment CSVs from `--all` runs.
  - `output/csv/batch/rosters/`: Enrollment summary CSVs from `--all` runs.
  - `output/csv/single/assignments/`: Assignment CSV from standalone runs.
  - `output/csv/single/rosters/`: Enrollment summary CSV from standalone runs.
- **Printable Documents (PDF)**:
  - `output/rosters/`: Formatted PDF rosters for teachers.
  - `output/schedules/`: Personalized PDF schedules for students.

---

## Project Structure

```graphql
scheduler/
├── cli.py              # Main entry point with CLI argument parsing
├── gui.py              # Graphical user interface (Tkinter)
├── engine.py           # Core orchestration engine (shared by CLI & GUI)
├── config.py           # Global settings (caps, default category, aliases)
├── io_utils.py         # Robust CSV reading utilities
├── metrics.py          # Satisfaction metrics (Top-N, PSI)
├── pdf_gen.py          # Logic for generating printable PDFs
├── preprocess.py       # Data cleaning and filler student generation
├── run_category.py     # Orchestrates block-level assignments
├── solve_lp.py         # Linear programming optimization logic
└── titles.py           # Title canonicalization and category extraction
```

---

## Metrics and Validation

After execution, the program prints summary statistics:
- **Top-1/2/3 Rates**: Percentage of students who received their high-ranked choices.
- **Mean Rank**: The average rank assigned (1.0 is perfect).
- **PSI (Preference Satisfaction Index)**: A weighted score from 0.0 to 1.0 representing overall community satisfaction.
