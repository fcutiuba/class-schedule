import time
import argparse
import pandas as pd
import os
import sys

if __package__ in (None, ""):
    import os, sys
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from scheduler.config import DEFAULT_MIN_CAP, DEFAULT_MAX_CAP, DEFAULT_CATEGORY
    from scheduler.engine import run_system
    from scheduler.validator import validate_csv_files
else:
    from .config import DEFAULT_MIN_CAP, DEFAULT_MAX_CAP, DEFAULT_CATEGORY
    from .engine import run_system
    from .validator import validate_csv_files

def main():
    parser = argparse.ArgumentParser(description="Presentation Assignment System")
    parser.add_argument("--category", type=str, default=DEFAULT_CATEGORY, 
                        help="Specific category to run (default: %(default)s)")
    parser.add_argument("--all", action="store_true", 
                        help="Run for all categories found in Presentations.csv")
    parser.add_argument("--min-cap", type=int, default=DEFAULT_MIN_CAP, help="Minimum class capacity")
    parser.add_argument("--max-cap", type=int, default=DEFAULT_MAX_CAP, help="Maximum class capacity")
    parser.add_argument("--pdf", action="store_true", help="Generate printable PDF rosters and schedules")
    parser.add_argument("--validate", action="store_true", help="Only validate CSV files without running assignment")
    parser.add_argument("--gui", action="store_true", help="Launch the graphical user interface")
    
    args = parser.parse_args()

    if args.gui:
        if __package__ in (None, ""):
            from scheduler.gui import AssignmentGUI
        else:
            from .gui import AssignmentGUI
        import tkinter as tk
        root = tk.Tk()
        app = AssignmentGUI(root)
        root.mainloop()
        return

    ROSTER_CSV        = "files/All students.csv"
    PRESENTERS_CSV    = "files/Presenter names.csv"
    SIGNUPS_CSV       = "files/Audience Sign Up.csv"
    PRESENTATIONS_CSV = "files/Presentations.csv"

    if args.validate:
        print(">>> VALIDATING INPUT FILES <<<")
        is_ok, messages = validate_csv_files(ROSTER_CSV, PRESENTERS_CSV, SIGNUPS_CSV, PRESENTATIONS_CSV)
        for msg in messages:
            print(msg)
        if not is_ok:
            sys.exit(1)
        return

    run_system(
        roster_csv=ROSTER_CSV,
        presenters_csv=PRESENTERS_CSV,
        signups_csv=SIGNUPS_CSV,
        presentations_csv=PRESENTATIONS_CSV,
        category=args.category,
        run_all=args.all,
        min_cap=args.min_cap,
        max_cap=args.max_cap,
        generate_pdfs=args.pdf
    )

if __name__ == "__main__":
    main()
