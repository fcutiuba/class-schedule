import os
import sys
import tempfile
import zipfile
import io
import re
import base64
import pandas as pd
import streamlit as st

# Ensure scheduler package can be imported
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scheduler.config import DEFAULT_MIN_CAP, DEFAULT_MAX_CAP, DEFAULT_CATEGORY
from scheduler.engine import run_system
from scheduler.validator import validate_csv_files
from scheduler.titles import get_all_categories
from scheduler.io_utils import read_csv_robust


def get_default_sample_paths():
    """Return default file paths from files/ directory if they exist."""
    base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "files")

    def resolve(candidates):
        for name in candidates:
            p = os.path.join(base, name)
            if os.path.exists(p):
                return p
        return None

    return {
        "roster": resolve(["All students.csv", "All_students.csv"]),
        "presenters": resolve(["Presenter names.csv", "Presenter_names.csv"]),
        "signups": resolve(["Audience Sign Up.csv", "Audience_Sign_Up.csv"]),
        "presentations": resolve(["Presentations.csv"]),
    }


def save_uploaded_file(uploaded_file, target_dir):
    """Save an UploadedFile to target_dir and return the absolute path."""
    dest_path = os.path.join(target_dir, uploaded_file.name)
    with open(dest_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return dest_path


def create_zip_archive(file_list):
    """Create a zip archive in-memory from a list of (disk_path, archive_name) tuples."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for disk_path, arc_name in file_list:
            if os.path.exists(disk_path):
                zf.write(disk_path, arc_name)
    buf.seek(0)
    return buf.getvalue()


def render_pdf_preview(pdf_path, height=600):
    """Embed and display a PDF using Mozilla PDF.js canvas rendering to prevent browser data-URI blocking."""
    try:
        with open(pdf_path, "rb") as f:
            base64_pdf = base64.b64encode(f.read()).decode("utf-8")
        
        pdfjs_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
          <script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js"></script>
          <style>
            body {{
              margin: 0;
              padding: 10px;
              background-color: #f8f9fa;
              display: flex;
              flex-direction: column;
              align-items: center;
              font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            }}
            #pdf-container {{
              display: flex;
              flex-direction: column;
              align-items: center;
              width: 100%;
            }}
            canvas {{
              margin-bottom: 12px;
              box-shadow: 0 1px 4px rgba(0,0,0,0.15);
              max-width: 98%;
              height: auto !important;
              background: white;
              border: 1px solid #ddd;
              border-radius: 4px;
            }}
            .status-text {{
              color: #666;
              font-size: 13px;
              margin-top: 15px;
            }}
          </style>
        </head>
        <body>
          <div id="pdf-container"><div class="status-text">Rendering document...</div></div>
          <script>
            try {{
              const rawData = atob("{base64_pdf}");
              const uint8Array = new Uint8Array(rawData.length);
              for (let i = 0; i < rawData.length; i++) {{
                uint8Array[i] = rawData.charCodeAt(i);
              }}
              pdfjsLib.GlobalWorkerOptions.workerSrc = "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js";
              const loadingTask = pdfjsLib.getDocument({{data: uint8Array}});
              loadingTask.promise.then(function(pdf) {{
                const container = document.getElementById("pdf-container");
                container.innerHTML = "";
                for (let pageNum = 1; pageNum <= pdf.numPages; pageNum++) {{
                  pdf.getPage(pageNum).then(function(page) {{
                    const viewport = page.getViewport({{scale: 1.3}});
                    const canvas = document.createElement("canvas");
                    const context = canvas.getContext("2d");
                    canvas.height = viewport.height;
                    canvas.width = viewport.width;
                    container.appendChild(canvas);
                    page.render({{canvasContext: context, viewport: viewport}});
                  }});
                }}
              }}).catch(function(err) {{
                document.getElementById("pdf-container").innerHTML = "<p style='color:#c00;'>Unable to render preview: " + err.message + "</p>";
              }});
            }} catch(e) {{
              document.getElementById("pdf-container").innerHTML = "<p style='color:#c00;'>Initialization error: " + e.message + "</p>";
            }}
          </script>
        </body>
        </html>
        """
        import streamlit.components.v1 as components
        components.html(pdfjs_html, height=height, scrolling=True)
    except Exception as e:
        st.warning(f"Could not preview PDF: {e}")


def find_student_schedule(email, assignment_dfs):
    """Find and return assigned classes for a specific student email."""
    clean_email = email.lower().strip()
    rows = []
    for df in assignment_dfs:
        if "Email" in df.columns:
            matched = df[df["Email"].astype(str).str.lower().str.strip() == clean_email]
            if not matched.empty:
                rows.append(matched)
    if rows:
        combined = pd.concat(rows, ignore_index=True)
        cols = [c for c in ["Category", "AssignedClass", "AssignedRank"] if c in combined.columns]
        return combined[cols].sort_values("Category" if "Category" in combined.columns else cols[0])
    return None


def find_class_students(target_filename, assignment_dfs):
    """Find and return students assigned to the presentation corresponding to target_filename."""
    clean_target = "".join(c for c in target_filename.lower().replace(".pdf", "") if c.isalnum())
    for df in assignment_dfs:
        if "AssignedClass" in df.columns:
            for cname in df["AssignedClass"].dropna().unique():
                cat = str(df.loc[df["AssignedClass"] == cname, "Category"].iloc[0]) if "Category" in df.columns else ""
                clean_full = "".join(c for c in f"{cat}_{cname}".lower() if c.isalnum())
                clean_cname = "".join(c for c in str(cname).lower() if c.isalnum())
                if clean_full == clean_target or clean_target.endswith(clean_cname):
                    matched = df[df["AssignedClass"] == cname].copy()
                    cols = [c for c in ["Student", "Email", "GradeBand", "AssignedRank", "IsFiller"] if c in matched.columns]
                    matched = matched[cols].sort_values("Student" if "Student" in matched.columns else cols[0])
                    return matched
    return None


def clear_output_directory(output_base="output"):
    """Remove all generated files and subdirectories in the output directory."""
    if not os.path.exists(output_base):
        return
    for root, dirs, files in os.walk(output_base, topdown=False):
        for f in files:
            try:
                os.remove(os.path.join(root, f))
            except OSError:
                pass
        for d in dirs:
            try:
                os.rmdir(os.path.join(root, d))
            except OSError:
                pass


def main():
    st.set_page_config(
        page_title="Presentation Assignment System",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Initialize session state (clear outputs on fresh startup)
    if "session_initialized" not in st.session_state:
        st.session_state.session_initialized = True
        st.session_state.use_sample_csvs = True
        clear_output_directory("output")

    if "logs" not in st.session_state:
        st.session_state.logs = []
    if "last_run_success" not in st.session_state:
        st.session_state.last_run_success = None
    if "feasibility_errors" not in st.session_state:
        st.session_state.feasibility_errors = []

    st.title("Presentation Assignment System")
    st.caption(
        "Assign students to presentations across scheduling blocks to maximize ranked preference satisfaction "
        "subject to capacity constraints."
    )

    sample_paths = get_default_sample_paths()
    has_sample_files = all(sample_paths.values())

    # --- Sidebar: Configuration & Controls ---
    with st.sidebar:
        st.header("Configuration")

        if has_sample_files:
            st.checkbox(
                "Use sample CSVs (files/)",
                value=st.session_state.get("use_sample_csvs", True),
                key="sidebar_use_sample",
                on_change=lambda: st.session_state.update(use_sample_csvs=st.session_state.sidebar_use_sample),
                help="Loads sample data included in the repository.",
            )

        st.subheader("Capacity Constraints")
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            min_cap = st.number_input(
                "Min Capacity",
                min_value=1,
                max_value=100,
                value=DEFAULT_MIN_CAP,
                step=1,
                help="Minimum number of students per class.",
            )
        with col_c2:
            max_cap = st.number_input(
                "Max Capacity",
                min_value=1,
                max_value=100,
                value=DEFAULT_MAX_CAP,
                step=1,
                help="Maximum number of students per class.",
            )

        st.subheader("Execution Options")
        run_all = st.checkbox(
            "Run all categories",
            value=True,
            help="Schedule all categories found in the Presentations file.",
        )
        generate_pdfs = st.checkbox(
            "Generate PDFs",
            value=True,
            help="Generate printable PDF class rosters and student schedules.",
        )
        clear_on_startup = st.checkbox(
            "Clear outputs on startup",
            value=True,
            help="Automatically clean previous output files when launching a fresh session.",
        )

    # --- Main Area: File Inputs ---
    st.subheader("Input Files")
    use_sample = False
    if has_sample_files:
        use_sample = st.checkbox(
            "Use sample CSVs (files/)",
            value=st.session_state.get("use_sample_csvs", True),
            key="main_use_sample",
            on_change=lambda: st.session_state.update(use_sample_csvs=st.session_state.main_use_sample),
            help="Automatically loads sample data included in the repository without manual upload.",
        )
    if use_sample:
        st.info("Using sample CSVs from the files/ directory. Uncheck the option above to upload custom CSVs.")

    col1, col2 = st.columns(2)
    with col1:
        roster_file = st.file_uploader(
            "Master Roster (All students.csv)",
            type=["csv"],
            key="roster_upload",
            disabled=use_sample,
        )
        presenters_file = st.file_uploader(
            "Presenters (Presenter names.csv)",
            type=["csv"],
            key="presenters_upload",
            disabled=use_sample,
        )

    with col2:
        signups_file = st.file_uploader(
            "Signups (Audience Sign Up.csv)",
            type=["csv"],
            key="signups_upload",
            disabled=use_sample,
        )
        presentations_file = st.file_uploader(
            "Presentations (Presentations.csv)",
            type=["csv"],
            key="presentations_upload",
            disabled=use_sample,
        )

    # Resolve active file paths
    temp_dir = tempfile.mkdtemp(prefix="scheduler_st_")

    active_paths = {}
    if use_sample:
        active_paths = sample_paths.copy()
    else:
        if roster_file is not None:
            active_paths["roster"] = save_uploaded_file(roster_file, temp_dir)
        if presenters_file is not None:
            active_paths["presenters"] = save_uploaded_file(presenters_file, temp_dir)
        if signups_file is not None:
            active_paths["signups"] = save_uploaded_file(signups_file, temp_dir)
        if presentations_file is not None:
            active_paths["presentations"] = save_uploaded_file(presentations_file, temp_dir)

    all_files_ready = (
        "roster" in active_paths
        and "presenters" in active_paths
        and "signups" in active_paths
        and "presentations" in active_paths
    )

    # Dynamic Category Selector
    categories = [DEFAULT_CATEGORY]
    if "presentations" in active_paths and active_paths["presentations"]:
        try:
            pres_df = read_csv_robust(active_paths["presentations"])
            loaded_cats = get_all_categories(pres_df)
            if loaded_cats:
                categories = loaded_cats
        except Exception:
            pass

    with st.sidebar:
        default_index = categories.index(DEFAULT_CATEGORY) if DEFAULT_CATEGORY in categories else 0
        selected_category = st.selectbox(
            "Category",
            options=categories,
            index=default_index,
            disabled=run_all,
            help="Block to schedule. Disabled when 'Run all categories' is selected.",
        )

    # --- Action Buttons ---
    st.write("---")
    col_act1, col_act2, col_act3, col_act4 = st.columns([1.5, 1.5, 1.5, 3.5])
    with col_act1:
        validate_btn = st.button(
            "Validate Only",
            use_container_width=True,
            help="Check file schemas, required columns, and email consistency before solving.",
        )
    with col_act2:
        run_btn = st.button(
            "Run Assignment",
            type="primary",
            use_container_width=True,
            help="Solve linear program and generate output files.",
        )
    with col_act3:
        if st.button("Clear Outputs", use_container_width=True, help="Delete all generated output files from disk"):
            clear_output_directory("output")
            st.session_state.last_run_success = None
            st.rerun()
    with col_act4:
        if st.button("Clear Logs", help="Reset execution logs"):
            st.session_state.logs = []
            st.session_state.last_run_success = None
            st.session_state.feasibility_errors = []
            st.rerun()

    # --- Validation Action ---
    if validate_btn:
        if not all_files_ready:
            missing = [k for k in ["roster", "presenters", "signups", "presentations"] if k not in active_paths]
            st.error(f"Missing required CSV files: {', '.join(missing)}.")
        else:
            st.subheader("Validation Report")
            with st.spinner("Validating CSV files..."):
                is_ok, messages = validate_csv_files(
                    active_paths["roster"],
                    active_paths["presenters"],
                    active_paths["signups"],
                    active_paths["presentations"],
                )

            if is_ok:
                st.success("All core structures and files look good.")
            else:
                st.error("Validation failed. Please fix the errors below.")

            for msg in messages:
                if msg.startswith("[ERROR]"):
                    st.error(msg)
                elif msg.startswith("[WARNING]"):
                    st.warning(msg)
                elif msg.startswith("[SUCCESS]"):
                    st.success(msg)
                else:
                    st.info(msg)

    # --- Run Assignment Action ---
    if run_btn:
        if not all_files_ready:
            missing = [k for k in ["roster", "presenters", "signups", "presentations"] if k not in active_paths]
            st.error(f"Cannot run assignment: missing required CSV files ({', '.join(missing)}).")
        else:
            st.session_state.logs = []
            st.session_state.feasibility_errors = []
            st.session_state.last_run_success = None

            log_container = st.empty()
            feasibility_alerts = []

            def log_callback(msg):
                st.session_state.logs.append(msg)
                log_container.code("\n".join(st.session_state.logs), language="text")
                if "Infeasible:" in msg:
                    m = re.search(r"Infeasible:.*", msg)
                    err_txt = m.group(0) if m else msg
                    if err_txt not in feasibility_alerts:
                        feasibility_alerts.append(err_txt)

            status_placeholder = st.status("Solving assignment...", expanded=True)
            success = False
            try:
                with status_placeholder:
                    st.write("Initializing orchestration engine...")
                    success = run_system(
                        roster_csv=active_paths["roster"],
                        presenters_csv=active_paths["presenters"],
                        signups_csv=active_paths["signups"],
                        presentations_csv=active_paths["presentations"],
                        category=selected_category,
                        run_all=run_all,
                        min_cap=int(min_cap),
                        max_cap=int(max_cap),
                        generate_pdfs=generate_pdfs,
                        output_base_dir="output",
                        logger=log_callback,
                    )
                    st.session_state.last_run_success = success
                    st.session_state.feasibility_errors = feasibility_alerts

                    if success:
                        status_placeholder.update(label="Assignment completed successfully.", state="complete", expanded=False)
                        st.success("Assignment process completed successfully.")
                    else:
                        status_placeholder.update(label="Assignment process encountered errors.", state="error", expanded=True)
                        st.error("Assignment process failed. Review logs below for details.")

            except ValueError as ve:
                st.session_state.last_run_success = False
                status_placeholder.update(label="Feasibility Constraint Error", state="error", expanded=True)
                st.error(f"Feasibility Error: {ve}")
            except Exception as e:
                st.session_state.last_run_success = False
                status_placeholder.update(label="Execution Failed", state="error", expanded=True)
                st.error(f"Critical Error: {e}")

            for fe in feasibility_alerts:
                st.error(f"Constraint Infeasible: {fe}")

    # --- Execution Logs ---
    if st.session_state.logs:
        with st.expander("Execution Logs", expanded=True):
            st.code("\n".join(st.session_state.logs), language="text")

    # --- Generated Outputs Section ---
    st.write("---")
    st.subheader("Generated Outputs")

    output_base = "output"
    csv_files = []
    roster_pdfs = []
    sched_pdfs = []

    # 1. Collect CSVs
    csv_dir = os.path.join(output_base, "csv")
    if os.path.exists(csv_dir):
        for root_path, _, filenames in sorted(os.walk(csv_dir)):
            for fname in sorted(filenames):
                if fname.endswith(".csv"):
                    full_p = os.path.join(root_path, fname)
                    rel_p = os.path.relpath(full_p, output_base)
                    file_type = "Assignment" if "assignments" in rel_p else "Roster"
                    csv_files.append({
                        "filename": fname,
                        "relative_path": rel_p,
                        "full_path": full_p,
                        "type": file_type,
                        "size_bytes": os.path.getsize(full_p),
                    })

    # 2. Collect PDF Rosters
    rosters_dir = os.path.join(output_base, "rosters")
    if os.path.exists(rosters_dir):
        for fname in sorted(os.listdir(rosters_dir)):
            if fname.endswith(".pdf"):
                full_p = os.path.join(rosters_dir, fname)
                rel_p = os.path.relpath(full_p, output_base)
                roster_pdfs.append({
                    "filename": fname,
                    "relative_path": rel_p,
                    "full_path": full_p,
                    "size_bytes": os.path.getsize(full_p),
                })

    # 3. Collect PDF Schedules
    sched_dir = os.path.join(output_base, "schedules")
    if os.path.exists(sched_dir):
        for fname in sorted(os.listdir(sched_dir)):
            if fname.endswith(".pdf"):
                full_p = os.path.join(sched_dir, fname)
                rel_p = os.path.relpath(full_p, output_base)
                sched_pdfs.append({
                    "filename": fname,
                    "relative_path": rel_p,
                    "full_path": full_p,
                    "size_bytes": os.path.getsize(full_p),
                })

    total_files = len(csv_files) + len(roster_pdfs) + len(sched_pdfs)

    if total_files == 0:
        st.info("No generated output files found on disk. Run an assignment to produce outputs.")
    else:
        # Top summary and bulk download bar
        all_disk_entries = []
        for item in csv_files + roster_pdfs + sched_pdfs:
            all_disk_entries.append((item["full_path"], item["relative_path"]))

        col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns([1, 1, 1, 2, 1.2])
        col_m1.metric("CSV Tables", len(csv_files))
        col_m2.metric("Class Rosters", len(roster_pdfs))
        col_m3.metric("Student Schedules", len(sched_pdfs))

        with col_m4:
            st.write("")
            all_zip = create_zip_archive(all_disk_entries)
            st.download_button(
                label="Download All Outputs (.zip)",
                data=all_zip,
                file_name="assignment_outputs.zip",
                mime="application/zip",
                type="primary",
                use_container_width=True,
                help="Download all generated CSV tables and PDF documents in one archive.",
            )
        with col_m5:
            st.write("")
            if st.button("Clear Outputs", key="btn_clear_outputs_sec", use_container_width=True, help="Delete all generated output files from disk"):
                clear_output_directory("output")
                st.session_state.last_run_success = None
                st.rerun()

        st.write("")

        # Structured tabs
        tab_csv, tab_roster, tab_sched = st.tabs([
            f"CSV Files ({len(csv_files)})",
            f"Class Rosters ({len(roster_pdfs)})",
            f"Student Schedules ({len(sched_pdfs)})",
        ])

        # --- Tab 1: CSV Files & Interactive Preview ---
        with tab_csv:
            if not csv_files:
                st.caption("No CSV files generated.")
            else:
                csv_map = {item["filename"]: item for item in csv_files}
                col_sel, col_btn = st.columns([3, 1])
                with col_sel:
                    selected_csv_name = st.selectbox(
                        "Select CSV to inspect:",
                        options=list(csv_map.keys()),
                        index=0,
                        key="sb_inspect_csv",
                        help="Choose a generated CSV to preview and download.",
                    )
                target_csv = csv_map[selected_csv_name]
                with col_btn:
                    st.write("")
                    with open(target_csv["full_path"], "rb") as f:
                        st.download_button(
                            label=f"Download {selected_csv_name}",
                            data=f.read(),
                            file_name=selected_csv_name,
                            mime="text/csv",
                            key=f"dl_btn_{selected_csv_name}",
                            use_container_width=True,
                        )

                # Dataframe preview
                try:
                    df_preview = pd.read_csv(target_csv["full_path"])
                    st.caption(f"Path: `{target_csv['relative_path']}` | Rows: {len(df_preview)} | Columns: {len(df_preview.columns)}")
                    st.dataframe(df_preview, use_container_width=True, hide_index=True)
                except Exception as e:
                    st.warning(f"Could not load preview for {selected_csv_name}: {e}")

                # Compact list of all CSV files
                with st.expander("All CSV files list"):
                    summary_data = [
                        {
                            "Filename": f["filename"],
                            "Type": f["type"],
                            "Size (KB)": round(f["size_bytes"] / 1024, 1),
                            "Path": f["relative_path"],
                        }
                        for f in csv_files
                    ]
                    st.dataframe(pd.DataFrame(summary_data), use_container_width=True, hide_index=True)

        # --- Tab 2: Class Rosters PDF ---
        with tab_roster:
            if not roster_pdfs:
                st.caption("No class roster PDFs available. Ensure 'Generate PDFs' was checked during the run.")
            else:
                col_r_zip, col_r_search = st.columns([1.5, 2.5])
                with col_r_zip:
                    rosters_zip = create_zip_archive([(item["full_path"], item["filename"]) for item in roster_pdfs])
                    st.download_button(
                        label="Download All Rosters (.zip)",
                        data=rosters_zip,
                        file_name="class_rosters.zip",
                        mime="application/zip",
                        key="btn_dl_all_rosters_zip",
                        use_container_width=True,
                    )
                with col_r_search:
                    search_roster = st.text_input(
                        "Search roster by presentation name:",
                        placeholder="Filter rosters...",
                        key="input_search_roster",
                        label_visibility="collapsed",
                    )

                filtered_rosters = roster_pdfs
                if search_roster.strip():
                    q = search_roster.strip().lower()
                    filtered_rosters = [r for r in roster_pdfs if q in r["filename"].lower()]

                if not filtered_rosters:
                    st.info(f"No rosters matching '{search_roster}'.")
                else:
                    col_r_sel, col_r_dl = st.columns([3, 1])
                    roster_map = {r["filename"]: r for r in filtered_rosters}
                    with col_r_sel:
                        selected_roster_name = st.selectbox(
                            "Select class roster to inspect:",
                            options=list(roster_map.keys()),
                            index=0,
                            key="sb_inspect_roster",
                        )
                    with col_r_dl:
                        st.write("")
                        target_roster = roster_map[selected_roster_name]
                        with open(target_roster["full_path"], "rb") as f:
                            st.download_button(
                                label="Download PDF",
                                data=f.read(),
                                file_name=selected_roster_name,
                                mime="application/pdf",
                                key=f"dl_btn_{selected_roster_name}",
                                use_container_width=True,
                            )

                    # In-browser roster preview
                    roster_view_pdf, roster_view_table = st.tabs(["PDF Document Preview", "Student Roster Table"])
                    with roster_view_pdf:
                        render_pdf_preview(target_roster["full_path"], height=650)
                    with roster_view_table:
                        assignment_dfs = [pd.read_csv(f["full_path"]) for f in csv_files if f["type"] == "Assignment"]
                        matched_students = find_class_students(selected_roster_name, assignment_dfs)
                        if matched_students is not None and not matched_students.empty:
                            st.caption(f"Enrolled Students: {len(matched_students)}")
                            st.dataframe(matched_students, use_container_width=True, hide_index=True)
                        else:
                            st.caption("Detailed student list table not found in assignment CSVs.")

                # Grid display of matching rosters in an expander
                with st.expander(f"Browse all rosters ({len(filtered_rosters)} of {len(roster_pdfs)})", expanded=False):
                    cols_per_row = 2
                    for i in range(0, len(filtered_rosters), cols_per_row):
                        row_items = filtered_rosters[i : i + cols_per_row]
                        cols = st.columns(cols_per_row)
                        for col, item in zip(cols, row_items):
                            with col:
                                clean_label = item["filename"].replace(".pdf", "")
                                with open(item["full_path"], "rb") as f:
                                    st.download_button(
                                        label=f"Download {clean_label}",
                                        data=f.read(),
                                        file_name=item["filename"],
                                        mime="application/pdf",
                                        key=f"btn_grid_roster_{item['filename']}",
                                        use_container_width=True,
                                    )

        # --- Tab 3: Student Schedules PDF ---
        with tab_sched:
            if not sched_pdfs:
                st.caption("No student schedule PDFs available. Ensure 'Generate PDFs' was checked during the run.")
            else:
                col_s_zip, col_s_search = st.columns([1.5, 2.5])
                with col_s_zip:
                    sched_zip = create_zip_archive([(item["full_path"], item["filename"]) for item in sched_pdfs])
                    st.download_button(
                        label="Download All Schedules (.zip)",
                        data=sched_zip,
                        file_name="student_schedules.zip",
                        mime="application/zip",
                        key="btn_dl_all_scheds_zip",
                        use_container_width=True,
                    )
                with col_s_search:
                    search_sched = st.text_input(
                        "Search schedule by student email:",
                        placeholder="Search student email (e.g. student0001)...",
                        key="input_search_sched",
                        label_visibility="collapsed",
                    )

                filtered_scheds = sched_pdfs
                if search_sched.strip():
                    q = search_sched.strip().lower()
                    filtered_scheds = [s for s in sched_pdfs if q in s["filename"].lower()]

                if not filtered_scheds:
                    st.info(f"No student schedules matching '{search_sched}'.")
                else:
                    col_s_sel, col_s_dl = st.columns([3, 1])
                    sched_map = {s["filename"]: s for s in filtered_scheds}
                    with col_s_sel:
                        selected_sched_name = st.selectbox(
                            "Select student schedule to inspect:",
                            options=list(sched_map.keys()),
                            index=0,
                            key="sb_inspect_sched",
                        )
                    with col_s_dl:
                        st.write("")
                        target_sched = sched_map[selected_sched_name]
                        with open(target_sched["full_path"], "rb") as f:
                            st.download_button(
                                label="Download PDF",
                                data=f.read(),
                                file_name=selected_sched_name,
                                mime="application/pdf",
                                key=f"dl_btn_{selected_sched_name}",
                                use_container_width=True,
                            )

                    # In-browser schedule preview
                    sched_view_pdf, sched_view_table = st.tabs(["PDF Document Preview", "Schedule Table"])
                    with sched_view_pdf:
                        render_pdf_preview(target_sched["full_path"], height=550)
                    with sched_view_table:
                        assignment_dfs = [pd.read_csv(f["full_path"]) for f in csv_files if f["type"] == "Assignment"]
                        matched_sched = find_student_schedule(selected_sched_name.replace(".pdf", ""), assignment_dfs)
                        if matched_sched is not None and not matched_sched.empty:
                            st.caption(f"Assigned Classes for {selected_sched_name.replace('.pdf', '')}:")
                            st.dataframe(matched_sched, use_container_width=True, hide_index=True)
                        else:
                            st.caption("Detailed schedule table not found in assignment CSVs.")

                # Show student list in a compact table inside an expander
                with st.expander(f"List of available schedules ({len(filtered_scheds)} of {len(sched_pdfs)})", expanded=False):
                    sched_table = [
                        {
                            "Student Email": s["filename"].replace(".pdf", ""),
                            "File Size (KB)": round(s["size_bytes"] / 1024, 1),
                        }
                        for s in filtered_scheds
                    ]
                    st.dataframe(pd.DataFrame(sched_table), use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
