import pandas as pd
from .io_utils import read_csv_robust
from .preprocess import _build_students_for_category
from .titles import (
    _build_canonical_titles_from_presentations,
    _apply_aliases_to_students,
    _map_student_choices_to_canonical,
)
from .solve_lp import solve_assignment_lp

def run_category_assignment(
    roster_csv, presenters_csv, signups_csv, presentations_csv,
    category_name, default_min_cap=9, default_max_cap=20,
    per_class_overrides=None, aliases=None
):
    roster_df     = read_csv_robust(roster_csv, "Roster")
    presenters_df = read_csv_robust(presenters_csv, "Presenters")
    prefs_df      = read_csv_robust(signups_csv, "Signups")
    pres_df       = read_csv_robust(presentations_csv, "Presentations")

    # Students + canonical titles
    students = _build_students_for_category(roster_df, presenters_df, prefs_df, category_name)
    class_titles = _build_canonical_titles_from_presentations(pres_df, category_name)

    # Aliases then canonical
    if aliases:
        students = _apply_aliases_to_students(students, aliases)
    students = _map_student_choices_to_canonical(students, class_titles)

    # Build min/max arrays honoring overrides
    mins, maxs = [], []
    for t in class_titles:
        mi = default_min_cap
        ma = default_max_cap
        if per_class_overrides and t in per_class_overrides:
            mi = int(per_class_overrides[t].get("min", mi))
            ma = int(per_class_overrides[t].get("max", ma))
        mins.append(mi); maxs.append(ma)

    assigned_titles, counts = solve_assignment_lp(students, class_titles, mins, maxs)

    def rank_of(s, title):
        try:
            return s["choices"].index(title) + 1
        except ValueError:
            return 6

    rows = [{
        "Email": s["email"],
        "Student": s["name"],
        "GradeBand": s["grade"],
        "IsFiller": s["is_filler"],
        "AssignedClass": title,
        "AssignedRank": rank_of(s, title)
    } for s, title in zip(students, assigned_titles)]
    assignments_df = pd.DataFrame(rows)

    roster_rows = []
    for j, t in enumerate(class_titles):
        mi, ma = mins[j], maxs[j]
        roster_rows.append({
            "Class": t, "AssignedCount": int(counts[j]),
            "MinCap": mi, "MaxCap": ma, "MeetsMin": int(counts[j]) >= mi
        })
    class_rosters_df = pd.DataFrame(roster_rows).sort_values("Class")

    rank_counts = assignments_df["AssignedRank"].value_counts().reindex([1,2,3,4,5,6], fill_value=0)
    diagnostics = {"rank_counts": rank_counts.to_dict()}

    return assignments_df, class_rosters_df, diagnostics
