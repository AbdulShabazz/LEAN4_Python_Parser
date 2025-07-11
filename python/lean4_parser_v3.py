#!/usr/bin/env python3
"""
Simple LEAN 4 Parser - Simpler version - captures everything up to [:=, where, by,...] etc.
"""

import os
import re
import json,csv
from pathlib import Path

#bugggy
def parse_lean_files(directory):
    """Parse all .lean files and extract definitions up to := or where."""
    
    results = []
    
    # Pattern: captures everything from doc comment/attributes/definition keyword 
    # up to (but not including) := or where
    pattern = re.compile(
        r'^.+?'  # Everything else (non-greedy)
        r'(?=\s*(?::=|where\b|by\b))',  # Stop before :=, where, or by
        re.MULTILINE | re.DOTALL
    )
    
    # Find all .lean files
    for lean_file in Path(directory).rglob("*.lean"):
        try:
            with open(lean_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Find all matches
            for match in pattern.finditer(content):
                definition = match.group(1).strip()
                if definition:
                    results.append(definition)
                    
        except Exception as e:
            print(f"Error processing {lean_file}: {e}")
            continue
    
    return results

def main():
    import sys
    
    all_params = len(sys.argv)

    if all_params < 2:
        print("Usage: python3 lean_parser.py <directory> <output_file.json>")
        sys.exit(1)
    
    directory = sys.argv[1]
    
    print(f"Parsing LEAN files in {directory}...")
    definitions = parse_lean_files(directory) # Extract file extension and determine format

    if not definitions:
        print("Error: No parsed LEAN files matched the required search and catalog criteria. Exiting")
        sys.exit(1)

    # Get output filename from command line args or use default
    output_file = sys.argv[2] if len(sys.argv[2]) > 2 else "definitions.json"

    file_name = os.path.splitext(output_file)[0].lower()
    file_ext = os.path.splitext(output_file)[1].lower()

    # Detect format based on file extension
    if file_ext == '.csv': # CSV format
        output_file = f"{file_name}.csv"        
        with open(output_file, "w", newline='', encoding="utf-8") as f:        
            writer = csv.DictWriter(f, fieldnames=definitions[0].keys())
            writer.writeheader()
            writer.writerows(definitions)            
    else: # JSON format (default for unknown extensions or no extension)
        # Fallback: treat other extensions as JSON
        output_file = f"{file_name}.json"        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(definitions, f, indent=4, ensure_ascii=False)
    
    print(f"\n{len(definitions)} definitions >> [{output_file}]")
    
    # Show summary
    
    print("\nSummary:")
    print(f"  definitions found: {len(definitions)}")

if __name__ == "__main__":
    main()