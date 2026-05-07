import os
from fpdf import FPDF
import pandas as pd
from .titles import _norm_category_from_presentations
from .preprocess import _canon_title

def clean_text(text):
    if not isinstance(text, str):
        text = str(text)
    # Replace common unicode characters that FPDF's default fonts don't like
    replacements = {
        "\u2018": "'",  # Left single quote
        "\u2019": "'",  # Right single quote
        "\u201c": '"',  # Left double quote
        "\u201d": '"',  # Right double quote
        "\u2013": "-",  # En dash
        "\u2014": "-",  # Em dash
        "\u2026": "...", # Ellipsis
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    # Encode to latin-1 and ignore errors as a last resort
    return text.encode("latin-1", "replace").decode("latin-1")

class PDF(FPDF):
    def header(self):
        pass

    def footer(self):
        self.set_y(-15)
        self.set_font("helvetica", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")

def generate_class_rosters(all_assignments_df, presentations_df, output_dir="output/rosters"):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    pres = presentations_df.copy()
    cat_col = "Presentation Category (choose the best fit)"
    title_col = 'Name of your presentation: "Creative Title: Descriptive Title"  (15 words max)'
    teacher_col = "All presentations will be paired with a teacher advisor. Is there a teacher already associated with your presentation, such as club advisor or class teacher? If yes, please write their last name below. "
    room_col = "Room #"

    pres["CatNorm"] = pres[cat_col].map(_norm_category_from_presentations)
    pres["TitleCanon"] = pres[title_col].map(_canon_title)
    
    info_map = {}
    for _, row in pres.iterrows():
        key = (row["CatNorm"], row["TitleCanon"])
        info_map[key] = {
            "teacher": str(row.get(teacher_col, "N/A")),
            "room": str(row.get(room_col, "N/A"))
        }

    grouped = all_assignments_df.groupby(["Category", "AssignedClass"])

    for (cat, title), group in grouped:
        details = info_map.get((cat, title), {"teacher": "N/A", "room": "N/A"})
        
        pdf = PDF()
        pdf.add_page()
        pdf.set_font("helvetica", "B", 16)
        pdf.cell(0, 10, clean_text(f"Class Roster: {title}"), ln=True, align="C")
        pdf.set_font("helvetica", "", 12)
        pdf.cell(0, 10, clean_text(f"Category: {cat}"), ln=True, align="C")
        pdf.cell(0, 10, clean_text(f"Teacher: {details['teacher']} | Room: {details['room']}"), ln=True, align="C")
        pdf.ln(10)

        pdf.set_font("helvetica", "B", 11)
        pdf.cell(80, 10, "Student Name", border=1)
        pdf.cell(40, 10, "Grade", border=1)
        pdf.cell(70, 10, "Email", border=1, ln=True)

        pdf.set_font("helvetica", "", 10)
        sorted_group = group.sort_values("Student")
        for _, s_row in sorted_group.iterrows():
            pdf.cell(80, 8, clean_text(s_row["Student"]), border=1)
            pdf.cell(40, 8, clean_text(s_row["GradeBand"]), border=1)
            pdf.cell(70, 8, clean_text(s_row["Email"]), border=1, ln=True)

        safe_title = "".join([c if c.isalnum() else "_" for c in title])
        filename = f"{cat}_{safe_title}.pdf"
        pdf.output(os.path.join(output_dir, filename))

def generate_student_schedules(all_assignments_df, presentations_df, output_dir="output/schedules"):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    pres = presentations_df.copy()
    cat_col = "Presentation Category (choose the best fit)"
    title_col = 'Name of your presentation: "Creative Title: Descriptive Title"  (15 words max)'
    teacher_col = "All presentations will be paired with a teacher advisor. Is there a teacher already associated with your presentation, such as club advisor or class teacher? If yes, please write their last name below. "
    room_col = "Room #"

    pres["CatNorm"] = pres[cat_col].map(_norm_category_from_presentations)
    pres["TitleCanon"] = pres[title_col].map(_canon_title)
    
    info_map = {}
    for _, row in pres.iterrows():
        key = (row["CatNorm"], row["TitleCanon"])
        info_map[key] = {
            "teacher": str(row.get(teacher_col, "N/A")),
            "room": str(row.get(room_col, "N/A"))
        }

    grouped = all_assignments_df.groupby("Email")

    for email, group in grouped:
        student_name = group["Student"].iloc[0]
        pdf = PDF()
        pdf.add_page()
        pdf.set_font("helvetica", "B", 16)
        pdf.cell(0, 10, clean_text(f"Student Schedule: {student_name}"), ln=True, align="C")
        pdf.set_font("helvetica", "", 12)
        pdf.cell(0, 10, clean_text(f"Email: {email}"), ln=True, align="C")
        pdf.ln(10)

        pdf.set_font("helvetica", "B", 11)
        pdf.cell(40, 10, "Block/Category", border=1)
        pdf.cell(80, 10, "Class Title", border=1)
        pdf.cell(40, 10, "Teacher", border=1)
        pdf.cell(30, 10, "Room", border=1, ln=True)

        pdf.set_font("helvetica", "", 10)
        sorted_group = group.sort_values("Category")
        for _, a_row in sorted_group.iterrows():
            cat = a_row["Category"]
            title = a_row["AssignedClass"]
            details = info_map.get((cat, title), {"teacher": "N/A", "room": "N/A"})
            
            h = 8
            pdf.cell(40, h, clean_text(cat), border=1)
            
            x = pdf.get_x()
            y = pdf.get_y()
            pdf.set_font("helvetica", "", 8 if len(title) > 40 else 10)
            pdf.multi_cell(80, h, clean_text(title), border=1)
            pdf.set_font("helvetica", "", 10)
            
            new_y = pdf.get_y()
            pdf.set_xy(x + 80, y)
            pdf.cell(40, new_y - y, clean_text(details["teacher"]), border=1)
            pdf.cell(30, new_y - y, clean_text(details["room"]), border=1, ln=True)

        filename = f"{email}.pdf"
        pdf.output(os.path.join(output_dir, filename))
