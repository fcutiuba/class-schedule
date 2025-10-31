import time

if __package__ in (None, ""):
    import os, sys
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from scheduler.config import ALIASES, DEFAULT_MIN_CAP, DEFAULT_MAX_CAP, DEFAULT_CATEGORY
    from scheduler.run_category import run_category_assignment
    from scheduler.metrics import compute_satisfaction
else:
    from .config import ALIASES, DEFAULT_MIN_CAP, DEFAULT_MAX_CAP, DEFAULT_CATEGORY
    from .run_category import run_category_assignment
    from .metrics import compute_satisfaction

def main():
    ROSTER_CSV        = "files/All students.csv"
    PRESENTERS_CSV    = "files/Presenter names.csv"
    SIGNUPS_CSV       = "files/Audience Sign Up.csv"
    PRESENTATIONS_CSV = "files/Presentations.csv"
    CATEGORY_NAME     = DEFAULT_CATEGORY
    MIN_CAP, MAX_CAP  = DEFAULT_MIN_CAP, DEFAULT_MAX_CAP

    t0 = time.time()
    assignments, class_rosters, diag = run_category_assignment(
        roster_csv=ROSTER_CSV,
        presenters_csv=PRESENTERS_CSV,
        signups_csv=SIGNUPS_CSV,
        presentations_csv=PRESENTATIONS_CSV,
        category_name=CATEGORY_NAME,
        default_min_cap=MIN_CAP,
        default_max_cap=MAX_CAP,
        per_class_overrides=None,
        aliases=ALIASES,
    )
    dt = time.time() - t0
    print(f"\nSolve time: {dt:.3f}s")

    _ = compute_satisfaction(assignments)
    print(class_rosters)

    assignments.to_csv("assignments.csv", index=False)
    class_rosters.to_csv("class_rosters.csv", index=False)

if __name__ == "__main__":
    main()
