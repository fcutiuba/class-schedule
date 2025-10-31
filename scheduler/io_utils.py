import pandas as pd

def read_csv_robust(path: str, name: str = "") -> pd.DataFrame:
    """Read CSV while skipping bad lines; print shape if name is provided."""
    df = pd.read_csv(path, engine="python", on_bad_lines="skip")
    if name:
        print(f"[OK] Loaded {name}: shape={df.shape}")
    return df
