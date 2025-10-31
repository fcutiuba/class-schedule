import re
import pandas as pd
from .preprocess import _canon_title

def _norm_category_from_presentations(val) -> str:
    """
    Presentations CSV has values like '1 Academics\\n9:00-9:35'.
    Extract 'Academic' etc., singularized and title-cased.
    """
    if pd.isna(val): 
        return ""
    s = str(val)
    m = re.search(r'([A-Za-z]+)', s)
    if not m: 
        return ""
    word = m.group(1).lower()
    if word.endswith('s'):
        word = word[:-1]
    return word.capitalize()

def _build_canonical_titles_from_presentations(presentations_df: pd.DataFrame, category_name: str):
    cat_col   = "Presentation Category (choose the best fit)"
    title_col = 'Name of your presentation: "Creative Title: Descriptive Title"  (15 words max)'
    if cat_col not in presentations_df.columns or title_col not in presentations_df.columns:
        raise ValueError("[Presentations] Missing expected columns.")
    tmp = presentations_df.copy()
    tmp["CatNorm"] = tmp[cat_col].map(_norm_category_from_presentations)
    want = category_name.lower().rstrip('s')
    tmp = tmp[tmp["CatNorm"].str.lower() == want]
    tmp["TitleCanon"] = tmp[title_col].map(_canon_title)
    titles = sorted(t for t in tmp["TitleCanon"].dropna().unique())
    if not titles:
        raise ValueError(f"[Presentations] No titles found for '{category_name}'.")
    return titles

def _apply_aliases_to_students(students, aliases: dict):
    """Map student-entered titles via ALIASES, preserving order."""
    if not aliases:
        return students
    mapped = []
    for s in students:
        new_choices = []
        for ch in s["choices"]:
            ch_norm = _canon_title(ch)
            if ch in aliases:
                new_choices.append(_canon_title(aliases[ch]))
            elif ch_norm in aliases:
                new_choices.append(_canon_title(aliases[ch_norm]))
            else:
                new_choices.append(ch_norm)
        s2 = dict(s)
        s2["choices"] = [c for c in new_choices if c]
        mapped.append(s2)
    return mapped

def _map_student_choices_to_canonical(students, canonical_titles):
    """Keep only choices that exist in canonical set; preserve order."""
    canon_set = set(canonical_titles)
    mapped = []
    for s in students:
        new_choices = []
        for ch in s["choices"]:
            cch = _canon_title(ch)
            if cch in canon_set:
                new_choices.append(cch)
        s2 = dict(s)
        s2["choices"] = new_choices
        mapped.append(s2)
    return mapped
