#!/usr/bin/env python3
"""
Convert CSV file to email_targets.json format.
Removes duplicate emails and handles missing data gracefully.
"""

import csv
import json
import sys
from pathlib import Path
from typing import Dict, List, Set, Union


def normalize_email(email: str) -> str:
    """Normalize email address (lowercase, strip whitespace)."""
    if not email:
        return ""
    return email.strip().lower()


def csv_to_email_targets(
    csv_file: Path,
    output_file: Path,
    email_column: str = "Email",
    first_name_column: str = "First Name",
    last_name_column: str = "Last Name",
) -> None:
    """
    Convert CSV to email_targets.json format.
    
    Args:
        csv_file: Path to input CSV file
        output_file: Path to output JSON file
        email_column: Column name for email addresses
        first_name_column: Column name for first name
        last_name_column: Column name for last name
    """
    if not csv_file.exists():
        print(f"Error: CSV file not found: {csv_file}")
        sys.exit(1)

    seen_emails: Set[str] = set()
    email_targets: List[Dict[str, Union[str, int]]] = []
    skipped_count = 0
    duplicate_count = 0

    print(f"Reading CSV file: {csv_file}")
    
    with open(csv_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        
        # Check if required columns exist
        if email_column not in reader.fieldnames:
            print(f"Error: Column '{email_column}' not found in CSV")
            print(f"Available columns: {', '.join(reader.fieldnames[:10])}...")
            sys.exit(1)
        
        if first_name_column not in reader.fieldnames:
            print(f"Error: Column '{first_name_column}' not found in CSV")
            print(f"Available columns: {', '.join(reader.fieldnames[:10])}...")
            sys.exit(1)
        
        if last_name_column not in reader.fieldnames:
            print(f"Error: Column '{last_name_column}' not found in CSV")
            print(f"Available columns: {', '.join(reader.fieldnames[:10])}...")
            sys.exit(1)
        
        for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
            # Get email
            email = normalize_email(row.get(email_column, ""))
            
            if not email:
                skipped_count += 1
                continue
            
            # Skip duplicates
            if email in seen_emails:
                duplicate_count += 1
                continue
            
            seen_emails.add(email)
            
            # Get first name and last name
            first_name = row.get(first_name_column, "").strip()
            last_name = row.get(last_name_column, "").strip()
            
            # Combine first name and last name
            if first_name and last_name:
                name = f"{first_name} {last_name}"
            elif first_name:
                name = first_name
            elif last_name:
                name = last_name
            else:
                # If no name available, use email as fallback
                name = email.split("@")[0].replace(".", " ").title()
            
            email_targets.append({
                "target_email": email,
                "name": name
            })
    
    # Sort by email for consistency
    email_targets.sort(key=lambda x: x["target_email"])
    
    # Add index to each item (1-based index)
    for index, item in enumerate(email_targets, start=1):
        item["index"] = index
    
    # Write JSON file
    print(f"\nWriting to: {output_file}")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(email_targets, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Conversion complete!")
    print(f"  - Total unique emails: {len(email_targets)}")
    print(f"  - Duplicates skipped: {duplicate_count}")
    print(f"  - Rows skipped (no email): {skipped_count}")
    print(f"  - Output file: {output_file}")


def main():
    """Main entry point."""
    script_dir = Path(__file__).parent
    
    # Default to 11_7.csv if it exists, otherwise prompt
    csv_file = script_dir / "apollo-contacts-export.csv"
    output_file = script_dir / "email_targets.json"
    
    # Allow command line arguments
    if len(sys.argv) > 1:
        csv_file = Path(sys.argv[1])
    if len(sys.argv) > 2:
        output_file = Path(sys.argv[2])
    
    if not csv_file.exists():
        print(f"Usage: {sys.argv[0]} [input.csv] [output.json]")
        print(f"\nError: CSV file not found: {csv_file}")
        sys.exit(1)
    
    csv_to_email_targets(csv_file, output_file)


if __name__ == "__main__":
    main()

