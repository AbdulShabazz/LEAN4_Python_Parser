#!/usr/bin/env python3
"""
Enhanced LEAN 4 Definition Extractor
Handles complex LEAN 4 syntax including nested structures and multi-line definitions.
"""

import os
import re
import json
import argparse
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass, asdict

@dataclass
class LeanDefinition:
    """Represents a LEAN 4 definition (lemma, theorem, or def)."""
    title: str
    definition_type: str
    type_instance_definitions: str
    local_instances: List[str]
    proof: List[str]
    file_path: str = ""
    line_number: int = 0

class EnhancedLean4Parser:
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        
        # Enhanced pattern for declarations with better attribute handling
        self.declaration_pattern = re.compile(
            r'^(?P<indent>\s*)'  # Capture indentation
            r'(?P<attributes>(?:@\[[^\]]*\]\s*)*)'  # Attributes
            r'(?P<modifiers>(?:(?:private|protected|noncomputable|partial)\s+)*)'  # Modifiers
            r'(?P<def_type>lemma|theorem|def)\s+'  # Declaration type
            r'(?P<name>[^\s\[\(:{\n]+)'  # Name
            r'(?P<rest>.*?)$',  # Rest of the line
            re.MULTILINE
        )
        
        # Pattern for extracting generics/type parameters
        self.type_param_pattern = re.compile(r'\{[^}]+\}|\[[^\]]+\]|\([^)]+\)')
        
    def remove_comments(self, content: str) -> str:
        """Remove single-line and multi-line comments from LEAN code."""
        # Remove single-line comments
        content = re.sub(r'--[^\n]*', '', content)
        # Remove multi-line comments
        content = re.sub(r'/-.*?-/', '', content, flags=re.DOTALL)
        return content
    
    def find_matching_brace(self, text: str, start: int, open_char: str, close_char: str) -> int:
        """Find the position of the matching closing brace/bracket/paren."""
        count = 1
        i = start + 1
        
        while i < len(text) and count > 0:
            if text[i] == open_char:
                count += 1
            elif text[i] == close_char:
                count -= 1
            i += 1
        
        return i if count == 0 else -1
    
    def extract_balanced_expression(self, content: str, start_pos: int) -> Tuple[str, int]:
        """Extract a balanced expression starting from start_pos."""
        # Skip whitespace
        while start_pos < len(content) and content[start_pos].isspace():
            start_pos += 1
        
        if start_pos >= len(content):
            return "", start_pos
        
        # Find the end of the declaration
        brace_pairs = {'(': ')', '[': ']', '{': '}', '⟨': '⟩'}
        stack = []
        i = start_pos
        in_string = False
        
        while i < len(content):
            char = content[i]
            
            # Handle strings
            if char == '"' and (i == 0 or content[i-1] != '\\'):
                in_string = not in_string
            
            if not in_string:
                # Check for declaration end markers
                if not stack and content[i:i+2] in [':=', 'by', '= ']:
                    break
                if not stack and char == ':' and i+1 < len(content) and content[i+1] != '=':
                    # This is the type separator
                    break
                
                # Handle braces
                if char in brace_pairs:
                    stack.append(brace_pairs[char])
                elif stack and char == stack[-1]:
                    stack.pop()
            
            i += 1
        
        return content[start_pos:i].strip(), i
    
    def extract_local_instances(self, params: str) -> Tuple[List[str], str]:
        """Extract letI and haveI declarations and return cleaned params."""
        local_instances = []
        
        # Pattern for local instances with better handling of complex expressions
        pattern = re.compile(
            r'\b(letI|haveI)\s*:\s*([^:=]+?)\s*:=\s*([^,\n]+(?:⟨[^⟩]*⟩)?)'
        )
        
        cleaned_params = params
        
        for match in pattern.finditer(params):
            inst_type = match.group(1)
            inst_name = match.group(2).strip()
            inst_value = match.group(3).strip()
            
            local_instance = f"{inst_type} : {inst_name} := {inst_value}"
            local_instances.append(local_instance)
            
            # Remove from params
            cleaned_params = cleaned_params.replace(match.group(0), '')
        
        # Clean up extra whitespace and commas
        cleaned_params = re.sub(r'\s+', ' ', cleaned_params)
        cleaned_params = re.sub(r',\s*,', ',', cleaned_params)
        cleaned_params = re.sub(r'^\s*,\s*', '', cleaned_params)
        cleaned_params = re.sub(r'\s*,\s*$', '', cleaned_params)
        
        return local_instances, cleaned_params.strip()
    
    def extract_definition_body(self, content: str, match_pos: int) -> str:
        """Extract the body/statement of a definition."""
        # Find where the actual statement starts (after : or :=)
        pos = content.find(':', match_pos)
        if pos == -1:
            return ""
        
        # Skip := or :
        if content[pos:pos+2] == ':=':
            pos += 2
        else:
            pos += 1
        
        # Skip whitespace
        while pos < len(content) and content[pos] in ' \t':
            pos += 1
        
        # Find the end of the statement (before 'by' or 'where')
        end_markers = ['\nby ', '\nwhere ', '\n\n', 'by\n', 'where\n']
        
        # Also look for the next definition
        next_def = re.search(
            r'\n\s*(?:@\[[^\]]*\]\s*)*(?:private\s+|protected\s+|noncomputable\s+)*(lemma|theorem|def)\s+',
            content[pos:]
        )
        
        end_pos = len(content)
        for marker in end_markers:
            marker_pos = content.find(marker, pos)
            if marker_pos != -1 and marker_pos < end_pos:
                end_pos = marker_pos
        
        if next_def and pos + next_def.start() < end_pos:
            end_pos = pos + next_def.start()
        
        statement = content[pos:end_pos].strip()
        
        # Clean up the statement
        statement = re.sub(r'\s+', ' ', statement)
        
        return statement
    
    def parse_file(self, filepath: Path) -> List[LeanDefinition]:
        """Parse a single LEAN 4 file and extract definitions."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            if self.verbose:
                print(f"Error reading {filepath}: {e}")
            return []
        
        # Remove comments for cleaner parsing
        content_no_comments = self.remove_comments(content)
        
        definitions = []
        
        # Keep track of line numbers
        lines = content.split('\n')
        line_starts = [0]
        for line in lines[:-1]:
            line_starts.append(line_starts[-1] + len(line) + 1)
        
        def get_line_number(pos: int) -> int:
            for i, start in enumerate(line_starts):
                if pos < start:
                    return i
            return len(lines)
        
        # Find all declarations
        for match in self.declaration_pattern.finditer(content_no_comments):
            try:
                def_type = match.group('def_type')
                name = match.group('name')
                
                # Get the full declaration
                decl_start = match.start()
                line_num = get_line_number(decl_start)
                
                # Extract parameters and type
                rest_of_line = match.group('rest')
                
                # Find the complete parameter list and type
                full_content = content_no_comments[match.end():]
                params_and_type, _ = self.extract_balanced_expression(
                    rest_of_line + full_content, 0
                )
                
                # Extract local instances
                local_instances, cleaned_params = self.extract_local_instances(params_and_type)
                
                # Extract the body/statement
                body = self.extract_definition_body(content_no_comments, match.start())
                
                definition = LeanDefinition(
                    title=name,
                    definition_type=def_type,
                    type_instance_definitions=cleaned_params,
                    local_instances=local_instances,
                    proof=[body] if body else [],
                    file_path=str(filepath.relative_to(filepath.parent.parent.parent)),
                    line_number=line_num
                )
                
                definitions.append(definition)
                
            except Exception as e:
                if self.verbose:
                    print(f"Error parsing definition at line {get_line_number(match.start())} in {filepath}: {e}")
                continue
        
        return definitions
    
    def parse_directory(self, directory: Path, extensions: Set[str] = {'.lean'}) -> List[LeanDefinition]:
        """Recursively parse all LEAN 4 files in a directory."""
        all_definitions = []
        
        # Find all relevant files
        lean_files = []
        for ext in extensions:
            lean_files.extend(directory.rglob(f"*{ext}"))
        
        # Remove duplicates and sort
        lean_files = sorted(set(lean_files))
        
        print(f"Found {len(lean_files)} LEAN files to parse...")
        
        for i, filepath in enumerate(lean_files, 1):
            if i % 10 == 0 or self.verbose:
                print(f"Processing file {i}/{len(lean_files)}: {filepath.name}")
            
            definitions = self.parse_file(filepath)
            all_definitions.extend(definitions)
        
        return all_definitions
    
    def save_to_json(self, definitions: List[LeanDefinition], output_file: str, pretty: bool = True):
        """Save the extracted definitions to a JSON file."""
        # Convert dataclasses to dicts
        def_dicts = [asdict(d) for d in definitions]
        
        with open(output_file, 'w', encoding='utf-8') as f:
            if pretty:
                json.dump(def_dicts, f, indent=2, ensure_ascii=False)
            else:
                json.dump(def_dicts, f, ensure_ascii=False)
        
        print(f"\nExtracted {len(definitions)} definitions to {output_file}")
        
        # Print summary
        by_type = {}
        for d in definitions:
            by_type[d.definition_type] = by_type.get(d.definition_type, 0) + 1
        
        print("\nSummary:")
        for dt, count in sorted(by_type.items()):
            print(f"  {dt}: {count}")

def main():
    parser = argparse.ArgumentParser(
        description="Extract LEAN 4 definitions (lemmas, theorems, defs) to JSON",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s /path/to/lean/project -o definitions.json
  %(prog)s . --types lemma theorem --verbose
  %(prog)s ./src --sample 100 --pretty
        """
    )
    
    parser.add_argument(
        "directory",
        help="Parent directory to recursively search for LEAN files"
    )
    parser.add_argument(
        "-o", "--output",
        default="lean_definitions.json",
        help="Output JSON file (default: lean_definitions.json)"
    )
    parser.add_argument(
        "--types",
        nargs="+",
        choices=["lemma", "theorem", "def"],
        help="Only extract specific definition types"
    )
    parser.add_argument(
        "--sample",
        type=int,
        help="Only process first N definitions (for testing)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        default=True,
        help="Pretty-print JSON output (default: True)"
    )
    parser.add_argument(
        "--extensions",
        nargs="+",
        default=[".lean"],
        help="File extensions to process (default: .lean)"
    )
    
    args = parser.parse_args()
    
    directory = Path(args.directory)
    if not directory.exists():
        print(f"Error: Directory '{directory}' does not exist")
        return 1
    
    # Create parser and process files
    parser = EnhancedLean4Parser(verbose=args.verbose)
    definitions = parser.parse_directory(directory, set(args.extensions))
    
    # Filter by type if requested
    if args.types:
        definitions = [d for d in definitions if d.definition_type in args.types]
        print(f"\nFiltered to {len(definitions)} definitions of types: {', '.join(args.types)}")
    
    # Apply sampling if requested
    if args.sample and args.sample < len(definitions):
        definitions = definitions[:args.sample]
        print(f"\nSampling first {args.sample} definitions")
    
    # Save to JSON
    parser.save_to_json(definitions, args.output, args.pretty)
    
    # Show examples
    if definitions and args.verbose:
        print("\nExample entries:")
        for i, d in enumerate(definitions[:3]):
            print(f"\n--- Example {i+1} ---")
            print(f"Title: {d.title}")
            print(f"Type: {d.definition_type}")
            print(f"File: {d.file_path}:{d.line_number}")
            print(f"Params: {d.type_instance_definitions[:100]}...")
            if d.local_instances:
                print(f"Local instances: {len(d.local_instances)} found")
            if d.proof:
                print(f"Statement: {d.proof[0][:100]}...")
    
    return 0

if __name__ == "__main__":
    exit(main())