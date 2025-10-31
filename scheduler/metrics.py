def compute_satisfaction(assignments_df):
    """
    Print and return satisfaction metrics:
      - Top-1 / Top-2 / Top-3 rates
      - Mean assigned rank (1..6, with 6 = off-list)
      - PSI (0–1): preference satisfaction index
    """
    total = len(assignments_df)
    vc = assignments_df["AssignedRank"].value_counts().reindex([1,2,3,4,5,6], fill_value=0)
    counts = {int(k): int(v) for k, v in vc.items()}
    top1 = counts[1] / total if total else 0.0
    top2 = (counts[1] + counts[2]) / total if total else 0.0
    top3 = (counts[1] + counts[2] + counts[3]) / total if total else 0.0
    mean_rank = (sum(k * v for k, v in counts.items()) / total) if total else 0.0

    psi_weights = {1:1.00, 2:0.85, 3:0.70, 4:0.50, 5:0.30, 6:0.00}
    psi = (sum(psi_weights[k] * v for k, v in counts.items()) / total) if total else 0.0

    print("\n=== Satisfaction ===")
    print(f"Top-1: {top1:.3f}  ({counts[1]}/{total})")
    print(f"Top-2: {top2:.3f}  ({counts[1] + counts[2]}/{total})")
    print(f"Top-3: {top3:.3f}  ({counts[1] + counts[2] + counts[3]}/{total})")
    print(f"Mean rank: {mean_rank:.2f}  (1 best, 6 = off-list)")
    print(f"PSI (0–1): {psi:.3f}")

    return {
        "top1": top1, "top2": top2, "top3": top3,
        "mean_rank": mean_rank, "psi": psi,
        "rank_counts": counts
    }
