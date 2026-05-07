import os
import pandas as pd
import re
from .io_utils import read_csv_robust
from .titles import get_all_categories
from .preprocess import _extract_category_choice_columns

def validate_csv_files(roster_path, presenters_path, signups_path, presentations_path):
    """
    Validates all input CSV files and returns a list of error/warning messages.
    Returns (is_ok, messages)
    """
    messages = []
    is_ok = True

    # 1. Check file existence
    paths = {
        "Roster": roster_path,
        "Presenters": presenters_path,
        "Signups": signups_path,
        "Presentations": presentations_path
    }
    for name, path in paths.items():
        if not os.path.exists(path):
            messages.append(f"[ERROR] {name} file missing at: {path}")
            is_ok = False
    
    if not is_ok:
        return False, messages

    # 2. Load dataframes
    try:
        roster_df = read_csv_robust(roster_path)
        pres_df = read_csv_robust(presenters_path)
        signups_df = read_csv_robust(signups_path)
        presentations_df = read_csv_robust(presentations_path)
    except Exception as e:
        messages.append(f"[ERROR] Failed to read one or more CSV files: {e}")
        return False, messages

    # 3. Validate Roster
    roster_cols = ["Email", "Student name", "Grade level"]
    for col in roster_cols:
        if col not in roster_df.columns:
            messages.append(f"[ERROR] Roster missing required column: '{col}'")
            is_ok = False

    # 4. Validate Presenters
    if "E-mail 1 - Value" not in pres_df.columns:
        messages.append(f"[ERROR] Presenters missing required column: 'E-mail 1 - Value'")
        is_ok = False

    # 5. Validate Presentations
    cat_col = "Presentation Category (choose the best fit)"
    title_col = 'Name of your presentation: "Creative Title: Descriptive Title"  (15 words max)'
    teacher_col = "All presentations will be paired with a teacher advisor. Is there a teacher already associated with your presentation, such as club advisor or class teacher? If yes, please write their last name below. "
    room_col = "Room #"

    pres_required = [cat_col, title_col, teacher_col, room_col]
    for col in pres_required:
        if col not in presentations_df.columns:
            messages.append(f"[ERROR] Presentations missing required column: '{col[:30]}...'")
            is_ok = False

    if not is_ok:
        return False, messages

    # 6. Validate Categories and Signups
    try:
        categories = get_all_categories(presentations_df)
        messages.append(f"[INFO] Found {len(categories)} categories: {', '.join(categories)}")
        
        for cat in categories:
            try:
                _extract_category_choice_columns(signups_df, cat)
            except ValueError:
                messages.append(f"[WARNING] Category '{cat}' found in Presentations but choice columns missing in Signups.")
    except Exception as e:
        messages.append(f"[ERROR] Error during category validation: {e}")
        is_ok = False

    # 7. Check email consistency (Warning only)
    if "Email" in roster_df.columns and "Email Address" in signups_df.columns:
        roster_emails = set(roster_df["Email"].dropna().str.strip().str.lower())
        signup_emails = set(signups_df["Email Address"].dropna().str.strip().str.lower())
        
        missing_in_roster = signup_emails - roster_emails
        if missing_in_roster:
            messages.append(f"[WARNING] {len(missing_in_roster)} emails in Signups are NOT in the Master Roster (they will be ignored).")
            if len(missing_in_roster) <= 5:
                messages.append(f"          Missing: {', '.join(list(missing_in_roster))}")

    if is_ok:
        messages.append("[SUCCESS] All core structures look good!")
    
    return is_ok, messages
