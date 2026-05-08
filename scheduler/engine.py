import time
import os
import pandas as pd
from .config import ALIASES
from .run_category import run_category_assignment
from .metrics import compute_satisfaction
from .titles import get_all_categories
from .io_utils import read_csv_robust
from .pdf_gen import generate_class_rosters, generate_student_schedules
from .validator import validate_csv_files

def run_system(
    roster_csv, 
    presenters_csv, 
    signups_csv, 
    presentations_csv, 
    category=None, 
    run_all=False, 
    min_cap=12, 
    max_cap=20, 
    generate_pdfs=False,
    output_base_dir="output",
    logger=print
):
    """
    Orchestrates the entire assignment process.
    logger: a function that takes a string (e.g., print or a GUI log function).
    """
    # 1. Validation
    logger(">>> VALIDATING INPUT FILES <<<")
    is_ok, messages = validate_csv_files(roster_csv, presenters_csv, signups_csv, presentations_csv)
    for msg in messages:
        logger(msg)
    
    if not is_ok:
        logger("\n[CRITICAL] Validation failed. Please fix the errors above.")
        return False

    # 2. Loading and Processing
    pres_df = read_csv_robust(presentations_csv, "Presentations")
    if run_all:
        categories = get_all_categories(pres_df)
    else:
        categories = [category] if category else []

    if not categories:
        logger("[ERROR] No categories specified to run.")
        return False

    all_assignments = []

    for cat in categories:
        logger(f"\n>>> PROCESSING CATEGORY: {cat} <<<")
        t0 = time.time()
        try:
            assignments, class_rosters, diag = run_category_assignment(
                roster_csv=roster_csv,
                presenters_csv=presenters_csv,
                signups_csv=signups_csv,
                presentations_csv=presentations_csv,
                category_name=cat,
                default_min_cap=min_cap,
                default_max_cap=max_cap,
                per_class_overrides=None,
                aliases=ALIASES,
            )
            assignments["Category"] = cat
            all_assignments.append(assignments)
        except Exception as e:
            logger(f"Error processing {cat}: {e}")
            continue

        dt = time.time() - t0
        logger(f"Solve time: {dt:.3f}s")

        stats = compute_satisfaction(assignments)
        logger(f"PSI: {stats['psi']:.3f}")
        logger(f"Mean Rank: {stats['mean_rank']:.2f}")

        # Update output filenames and ensure directories exist
        run_mode = "batch" if run_all else "single"
        base_dir = os.path.join(output_base_dir, "csv", run_mode)
        os.makedirs(os.path.join(base_dir, "assignments"), exist_ok=True)
        os.makedirs(os.path.join(base_dir, "rosters"), exist_ok=True)
        
        assignments_path = os.path.join(base_dir, "assignments", f"assignments_{cat.lower()}.csv")
        rosters_path = os.path.join(base_dir, "rosters", f"class_rosters_{cat.lower()}.csv")
            
        assignments.to_csv(assignments_path, index=False)
        class_rosters.to_csv(rosters_path, index=False)
        logger(f"Saved to {assignments_path} and {rosters_path}")

    if generate_pdfs and all_assignments:
        logger("\n>>> GENERATING PDFs <<<")
        combined_df = pd.concat(all_assignments, ignore_index=True)
        
        logger("Generating class rosters...")
        generate_class_rosters(combined_df, pres_df, output_dir=os.path.join(output_base_dir, "rosters"))
        
        logger("Generating student schedules...")
        generate_student_schedules(combined_df, pres_df, output_dir=os.path.join(output_base_dir, "schedules"))
        logger(f"PDFs generated in {output_base_dir}/rosters and {output_base_dir}/schedules")
    
    logger("\n>>> PROCESS COMPLETE <<<")
    return True
