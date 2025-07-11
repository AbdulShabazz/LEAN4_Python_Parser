#!/usr/bin/env python3
"""
Simple LEAN 4 Parser - Extracts definitions in the exact requested format
"""

import os
import re
import json, csv
from pathlib import Path

def clean_up_params(m):
    ws = m.group(0)
    if '\n' in ws:
        return '\n'  # Multiple newlines become one
    else:
        return ' '   # Other whitespace becomes single space

def parse_lean_files(directory):
    """Parse all .lean files recursively and extract lemmas, theorems, and defs."""
    
    results = []
    
    # Pattern to match lemma/theorem/def declarations
    pattern = re.compile(
        r'^(?P<indent>\s*)'  # Capture indentation
        r'(?P<attributes>(?:@\[[^\]]*\]\s*)*)'  # Optional attributes like @[simp]
        r'(?:private\s+|protected\s+|noncomputable\s+)*'  # Optional modifiers
        r'(?P<def_type>lemma|theorem|def|class|structure|inductive|variable)\s+'  # Declaration type - EXTENDED
        r'(?P<name>[^\s\(\[:]+)'  # Name (stop at space, paren, bracket, colon)        
        r'(?P<type_instance>(?:\s*(?:\{[^}]*\}|\[[^\]]*\]|\([^)]*\)))+)'  # Optional type instances, like [∀ i, T2Space (H i)]
        r'\s*:\s*'  # Colon separator
        r'(?P<proof>.*?)(?=\s*:=|\s*where\b|\s*by\b|$)',  # Type/statement
        re.MULTILINE | re.DOTALL
    )
    
    # Extract local instances (letI and haveI)    
    local_pattern = re.compile(r'^.*\b(letI|haveI)\b.*$', re.MULTILINE)

    # Find all .lean files recursively
    for lean_file in Path(directory).rglob("*.lean"):
        try:
            with open(lean_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Remove comments for cleaner parsing
            content = re.sub(r'--[^\n]*', '', content)
            content = re.sub(r'/-.*?-/', '', content, flags=re.DOTALL)
            
            # Find all matches
            for match in pattern.finditer(content):
                attribs = re.sub(r'\s+$', '', match.group('attributes'))
                def_type = match.group('def_type')
                name = match.group('name')
                type_instance = match.group('type_instance')
                proof = match.group('proof').strip()
                
                type_instance_defs = re.sub(r'^\s*|\s*$', '', re.sub(r'\s+', ' ', type_instance))
                
                # Clean up the statement
                proof = re.sub(r'\s+', ' ', proof).strip()
                
                entry = {
                    "attributes": attribs,
                    "definition_type": def_type,
                    "name": name,
                    "instances": type_instance_defs,
                    "proof": [proof] if proof else [],
                    "file": str(lean_file),
                    "line_number": ""
                }
                
                results.append(entry)
                
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
    definitions = parse_lean_files(directory)# Extract file extension and determine format

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
    summary = {}
    for d in definitions:
        dt = d['definition_type']
        summary[dt] = summary.get(dt, 0) + 1
    
    print("\nSummary:")
    for dt, count in summary.items():
        print(f"  {dt}: {count}")
    
    # Show a sample entry
    if definitions:
        print("\nSample entry:")
        print(json.dumps(definitions[0], indent=4, ensure_ascii=False))

if __name__ == "__main__":
    main()