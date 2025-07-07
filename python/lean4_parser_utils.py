#!/usr/bin/env python3
"""
LEAN Parser Utilities - Tools for working with extracted LEAN definitions
"""

import json
import argparse
from pathlib import Path
from typing import List, Dict
import csv
import re

class LeanDefinitionAnalyzer:
    def __init__(self, json_file: str):
        with open(json_file, 'r', encoding='utf-8') as f:
            self.definitions = json.load(f)
    
    def search(self, pattern: str, field: str = 'title') -> List[Dict]:
        """Search definitions by regex pattern in specified field."""
        regex = re.compile(pattern, re.IGNORECASE)
        results = []
        
        for d in self.definitions:
            if field == 'any':
                # Search in all text fields
                text = ' '.join([
                    str(d.get('title', '')),
                    str(d.get('type_instance_definitions', '')),
                    ' '.join(d.get('local_instances', [])),
                    ' '.join(d.get('proof', []))
                ])
                if regex.search(text):
                    results.append(d)
            elif field in d and regex.search(str(d[field])):
                results.append(d)
        
        return results
    
    def filter_by_type(self, def_types: List[str]) -> List[Dict]:
        """Filter definitions by type (lemma, theorem, def)."""
        return [d for d in self.definitions if d['definition_type'] in def_types]
    
    def get_dependencies(self, definition_name: str) -> List[str]:
        """Extract potential dependencies from a definition's proof."""
        deps = set()
        
        for d in self.definitions:
            if d['title'] == definition_name:
                # Look for references to other definitions in the proof
                proof_text = ' '.join(d.get('proof', []))
                
                # Find potential theorem/lemma references
                for other in self.definitions:
                    if other['title'] != definition_name and other['title'] in proof_text:
                        deps.add(other['title'])
                
                break
        
        return sorted(deps)
    
    def export_to_csv(self, output_file: str):
        """Export definitions to CSV format."""
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Title', 'Type', 'Parameters', 'Local Instances', 'Statement'])
            
            for d in self.definitions:
                writer.writerow([
                    d['title'],
                    d['definition_type'],
                    d['type_instance_definitions'],
                    ' | '.join(d['local_instances']),
                    ' '.join(d['proof'])
                ])
    
    def export_to_markdown(self, output_file: str):
        """Export definitions to Markdown format."""
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("# LEAN 4 Definitions\n\n")
            
            # Group by type
            by_type = {}
            for d in self.definitions:
                dt = d['definition_type']
                if dt not in by_type:
                    by_type[dt] = []
                by_type[dt].append(d)
            
            for def_type, defs in by_type.items():
                f.write(f"## {def_type.capitalize()}s\n\n")
                
                for d in sorted(defs, key=lambda x: x['title']):
                    f.write(f"### `{d['title']}`\n\n")
                    
                    if d['type_instance_definitions']:
                        f.write(f"**Parameters:** `{d['type_instance_definitions']}`\n\n")
                    
                    if d['local_instances']:
                        f.write("**Local Instances:**\n")
                        for inst in d['local_instances']:
                            f.write(f"- `{inst}`\n")
                        f.write("\n")
                    
                    if d['proof']:
                        f.write(f"**Statement:** `{' '.join(d['proof'])}`\n\n")
                    
                    f.write("---\n\n")
    
    def statistics(self) -> Dict:
        """Generate statistics about the definitions."""
        stats = {
            'total': len(self.definitions),
            'by_type': {},
            'with_local_instances': 0,
            'avg_param_length': 0,
            'most_complex': None
        }
        
        # Count by type
        param_lengths = []
        max_complexity = 0
        
        for d in self.definitions:
            # Type counts
            dt = d['definition_type']
            stats['by_type'][dt] = stats['by_type'].get(dt, 0) + 1
            
            # Local instances
            if d['local_instances']:
                stats['with_local_instances'] += 1
            
            # Parameter length
            param_len = len(d['type_instance_definitions'])
            param_lengths.append(param_len)
            
            # Complexity (based on length and local instances)
            complexity = param_len + len(' '.join(d['local_instances']))
            if complexity > max_complexity:
                max_complexity = complexity
                stats['most_complex'] = d['title']
        
        stats['avg_param_length'] = sum(param_lengths) / len(param_lengths) if param_lengths else 0
        
        return stats

def main():
    parser = argparse.ArgumentParser(
        description="Utilities for working with extracted LEAN definitions"
    )
    
    parser.add_argument("json_file", help="Input JSON file with LEAN definitions")
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Search command
    search_parser = subparsers.add_parser('search', help='Search definitions')
    search_parser.add_argument('pattern', help='Regex pattern to search for')
    search_parser.add_argument('--field', default='title', 
                             choices=['title', 'type_instance_definitions', 'proof', 'any'],
                             help='Field to search in')
    
    # Filter command
    filter_parser = subparsers.add_parser('filter', help='Filter by definition type')
    filter_parser.add_argument('--types', nargs='+', required=True,
                             choices=['lemma', 'theorem', 'def'],
                             help='Definition types to include')
    filter_parser.add_argument('-o', '--output', help='Output filtered results to file')
    
    # Export command
    export_parser = subparsers.add_parser('export', help='Export to different formats')
    export_parser.add_argument('format', choices=['csv', 'markdown'],
                             help='Export format')
    export_parser.add_argument('-o', '--output', required=True,
                             help='Output file')
    
    # Stats command
    stats_parser = subparsers.add_parser('stats', help='Show statistics')
    
    # Dependencies command
    deps_parser = subparsers.add_parser('deps', help='Find dependencies')
    deps_parser.add_argument('definition', help='Definition name to analyze')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    analyzer = LeanDefinitionAnalyzer(args.json_file)
    
    if args.command == 'search':
        results = analyzer.search(args.pattern, args.field)
        print(f"Found {len(results)} matches:")
        for r in results:
            print(f"  {r['definition_type']} {r['title']}")
    
    elif args.command == 'filter':
        results = analyzer.filter_by_type(args.types)
        print(f"Found {len(results)} definitions of types: {', '.join(args.types)}")
        
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"Saved to {args.output}")
    
    elif args.command == 'export':
        if args.format == 'csv':
            analyzer.export_to_csv(args.output)
        elif args.format == 'markdown':
            analyzer.export_to_markdown(args.output)
        print(f"Exported to {args.output}")
    
    elif args.command == 'stats':
        stats = analyzer.statistics()
        print("\nStatistics:")
        print(f"  Total definitions: {stats['total']}")
        print(f"  By type:")
        for dt, count in stats['by_type'].items():
            print(f"    {dt}: {count}")
        print(f"  With local instances: {stats['with_local_instances']}")
        print(f"  Average parameter length: {stats['avg_param_length']:.1f} characters")
        if stats['most_complex']:
            print(f"  Most complex definition: {stats['most_complex']}")
    
    elif args.command == 'deps':
        deps = analyzer.get_dependencies(args.definition)
        if deps:
            print(f"Potential dependencies of {args.definition}:")
            for d in deps:
                print(f"  - {d}")
        else:
            print(f"No dependencies found for {args.definition}")

if __name__ == "__main__":
    main()