import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
import threading
import os
import sys

# Ensure we can import from the scheduler package
if __package__ in (None, ""):
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from scheduler.engine import run_system
    from scheduler.config import DEFAULT_MIN_CAP, DEFAULT_MAX_CAP, DEFAULT_CATEGORY
    from scheduler.io_utils import read_csv_robust
    from scheduler.titles import get_all_categories
else:
    from .engine import run_system
    from .config import DEFAULT_MIN_CAP, DEFAULT_MAX_CAP, DEFAULT_CATEGORY
    from .io_utils import read_csv_robust
    from .titles import get_all_categories

class AssignmentGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Presentation Assignment System")
        self.root.geometry("800x700")
        
        self.setup_variables()
        self.create_widgets()
        
    def setup_variables(self):
        # File paths
        self.roster_path = tk.StringVar(value="files/All students.csv")
        self.presenters_path = tk.StringVar(value="files/Presenter names.csv")
        self.signups_path = tk.StringVar(value="files/Audience Sign Up.csv")
        self.presentations_path = tk.StringVar(value="files/Presentations.csv")
        
        # Options
        self.min_cap = tk.IntVar(value=DEFAULT_MIN_CAP)
        self.max_cap = tk.IntVar(value=DEFAULT_MAX_CAP)
        self.run_all = tk.BooleanVar(value=False)
        self.generate_pdfs = tk.BooleanVar(value=True)
        self.category = tk.StringVar(value=DEFAULT_CATEGORY)
        self.categories = [DEFAULT_CATEGORY]

    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # --- File Selection ---
        file_frame = ttk.LabelFrame(main_frame, text="Input Files", padding="10")
        file_frame.pack(fill=tk.X, pady=5)
        
        files = [
            ("Master Roster:", self.roster_path),
            ("Presenters:", self.presenters_path),
            ("Signups:", self.signups_path),
            ("Presentations:", self.presentations_path),
        ]
        
        for i, (label, var) in enumerate(files):
            ttk.Label(file_frame, text=label).grid(row=i, column=0, sticky=tk.W, pady=2)
            ttk.Entry(file_frame, textvariable=var, width=60).grid(row=i, column=1, padx=5)
            ttk.Button(file_frame, text="Browse", command=lambda v=var: self.browse_file(v)).grid(row=i, column=2)

        # --- Configuration ---
        config_frame = ttk.LabelFrame(main_frame, text="Configuration", padding="10")
        config_frame.pack(fill=tk.X, pady=5)
        
        # Caps
        ttk.Label(config_frame, text="Min Capacity:").grid(row=0, column=0, sticky=tk.W)
        ttk.Spinbox(config_frame, from_=1, to=100, textvariable=self.min_cap, width=5).grid(row=0, column=1, sticky=tk.W, padx=5)
        
        ttk.Label(config_frame, text="Max Capacity:").grid(row=0, column=2, sticky=tk.W, padx=(20, 0))
        ttk.Spinbox(config_frame, from_=1, to=100, textvariable=self.max_cap, width=5).grid(row=0, column=3, sticky=tk.W, padx=5)
        
        # Category
        ttk.Label(config_frame, text="Category:").grid(row=1, column=0, sticky=tk.W, pady=10)
        self.cat_combo = ttk.Combobox(config_frame, textvariable=self.category, values=self.categories)
        self.cat_combo.grid(row=1, column=1, columnspan=2, sticky=tk.W, padx=5)
        
        ttk.Button(config_frame, text="Refresh Categories", command=self.refresh_categories).grid(row=1, column=3, sticky=tk.W)
        
        # Flags
        ttk.Checkbutton(config_frame, text="Run All Categories", variable=self.run_all).grid(row=2, column=0, columnspan=2, sticky=tk.W)
        ttk.Checkbutton(config_frame, text="Generate PDFs", variable=self.generate_pdfs).grid(row=2, column=2, columnspan=2, sticky=tk.W)

        # --- Actions ---
        action_frame = ttk.Frame(main_frame, padding="10")
        action_frame.pack(fill=tk.X)
        
        self.run_btn = ttk.Button(action_frame, text="Run Assignment", command=self.start_run)
        self.run_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(action_frame, text="Clear Logs", command=self.clear_logs).pack(side=tk.LEFT, padx=5)

        # --- Logs ---
        log_frame = ttk.LabelFrame(main_frame, text="Execution Logs", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.log_area = scrolledtext.ScrolledText(log_frame, height=15, state=tk.DISABLED)
        self.log_area.pack(fill=tk.BOTH, expand=True)

    def browse_file(self, var):
        filename = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if filename:
            var.set(filename)
            if var == self.presentations_path:
                self.refresh_categories()

    def refresh_categories(self):
        path = self.presentations_path.get()
        if not os.path.exists(path):
            return
        try:
            df = read_csv_robust(path)
            cats = get_all_categories(df)
            self.categories = cats
            self.cat_combo['values'] = cats
            if cats and self.category.get() not in cats:
                self.category.set(cats[0])
            self.log(f"Updated categories: {', '.join(cats)}")
        except Exception as e:
            self.log(f"Failed to load categories: {e}")

    def log(self, message):
        self.log_area.config(state=tk.NORMAL)
        self.log_area.insert(tk.END, message + "\n")
        self.log_area.see(tk.END)
        self.log_area.config(state=tk.DISABLED)
        self.root.update_idletasks()

    def clear_logs(self):
        self.log_area.config(state=tk.NORMAL)
        self.log_area.delete(1.0, tk.END)
        self.log_area.config(state=tk.DISABLED)

    def start_run(self):
        self.run_btn.config(state=tk.DISABLED)
        threading.Thread(target=self.run_process, daemon=True).start()

    def run_process(self):
        try:
            success = run_system(
                roster_csv=self.roster_path.get(),
                presenters_csv=self.presenters_path.get(),
                signups_csv=self.signups_path.get(),
                presentations_csv=self.presentations_path.get(),
                category=self.category.get(),
                run_all=self.run_all.get(),
                min_cap=self.min_cap.get(),
                max_cap=self.max_cap.get(),
                generate_pdfs=self.generate_pdfs.get(),
                logger=self.log
            )
            if success:
                messagebox.showinfo("Success", "Assignment process completed successfully!")
            else:
                messagebox.showerror("Error", "Assignment process failed. Check logs for details.")
        except Exception as e:
            self.log(f"CRITICAL ERROR: {e}")
            messagebox.showerror("Critical Error", str(e))
        finally:
            self.run_btn.config(state=tk.NORMAL)

if __name__ == "__main__":
    root = tk.Tk()
    app = AssignmentGUI(root)
    root.mainloop()
