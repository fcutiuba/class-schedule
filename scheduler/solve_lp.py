import numpy as np
from scipy.optimize import linprog

def solve_assignment_lp(
    students, class_titles, mins, maxs,
    rank_cost={1:0.0, 2:2.0, 3:5.0, 4:9.0, 5:14.0},
    unlisted_cost=18.0, filler_cost=12.0,
    eps_by_grade={'Freshman':0.000, 'Sophomore':0.001, 'Junior':0.002, 'Senior':0.003}
):
    """
    Solve the assignment as a linear program with per-class min/max capacity.
    Returns (assigned_titles, class_counts).
    """
    n = len(students)
    m = len(class_titles)

    def edge_cost(i, j):
        s = students[i]
        title = class_titles[j]
        eps = eps_by_grade.get(s["grade"], 0.003)
        if s["is_filler"]:
            return filler_cost + eps
        try:
            r = s["choices"].index(title) + 1
            return rank_cost.get(r, unlisted_cost) + eps
        except ValueError:
            return unlisted_cost + eps

    C = np.fromfunction(np.vectorize(lambda i, j: edge_cost(int(i), int(j))), (n, m))
    c = C.reshape(n*m)

    # Equality
    A_eq = np.zeros((n, n*m))
    for i in range(n):
        A_eq[i, i*m:(i+1)*m] = 1.0
    b_eq = np.ones(n)

    # Upper bounds per class: sum_i x_{i,j} <= max_j
    A_ub = []
    b_ub = []
    for j in range(m):
        row = np.zeros(n*m); row[j::m] = 1.0
        A_ub.append(row); b_ub.append(maxs[j])

    # Lower bounds per class: sum_i x_{i,j} >= min_j -> -sum_i x_{i,j} <= -min_j
    for j in range(m):
        row = np.zeros(n*m); row[j::m] = -1.0
        A_ub.append(row); b_ub.append(-mins[j])

    A_ub = np.vstack(A_ub) if A_ub else None
    b_ub = np.array(b_ub) if b_ub else None

    bounds = [(0.0, 1.0)] * (n*m)

    res = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq,
                  bounds=bounds, method="highs")
    if res.status != 0:
        raise RuntimeError(f"LP failed: {res.message}")

    x = res.x.reshape(n, m)
    assign_j = x.argmax(axis=1)
    assigned_titles = [class_titles[j] for j in assign_j]
    class_counts = x.sum(axis=0).round().astype(int)
    return assigned_titles, class_counts
