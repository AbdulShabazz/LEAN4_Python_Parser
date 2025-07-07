# LEAN 4 Definition Parser

A set of Python scripts to extract and analyze lemmas, theorems, and definitions from LEAN 4 source files.

## Quick Start

1. **Basic parsing:**
   ```bash
   python3 lean4_parser.py /path/to/lean/project -o definitions.json
   ```

2. **View results:**
   ```bash
   # Show first few entries
   head -n 50 definitions.json
   
   # Count definitions
   jq length definitions.json
   ```

## Scripts Overview

### 1. `lean4_parser.py` - Simple Parser
The basic parser that extracts definitions in the exact format requested:

```json
[{
    "title": "mulEquivHaarChar_piCongrRight",
    "definition_type": "lemma",
    "type_instance_definitions": "[Fintype ι] [∀ i, T2Space (H i)]...",
    "local_instances": ["letI : MeasurableSpace (Π i, H i) := borel _"],
    "proof": ["mulEquivHaarChar (ContinuousMulEquiv.piCongrRight ψ) = ∏ i, mulEquivHaarChar (ψ i)"]
}]
```

### 2. `lean4_parser_enhanced.py` - Enhanced Parser
More robust parser with better error handling and additional features:

```bash
# Parse with verbose output
python3 lean4_parser_enhanced.py ./src --verbose

# Extract only lemmas and theorems
python3 lean4_parser_enhanced.py . --types lemma theorem

# Sample first 100 definitions
python3 lean4_parser_enhanced.py . --sample 100
```

### 3. `lean_parser_utils.py` - Analysis Utilities
Tools for searching, filtering, and exporting:

```bash
# Search for definitions containing "Haar"
python3 lean_parser_utils.py definitions.json search "Haar"

# Filter only lemmas
python3 lean_parser_utils.py definitions.json filter --types lemma -o lemmas.json

# Export to CSV
python3 lean_parser_utils.py definitions.json export csv -o definitions.csv

# Export to Markdown
python3 lean_parser_utils.py definitions.json export markdown -o definitions.md

# Show statistics
python3 lean_parser_utils.py definitions.json stats
```

## Installation

1. **Requirements:**
   - Python 3.6+
   - No external dependencies (uses only standard library)

2. **Make scripts executable:**
   ```bash
   chmod +x lean4_parser.py lean4_parser_enhanced.py lean_parser_utils.py
   ```

## Examples

### Find all lemmas with local instances:
```python
import json

with open('definitions.json', 'r') as f:
    defs = json.load(f)

lemmas_with_local = [d for d in defs 
                     if d['definition_type'] == 'lemma' 
                     and d['local_instances']]

print(f"Found {len(lemmas_with_local)} lemmas with local instances")
```

### Extract definitions from specific files:
```python
specific_file_defs = [d for d in defs 
                      if 'HaarChar' in d.get('file_path', '')]
```

### Find complex definitions:
```python
# Sort by total length of parameters and local instances
complex_defs = sorted(defs, 
    key=lambda d: len(d['type_instance_definitions']) + 
                  sum(len(inst) for inst in d['local_instances']),
    reverse=True)[:10]
```

## Output Formats

### JSON (default)
Standard JSON format with all fields preserved.

### CSV
Flat format suitable for spreadsheet analysis:
```
Title,Type,Parameters,Local Instances,Statement
mulEquivHaarChar_piCongrRight,lemma,[Fintype ι]...,letI : ...,mulEquivHaarChar...
```

### Markdown
Human-readable format organized by definition type:
```markdown
## Lemmas

### `mulEquivHaarChar_piCongrRight`

**Parameters:** `[Fintype ι] [∀ i, T2Space (H i)]...`

**Local Instances:**
- `letI : MeasurableSpace (Π i, H i) := borel _`

**Statement:** `mulEquivHaarChar (ContinuousMulEquiv.piCongrRight ψ) = ∏ i, mulEquivHaarChar (ψ i)`
```

## Troubleshooting

1. **Unicode errors:** The scripts handle UTF-8 by default. If you encounter issues, ensure your LEAN files are UTF-8 encoded.

2. **Missing definitions:** The parser uses regex patterns that should catch most standard LEAN 4 syntax. For non-standard formatting, you may need to adjust the patterns.

3. **Performance:** For large projects, use `--sample` to test on a subset first.

## Advanced Usage

### Custom filtering:
```bash
# Extract and filter in one command
python3 lean4_parser.py . -o - | \
  jq '[.[] | select(.title | contains("Haar"))]' > haar_definitions.json
```

### Parallel processing (for very large codebases):
```bash
# Split by directory and process in parallel
find . -name "*.lean" -type f | \
  xargs -P 4 -I {} python3 lean4_parser.py {} -o {}.json

# Merge results
jq -s 'flatten' *.json > all_definitions.json
```

```bash
#!/bin/bash

## LEAN 4 Parser Usage Examples
### Save this as parse_lean.sh and make it executable with: chmod +x parse_lean.sh

### Basic usage - parse all LEAN files in current directory

python3 lean4_parser.py . -o all_definitions.json

### Parse only lemmas and theorems
python3 lean4_parser.py /path/to/lean/project --types lemma theorem -o lemmas_theorems.json

### Parse with verbose output to see progress
python3 lean4_parser.py ./src --verbose -o definitions.json

### Sample first 100 definitions for testing
python3 lean4_parser.py . --sample 100 -o sample.json

### Parse specific file extensions
python3 lean4_parser.py . --extensions .lean .lean4 -o all_lean_files.json

### Example Python script to filter the results
cat > filter_results.py << 'EOF'
```

```python
#!/usr/bin/env python3
import json
import sys

# Load the JSON file
with open(sys.argv[1], 'r') as f:
    definitions = json.load(f)

# Example filters:

# 1. Find all definitions containing "Haar" in the name
haar_defs = [d for d in definitions if 'Haar' in d['title']]
print(f"Found {len(haar_defs)} definitions with 'Haar' in the name")

# 2. Find all lemmas with local instances
lemmas_with_local = [d for d in definitions 
                     if d['definition_type'] == 'lemma' 
                     and d['local_instances']]
print(f"Found {len(lemmas_with_local)} lemmas with local instances")

# 3. Find all definitions in a specific file
specific_file = 'AddEquiv.lean'
file_defs = [d for d in definitions if specific_file in d.get('file_path', '')]
print(f"Found {len(file_defs)} definitions in {specific_file}")

# 4. Export filtered results
if len(sys.argv) > 2:
    with open(sys.argv[2], 'w') as f:
        json.dump(haar_defs, f, indent=2)
    print(f"Saved filtered results to {sys.argv[2]}")
```
set executable attribute at commandline
```bash
$ chmod +x filter_results.py
```

### Use the filter script
```bash
./filter_results.py all_definitions.json haar_definitions.json
```