#!/usr/bin/env python3
"""
Update name fields in existing email_targets.json using First Name + Last Name from CSV.
"""

import csv
import json
import sys
from pathlib import Path
from typing import Dict


def normalize_email(email: str) -> str:
    """Normalize email address (lowercase, strip whitespace)."""
    if not email:
        return ""
    return email.strip().lower()


def load_name_mapping_from_csv(csv_file: Path) -> Dict[str, str]:
    """
    Load email -> name mapping from CSV file.
    Returns dict mapping normalized email to "FirstName LastName".
    """
    name_mapping: Dict[str, str] = {}
    
    print(f"Reading CSV file: {csv_file}")
    
    with open(csv_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        
        if "Email" not in reader.fieldnames:
            print(f"Error: 'Email' column not found in CSV")
            sys.exit(1)
        if "First Name" not in reader.fieldnames:
            print(f"Error: 'First Name' column not found in CSV")
            sys.exit(1)
        if "Last Name" not in reader.fieldnames:
            print(f"Error: 'Last Name' column not found in CSV")
            sys.exit(1)
        
        for row in reader:
            email = normalize_email(row.get("Email", ""))
            if not email:
                continue
            
            first_name = row.get("First Name", "").strip()
            last_name = row.get("Last Name", "").strip()
            
            # Combine first name and last name
            if first_name and last_name:
                name = f"{first_name} {last_name}"
            elif first_name:
                name = first_name
            elif last_name:
                name = last_name
            else:
                continue  # Skip if no name available
            
            # Store mapping (if email already exists, keep the first one)
            if email not in name_mapping:
                name_mapping[email] = name
    
    print(f"Loaded {len(name_mapping)} email -> name mappings from CSV")
    return name_mapping


def update_email_targets_json(json_file: Path, name_mapping: Dict[str, str]) -> None:
    """
    Update name fields in email_targets.json using the name mapping from CSV.
    """
    print(f"\nReading JSON file: {json_file}")
    
    # Read existing JSON
    with open(json_file, "r", encoding="utf-8") as f:
        email_targets = json.load(f)
    
    if not isinstance(email_targets, list):
        print(f"Error: JSON file must contain an array")
        sys.exit(1)
    
    updated_count = 0
    not_found_count = 0
    
    # Update names
    for item in email_targets:
        if not isinstance(item, dict):
            continue
        
        target_email = normalize_email(item.get("target_email", ""))
        if not target_email:
            continue
        
        if target_email in name_mapping:
            old_name = item.get("name", "")
            new_name = name_mapping[target_email]
            item["name"] = new_name
            updated_count += 1
            if old_name != new_name:
                print(f"  Updated: {target_email} - '{old_name}' -> '{new_name}'")
        else:
            not_found_count += 1
    
    # Write updated JSON
    print(f"\nWriting updated JSON to: {json_file}")
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(email_targets, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Update complete!")
    print(f"  - Total entries: {len(email_targets)}")
    print(f"  - Updated: {updated_count}")
    print(f"  - Not found in CSV: {not_found_count}")


def main():
    """Main entry point."""
    script_dir = Path(__file__).parent
    
    csv_file = script_dir / "apollo-contacts-export.csv"
    json_file = script_dir / "email_targets.json"
    
    # Allow command line arguments
    if len(sys.argv) > 1:
        csv_file = Path(sys.argv[1])
    if len(sys.argv) > 2:
        json_file = Path(sys.argv[2])
    
    if not csv_file.exists():
        print(f"Usage: {sys.argv[0]} [input.csv] [email_targets.json]")
        print(f"\nError: CSV file not found: {csv_file}")
        sys.exit(1)
    
    if not json_file.exists():
        print(f"Error: JSON file not found: {json_file}")
        sys.exit(1)
    
    # Load name mapping from CSV
    name_mapping = load_name_mapping_from_csv(csv_file)
    
    # Update JSON file
    update_email_targets_json(json_file, name_mapping)


if __name__ == "__main__":
    main()

