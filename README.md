# Presentation Assignment System

This program assigns students to presentations (or classes) for a single scheduling block, such as the “Academic” block during a presentation day. The goal is to maximize how many students receive their top-ranked preferences while keeping every class within its minimum and maximum capacity limits.

---

## Overview

The system reads four input CSV files:

1. **All Students.csv**  
   The authoritative roster of students.  
   Columns: `Student name`, `Grade level`, `Advisor`, `Email`

2. **Presenter Names.csv**  
   A list of students who are presenting. These students are excluded from audience assignment.  
   Columns: `Name`, `Given Name`, `Family Name`, `E-mail 1 - Value`

3. **Audience Sign Up.csv**  
   Each student’s ranked preferences for which presentations they want to attend.  
   Columns include:  
   `Email Address`, and  
   `Which presentation is your first/second/… fifth choice for the <Category> block?`

4. **Presentations.csv**  
   The canonical list of valid presentations for the chosen category.  
   Columns include:  
   `Presentation Category (choose the best fit)` and  
   `Name of your presentation: "Creative Title: Descriptive Title" (15 words max)`

---

## What It Does

1. **Preprocessing**
   - Normalizes emails and grade levels.
   - Removes presenters from the student and signup lists.
   - Parses the five preference columns for the selected category (e.g., “Academic”).
   - Cleans and canonicalizes presentation titles (handles numbering, aliases, and case).
   - Identifies “filler” students who did not submit preferences, to fill leftover seats later.

2. **Assignment Optimization**
   - Uses **Linear Programming (LP)** via `scipy.optimize.linprog` to solve the assignment problem.
   - Each student can be assigned to exactly one class.
   - Each class must stay within its minimum (`min_cap`) and maximum (`max_cap`) capacities.
   - Preferences are modeled as costs:
     - Rank 1 → 0  
     - Rank 2 → 2  
     - Rank 3 → 5  
     - Rank 4 → 9  
     - Rank 5 → 14  
     - Off-list → 18  
   - Grade-based tie-breakers give preference to underclassmen.

3. **Outputs**
   - `assignments.csv` — One row per student with their assigned class and assigned rank.  
     Columns: `Email`, `Student`, `GradeBand`, `IsFiller`, `AssignedClass`, `AssignedRank`
   - `class_rosters.csv` — Each class’s assigned count, min/max caps, and whether it meets its minimum.  
     Columns: `Class`, `AssignedCount`, `MinCap`, `MaxCap`, `MeetsMin`

4. **Satisfaction Metrics**
   - After the solve, the program prints summary statistics:
     - Percentage of students receiving their top-1, top-2, and top-3 choices.
     - Mean assigned rank (1 = best, 6 = off-list).
     - **PSI (Preference Satisfaction Index)**:  
       Weighted average of satisfaction scores (1.0 = ideal, 0.0 = none).  
       Typically, PSI > 0.8 indicates very strong alignment between preferences and assignments.

---

## Example Output
=== Satisfaction ===  
Top-1: 0.584  (180/308)  
Top-2: 0.870  (268/308)  
Top-3: 0.909  (280/308)  
Mean rank: 1.82  (1 best, 6 = off-list)  
PSI (0–1): 0.855  


This means:
- 58% of students received their first choice.
- 87% received one of their top two choices.
- 90% received one of their top three choices.
- The average satisfaction is high, corresponding roughly to “most students got what they wanted.”

---

## Configuration

Most logic now lives in the `scheduler/` package.  

You can modify key parameters inside `scheduler/config.py`:

| Parameter | Description | Default |
|------------|-------------|----------|
| `CATEGORY_NAME` | Which presentation block to assign | `"Academic"` |
| `MIN_CAP` | Minimum number of students per class | `9` |
| `MAX_CAP` | Maximum number of students per class | `20` |
| `ALIASES` | Mapping of known title variants to canonical titles | *Defined at top of file* |

---

## Running the Program

From the project root, run:
```bash
python -m scheduler.cli
```
This will:

Load and preprocess the CSV files (`All students.csv`, `Presenter names.csv`, `Audience Sign Up.csv`, and `Presentations.csv`).

Solve the assignment problem using the linear programming solver (`scheduler/solve_lp.py`).

Compute satisfaction metrics and output CSV results to the project root.

```graphql
scheduler/
├── cli.py              # Entry point for running the program
├── config.py           # Configuration (min/max caps, category name, aliases)
├── io_utils.py         # Robust CSV reading and validation
├── preprocess.py       # Builds normalized student data and removes presenters
├── titles.py           # Handles canonical title extraction and aliasing
├── solve_lp.py         # Linear programming solver for optimal assignment
├── run_category.py     # Orchestrates full category-level assignment
└── metrics.py          # Computes satisfaction metrics (Top-1, PSI, etc.)
```

Output CSV files (e.g., `assignments.csv` and `class_rosters.csv`) will be written to the project root after execution.
