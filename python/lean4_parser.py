#!/usr/bin/env python3
"""
Simple LEAN 4 Parser - Extracts definitions in the exact requested format
"""

import os
import re
import json
from pathlib import Path

def parse_lean_files(directory):
    """Parse all .lean files recursively and extract lemmas, theorems, and defs."""
    
    results = []
    
    # Pattern to match lemma/theorem/def declarations
    pattern = re.compile(
        r'^(?:@\[[^\]]*\]\s*)*'  # Optional attributes like @[simp]
        r'(?:private\s+|protected\s+|noncomputable\s+)*'  # Optional modifiers
        r'(lemma|theorem|def)\s+'  # Declaration type
        r'([^\s\[\(:]+)'  # Name
        r'\s*([^:]+?):'  # Parameters before the colon
        r'(.*?)(?=\s*:=|\s*by\b|\s*where\b)',  # The statement/type
        re.MULTILINE | re.DOTALL
    )
    
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
                def_type = match.group(1)
                name = match.group(2)
                params = match.group(3).strip()
                statement = match.group(4).strip()
                
                # Extract local instances (letI and haveI)
                local_instances = []
                local_pattern = re.compile(r'(letI|haveI)\s*:\s*([^:=]+):=\s*([^,\n]+)')
                
                for local_match in local_pattern.finditer(params):
                    inst_type = local_match.group(1)
                    inst_name = local_match.group(2).strip()
                    inst_value = local_match.group(3).strip()
                    local_instances.append(f"{inst_type} : {inst_name} := {inst_value}")
                
                # Remove local instances from params to get clean type_instance_definitions
                clean_params = params
                for inst in local_instances:
                    clean_params = clean_params.replace(inst, '')
                
                # Clean up whitespace
                clean_params = re.sub(r'\s+', ' ', clean_params).strip()
                clean_params = re.sub(r',\s*,', ',', clean_params).strip(', ')
                
                # Clean up the statement
                statement = re.sub(r'\s+', ' ', statement).strip()
                
                entry = {
                    "title": name,
                    "definition_type": def_type,
                    "type_instance_definitions": clean_params,
                    "local_instances": local_instances,
                    "proof": [statement] if statement else []
                }
                
                results.append(entry)
                
        except Exception as e:
            print(f"Error processing {lean_file}: {e}")
            continue
    
    return results

def main():
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python3 lean_parser.py <directory> [output_file.json]")
        sys.exit(1)
    
    directory = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else "lean_definitions.json"
    
    print(f"Parsing LEAN files in {directory}...")
    definitions = parse_lean_files(directory)
    
    # Save to JSON with nice formatting
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(definitions, f, indent=4, ensure_ascii=False)
    
    print(f"\nExtracted {len(definitions)} definitions to {output_file}")
    
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