#!/usr/bin/env python3
"""
Simple LEAN 4 Parser - Extracts definitions in the exact requested format
"""

import os
import re
import json, csv
from pathlib import Path
from typing import List, Optional, Dict, Tuple

def clean_up_params(m):
    ws = m.group(0)
    if '\n' in ws:
        return '\n'  # Multiple newlines become one
    else:
        return ' '   # Other whitespace becomes single space

def parse_defs(curr_line: dict) -> dict:

    i = curr_line['i']
    I = curr_line['I']

    pattern = re.compile(r'[^\s\(\[:]+', re.MULTILINE | re.DOTALL) # Name (stop at space, paren, bracket, colon) 
    if i<I and not re.search(pattern, curr_line['content'][i]):
        i += 1

    if i < I:
        curr_line['entry']['line_number'] = i + 1  # Line numbers are 1-based
        curr_line['entry']['name'] = curr_line['content'][i]
        i += 1
    
    pattern = re.compile(r'(?P<proof>.*?)(?=\s*:=\s+by\b|\s*where\b|$)', re.MULTILINE | re.DOTALL)
    while i<I and not re.search(pattern, curr_line['content'][i]):
        curr_line['entry']['instances'] = f"{curr_line['entry']['instances']} {curr_line['content'][i]}"
        i += 1

    curr_line['i'] = i
    if i<I:
        curr_line['entry']['proof'] = curr_line['content'][i]

    return curr_line

def parse_attr(curr_line: dict) -> dict:

    curr_line['entry'] = {
        "attributes": "",
        "definition_type": "",
        "name": "",
        "instances": "",
        "proof": "",
        "file": curr_line['lean_file'],
        "line_number": curr_line['i']
    }

    i = curr_line['i']
    I = curr_line['I']

    while i<I and not re.search(r'(?:@\[[^\]]*\]\s*)*', curr_line['content'][i]):
        i += 1
        
    if i < I:
        curr_line['entry']['attributes'] = curr_line['content'][i]
        i += 1

    pattern = re.compile(
        r'(?:private\s+|protected\s+|noncomputable\s+)*'  # Optional modifiers
        r'(?P<def_type>lemma|theorem|def|class|structure|inductive|variable)\s+',  # Declaration type
        re.DOTALL
    )

    while i<I and not re.search(pattern, curr_line['content'][i]):
        curr_line['entry']['attributes'] = f"{curr_line['entry']['attributes']} {curr_line['content'][i]}"
        i += 1

    curr_line['i'] = i        
    if i < I:
        curr_line['entry']['definition_type'] = curr_line['content'][i]

    curr_line = parse_defs(curr_line)

    return curr_line

def parse_lean_files(directory):
    """Parse all .lean files recursively and extract lemmas, theorems, and defs."""

    o = {
        "lean_file": "",
        "entry": {},
        "results": [],
        "i": 0,
        "I": 0,
        "content": []
    }

    # Find all .lean files recursively
    for lean_file in Path(directory).rglob("*.lean"):
        try:
            with open(lean_file, 'r', encoding='utf-8') as f:
                content = f.read().splitlines()
            o['entry'] = {}
            o['lean_file'] = str(lean_file)
            o['content'] = content
            o['i'] = 0
            o['I'] = len(content)
            o = parse_attr(o)                
            o['results'].append(o['entry'])                
        except Exception as e:
            print(f"Error processing {lean_file}: {e}")
            continue
    
    return o['results']

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