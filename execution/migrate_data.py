import os
import shutil
from pathlib import Path
from datetime import datetime

# Define old and new generic formats for pattern matching
# Actually, we know the specific format YYYYMMDD
OLD_FORMAT = "%Y%m%d"
NEW_FORMAT = "%d-%m-%Y"

ROOT_DIR = Path(__file__).parent.parent
TMP_DIR = ROOT_DIR / ".tmp"

def migrate():
    print(f"Starting migration in {TMP_DIR}")
    if not TMP_DIR.exists():
        print("No .tmp directory found.")
        return

    # 1. Migrate Directories
    for item in TMP_DIR.iterdir():
        if item.is_dir():
            try:
                # specific validation for YYYYMMDD (8 digits)
                if len(item.name) == 8 and item.name.isdigit():
                    date_obj = datetime.strptime(item.name, OLD_FORMAT)
                    new_name = date_obj.strftime(NEW_FORMAT)
                    new_path = TMP_DIR / new_name
                    
                    if new_path.exists():
                        print(f"Skipping {item.name} -> {new_name} (Target exists)")
                    else:
                        print(f"Renaming Directory: {item.name} -> {new_name}")
                        item.rename(new_path)
                        
                        # Process files inside the renamed directory
                        migrate_files_in_dir(new_path, date_obj)
            except ValueError:
                continue # Not a date folder

def migrate_files_in_dir(directory: Path, date_obj: datetime):
    old_date_str = date_obj.strftime(OLD_FORMAT)
    new_date_str = date_obj.strftime(NEW_FORMAT)
    
    # Recursive walk for nested folders like scraped_data/ reports/
    for root, _, files in os.walk(directory):
        for file in files:
            if old_date_str in file:
                old_file_path = Path(root) / file
                new_filename = file.replace(old_date_str, new_date_str)
                new_file_path = Path(root) / new_filename
                
                print(f"  Renaming File: {file} -> {new_filename}")
                old_file_path.rename(new_file_path)

if __name__ == "__main__":
    migrate()
