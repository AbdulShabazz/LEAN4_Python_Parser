
import re
import json
from pathlib import Path

def parse_lean_files(directory):
    """Parse all .lean files recursively and extract lemmas, theorems, and defs."""

    results = []

    # Pattern to match lemma/theorem/def declarations
    pattern = re.compile(
        r'(?P<def_type>(lemma|theorem|def))\s+',  # Declaration type
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
                def_type = match.group('def_type')
                
                entry = {
                    "definition_type": def_type,
                    "file": str(lean_file),
                    "line_number": "-"
                }
                
                results.append(entry)
        except Exception as e:
            print(f"Error processing {lean_file}: {e}")
            continue

    return results

def main():
    import sys

    if len(sys.argv) < 2:
        print("Usage: python3 lean_parser.py <directory> <filename.json>")
        sys.exit(1)

    directory = sys.argv[1]
    output_file = sys.argv[2]

    print(f"Parsing LEAN files in {directory}...")
    definitions = parse_lean_files(directory)
    
    # Save to JSON with nice formatting
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
        print(f"  {dt}s: {count}")

if __name__ == "__main__":
    main()

Notes = '''
367062 definitions >> [total_lean4_lemmas.json]

Summary:
  theorem: 228904
  def: 61534
  lemma: 76624
'''