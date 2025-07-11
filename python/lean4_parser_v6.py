import os
import re
import json, csv
from pathlib import Path
from typing import List, Optional, Dict, Tuple

def extract_signatures(directory):
    """Extract only the signatures (before := by, where)."""
    
    pattern = re.compile(
        r'((?:@\[[^\]]*\]\s*)*'  # Optional attributes
        r'(?:private\s+|protected\s+|noncomputable\s+)*'  # Optional modifiers
        r'(?:lemma|theorem|def|class|structure|inductive|variable)\s+'  # Definition type
        r'.*?)'  # Everything up to := or where
        r'(?=\s*(?::=\s+by\b|where\b))',
        re.MULTILINE | re.DOTALL
    )

    definitions = []    

    # Find all .lean files recursively
    for lean_file in Path(directory).rglob("*.lean"):
        try:
            with open(lean_file, 'r', encoding='utf-8') as f:
                content = f.read()            
            signatures = pattern.findall(content)
            definitions.append( {"file": str(lean_file), "proofs": [sig.strip() for sig in signatures]} )   
        except Exception as e:
            print(f"Error processing {lean_file}: {e}")
            continue
    return definitions

def main():
    import sys
    
    all_params = len(sys.argv)

    if all_params < 2:
        print("Usage: python3 lean_parser.py <directory> <output_file.json>")
        sys.exit(1)
    
    directory = sys.argv[1]
    
    print(f"Parsing LEAN files in {directory}...")
    definitions = extract_signatures(directory)# Extract file extension and determine format

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
    """ summary = {}
    for d in definitions:
        dt = d['definition_type']
        summary[dt] = summary.get(dt, 0) + 1
    
    print("\nSummary:")
    for dt, count in summary.items():
        print(f"  {dt}: {count}")
    
    # Show a sample entry
    if definitions:
        print("\nSample entry:")
        print(json.dumps(definitions[0], indent=4, ensure_ascii=False))"""

if __name__ == "__main__":
    main()