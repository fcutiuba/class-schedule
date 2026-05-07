import time
import argparse
import pandas as pd
import os

if __package__ in (None, ""):
    import os, sys
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from scheduler.config import ALIASES, DEFAULT_MIN_CAP, DEFAULT_MAX_CAP, DEFAULT_CATEGORY
    from scheduler.run_category import run_category_assignment
    from scheduler.metrics import compute_satisfaction
    from scheduler.titles import get_all_categories
    from scheduler.io_utils import read_csv_robust
    from scheduler.pdf_gen import generate_class_rosters, generate_student_schedules
else:
    from .config import ALIASES, DEFAULT_MIN_CAP, DEFAULT_MAX_CAP, DEFAULT_CATEGORY
    from .run_category import run_category_assignment
    from .metrics import compute_satisfaction
    from .titles import get_all_categories
    from .io_utils import read_csv_robust
    from .pdf_gen import generate_class_rosters, generate_student_schedules

def main():
    parser = argparse.ArgumentParser(description="Presentation Assignment System")
    parser.add_argument("--category", type=str, default=DEFAULT_CATEGORY, 
                        help="Specific category to run (default: %(default)s)")
    parser.add_argument("--all", action="store_true", 
                        help="Run for all categories found in Presentations.csv")
    parser.add_argument("--min-cap", type=int, default=DEFAULT_MIN_CAP, help="Minimum class capacity")
    parser.add_argument("--max-cap", type=int, default=DEFAULT_MAX_CAP, help="Maximum class capacity")
    parser.add_argument("--pdf", action="store_true", help="Generate printable PDF rosters and schedules")
    
    args = parser.parse_args()

    ROSTER_CSV        = "files/All students.csv"
    PRESENTERS_CSV    = "files/Presenter names.csv"
    SIGNUPS_CSV       = "files/Audience Sign Up.csv"
    PRESENTATIONS_CSV = "files/Presentations.csv"
    MIN_CAP, MAX_CAP  = args.min_cap, args.max_cap

    pres_df = read_csv_robust(PRESENTATIONS_CSV, "Presentations")
    if args.all:
        categories = get_all_categories(pres_df)
        print(f"Found categories: {categories}")
    else:
        categories = [args.category]

    all_assignments = []

    for category in categories:
        print(f"\n>>> PROCESSING CATEGORY: {category} <<<")
        t0 = time.time()
        try:
            assignments, class_rosters, diag = run_category_assignment(
                roster_csv=ROSTER_CSV,
                presenters_csv=PRESENTERS_CSV,
                signups_csv=SIGNUPS_CSV,
                presentations_csv=PRESENTATIONS_CSV,
                category_name=category,
                default_min_cap=MIN_CAP,
                default_max_cap=MAX_CAP,
                per_class_overrides=None,
                aliases=ALIASES,
            )
            assignments["Category"] = category
            all_assignments.append(assignments)
        except Exception as e:
            print(f"Error processing {category}: {e}")
            continue

        dt = time.time() - t0
        print(f"Solve time: {dt:.3f}s")

        _ = compute_satisfaction(assignments)
        print(class_rosters)

        # Update output filenames and ensure directories exist
        run_mode = "batch" if args.all else "single"
        base_dir = os.path.join("output", "csv", run_mode)
        os.makedirs(os.path.join(base_dir, "assignments"), exist_ok=True)
        os.makedirs(os.path.join(base_dir, "rosters"), exist_ok=True)
        
        assignments_path = os.path.join(base_dir, "assignments", f"assignments_{category.lower()}.csv")
        rosters_path = os.path.join(base_dir, "rosters", f"class_rosters_{category.lower()}.csv")
            
        assignments.to_csv(assignments_path, index=False)
        class_rosters.to_csv(rosters_path, index=False)
        print(f"Saved to {assignments_path} and {rosters_path}")

    if args.pdf and all_assignments:
        print("\n>>> GENERATING PDFs <<<")
        combined_df = pd.concat(all_assignments, ignore_index=True)
        
        print("Generating class rosters...")
        generate_class_rosters(combined_df, pres_df, output_dir="output/rosters")
        
        print("Generating student schedules...")
        generate_student_schedules(combined_df, pres_df, output_dir="output/schedules")
        print(f"PDFs generated in output/rosters and output/schedules")

if __name__ == "__main__":
    main()
