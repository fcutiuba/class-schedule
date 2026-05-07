import unittest
import os
import shutil
import tempfile
import pandas as pd
import sys

# Add the project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scheduler.validator import validate_csv_files

class TestValidator(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory
        self.test_dir = tempfile.mkdtemp()
        self.roster_path = os.path.join(self.test_dir, "All students.csv")
        self.presenters_path = os.path.join(self.test_dir, "Presenter names.csv")
        self.signups_path = os.path.join(self.test_dir, "Audience Sign Up.csv")
        self.presentations_path = os.path.join(self.test_dir, "Presentations.csv")

    def tearDown(self):
        # Remove the directory after the test
        shutil.rmtree(self.test_dir)

    def create_valid_files(self):
        # Roster
        roster_df = pd.DataFrame({
            "Email": ["alice@school.org", "bob@school.org"],
            "Student name": ["Alice A", "Bob B"],
            "Grade level": [9, 10]
        })
        roster_df.to_csv(self.roster_path, index=False)

        # Presenters
        presenters_df = pd.DataFrame({
            "E-mail 1 - Value": ["presenter@school.org"]
        })
        presenters_df.to_csv(self.presenters_path, index=False)

        # Presentations
        presentations_df = pd.DataFrame({
            "Presentation Category (choose the best fit)": ["Academic", "Academic"],
            'Name of your presentation: "Creative Title: Descriptive Title"  (15 words max)': ["Title 1", "Title 2"],
            "Room #": ["101", "102"],
            "All presentations will be paired with a teacher advisor. Is there a teacher already associated with your presentation, such as club advisor or class teacher? If yes, please write their last name below. ": ["Smith", "Jones"]
        })
        presentations_df.to_csv(self.presentations_path, index=False)

        # Signups
        signups_df = pd.DataFrame({
            "Email Address": ["alice@school.org", "bob@school.org"],
            "Which presentation is your first choice for the Academic block?": ["Title 1", "Title 2"],
            "Which presentation is your second choice for the Academic block?": ["Title 2", "Title 1"],
            "Which presentation is your third choice for the Academic block?": ["Title 1", "Title 2"],
            "Which presentation is your fourth choice for the Academic block?": ["Title 2", "Title 1"],
            "Which presentation is your fifth choice for the Academic block?": ["Title 1", "Title 2"]
        })
        signups_df.to_csv(self.signups_path, index=False)

    def test_all_valid(self):
        self.create_valid_files()
        is_ok, messages = validate_csv_files(
            self.roster_path, self.presenters_path, self.signups_path, self.presentations_path
        )
        self.assertTrue(is_ok)
        self.assertTrue(any("[SUCCESS]" in m for m in messages))

    def test_missing_file(self):
        self.create_valid_files()
        os.remove(self.roster_path)
        is_ok, messages = validate_csv_files(
            self.roster_path, self.presenters_path, self.signups_path, self.presentations_path
        )
        self.assertFalse(is_ok)
        self.assertTrue(any("[ERROR] Roster file missing" in m for m in messages))

    def test_missing_roster_column(self):
        self.create_valid_files()
        # Read and drop a column
        df = pd.read_csv(self.roster_path)
        df = df.drop(columns=["Grade level"])
        df.to_csv(self.roster_path, index=False)

        is_ok, messages = validate_csv_files(
            self.roster_path, self.presenters_path, self.signups_path, self.presentations_path
        )
        self.assertFalse(is_ok)
        self.assertTrue(any("missing required column: 'Grade level'" in m for m in messages))

    def test_missing_signups_choices(self):
        self.create_valid_files()
        # Signups missing 5th choice
        df = pd.read_csv(self.signups_path)
        df = df.drop(columns=["Which presentation is your fifth choice for the Academic block?"])
        df.to_csv(self.signups_path, index=False)

        is_ok, messages = validate_csv_files(
            self.roster_path, self.presenters_path, self.signups_path, self.presentations_path
        )
        # validator.py currently treats missing choices as a WARNING in validate_csv_files (Step 6)
        # unless it crashes, but it has a try-except.
        self.assertTrue(any("[WARNING] Category 'Academic' found in Presentations but choice columns missing in Signups." in m for m in messages))

    def test_email_mismatch_warning(self):
        self.create_valid_files()
        # Add a signup email that isn't in roster
        df = pd.read_csv(self.signups_path)
        new_row = df.iloc[0].copy()
        new_row["Email Address"] = "stranger@school.org"
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        df.to_csv(self.signups_path, index=False)

        is_ok, messages = validate_csv_files(
            self.roster_path, self.presenters_path, self.signups_path, self.presentations_path
        )
        self.assertTrue(is_ok) # Should still be OK, just a warning
        self.assertTrue(any("emails in Signups are NOT in the Master Roster" in m for m in messages))

if __name__ == "__main__":
    unittest.main()
