import re
import pandas as pd

def _norm_email(s) -> str:
    return str(s).strip().lower() if pd.notna(s) else ""

def _grade_to_band(grade_val) -> str:
    if pd.isna(grade_val): 
        return "Senior"
    s = str(grade_val).strip().lower()
    if s in {"9", "9th", "freshman"}:  return "Freshman"
    if s in {"10", "10th", "sophomore"}: return "Sophomore"
    if s in {"11", "11th", "junior"}:  return "Junior"
    if s in {"12", "12th", "senior"}:  return "Senior"
    m = re.search(r'(\d+)', s)
    return _grade_to_band(m.group(1)) if m else "Senior"

def _strip_number_prefix(title):
    if pd.isna(title):
        return None
    t = str(title).strip()
    if t.upper() == "NONE" or t == "":
        return None
    m = re.match(r'^\s*\d+\s*[\.\)]\s*(.+)$', t)
    return m.group(1).strip() if m else t

def _canon_title(s):
    if s is None or pd.isna(s):
        return None
    s = str(s).strip()
    s = re.sub(r'^\s*\d+[\.\)]\s*', '', s)
    s = re.sub(r'\s+', ' ', s)
    return s

def _extract_category_choice_columns(prefs_df: pd.DataFrame, category_name: str):
    """
    Match headers like:
    'Which presentation is your first choice for the Academic block?'
    """
    cat = re.escape(category_name)
    pat = re.compile(
        rf"^Which presentation is your (first|second|third|fourth|fifth)\s+choice\s+for\s+the\s+{cat}\s+block\??\s*$",
        re.IGNORECASE
    )
    cols = [c for c in prefs_df.columns if pat.match(str(c))]
    order = {"first":0, "second":1, "third":2, "fourth":3, "fifth":4}
    cols = sorted(cols, key=lambda c: order[pat.match(str(c)).group(1).lower()] if pat.match(str(c)) else 99)
    if len(cols) != 5:
        raise ValueError(f"[Signups] Could not find exactly 5 choice columns for '{category_name}'. Found: {cols}")
    return cols

def _build_students_for_category(
    roster_df: pd.DataFrame, presenters_df: pd.DataFrame, prefs_df: pd.DataFrame, category_name: str
):
    """
    Returns a list of dicts:
    {
      id, email, name, grade, choices (list[str]), is_filler (bool)
    }
    """
    roster = roster_df.copy()
    if "Email" not in roster.columns:
        raise ValueError("[Roster] Missing 'Email' column.")
    roster["Email_norm"] = roster["Email"].map(_norm_email)

    if "E-mail 1 - Value" not in presenters_df.columns:
        raise ValueError("[Presenters] Missing 'E-mail 1 - Value' column.")
    presenters_emails = set(presenters_df["E-mail 1 - Value"].map(_norm_email))

    prefs = prefs_df.copy()
    if "Email Address" not in prefs.columns:
        raise ValueError("[Signups] Missing 'Email Address' column.")
    prefs["Email_norm"] = prefs["Email Address"].map(_norm_email)

    # Exclude presenters
    roster_nopresenters = roster[~roster["Email_norm"].isin(presenters_emails)].copy()
    prefs_nopresenters  = prefs[~prefs["Email_norm"].isin(presenters_emails)].copy()
    
    choice_cols = _extract_category_choice_columns(prefs_nopresenters, category_name)

    # Signed-up students
    need_cols_roster = [c for c in ["Email_norm", "Student name", "Grade level"] if c in roster_nopresenters.columns]
    signed = pd.merge(
        prefs_nopresenters[["Email_norm"] + choice_cols],
        roster_nopresenters[need_cols_roster],
        on="Email_norm", how="left"
    ).drop_duplicates("Email_norm")

    students = []

    # Students with preferences
    for _, row in signed.iterrows():
        choices_raw = [row[c] for c in choice_cols]
        choices = [_strip_number_prefix(x) for x in choices_raw]
        choices = [c for c in choices if c is not None]
        grade_band = _grade_to_band(row.get("Grade level"))
        students.append({
            "id": row["Email_norm"],
            "email": row["Email_norm"],
            "name": row.get("Student name", row["Email_norm"]),
            "grade": grade_band,
            "choices": choices,
            "is_filler": False
        })

    # Non-signups → fillers
    signup_emails = set(prefs_nopresenters["Email_norm"])
    nonsign = roster_nopresenters[~roster_nopresenters["Email_norm"].isin(signup_emails)].copy()
    for _, row in nonsign.iterrows():
        grade_band = _grade_to_band(row.get("Grade level"))
        students.append({
            "id": row["Email_norm"],
            "email": row["Email_norm"],
            "name": row.get("Student name", row["Email_norm"]),
            "grade": grade_band,
            "choices": [],
            "is_filler": True
        })

    return students