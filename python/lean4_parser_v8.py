import os
import re
import pickle, json, csv
from collections import defaultdict
from typing import List, Dict, Set, Tuple, Optional
from pathlib import Path

class Lean4Parser:
    """Simple LEAN 4 parser (JSON) using word-boundary tokenization"""
    
    def __init__(self):
        self.adjacency_list = defaultdict(set)
        self.word_to_id = {}
        self.id_to_word = {}
        self.current_id = 0
        self.lemmas = {}  # name -> (file, token_indices)
        
    def get_word_id(self, word: str) -> int:
        """Get or create ID for a word"""
        if word not in self.word_to_id:
            self.word_to_id[word] = self.current_id
            self.id_to_word[self.current_id] = word
            self.current_id += 1
        return self.word_to_id[word]
    
    def tokenize_file(self, filepath: str) -> List[str]:
        """Simple word-boundary tokenization"""
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Remove comments
        content = re.sub(r'--[^\n]*', '', content)
        content = re.sub(r'/-.*?-/', '', content, flags=re.DOTALL)
        
        # Split on whitespace and punctuation, keeping the punctuation
        tokens = re.findall(r'\b\w+\b|[^\w\s]', content)
        
        return tokens
    
    def extract_declarations(self, tokens: List[str], filepath: str):
        """Extract lemma/theorem/def declarations"""
        decl_keywords = {'lemma', 'theorem', 'def', 'axiom', 'example', 'instance', 'structure', 'class'}
        
        i = 0
        while i < len(tokens):
            if tokens[i] in decl_keywords:
                # Found a declaration
                decl_type = tokens[i]
                
                # Next non-punctuation token should be the name
                j = i + 1
                while j < len(tokens) and not tokens[j].isalnum():
                    j += 1
                
                if j < len(tokens):
                    name = tokens[j]
                    
                    # Store lemma info (simplified - just track start position)
                    if name not in self.lemmas:
                        self.lemmas[name] = []
                    self.lemmas[name].append((filepath, i, decl_type))
            
            i += 1
    
    def build_adjacency_list(self, tokens: List[str]):
        """Build adjacency list from token sequence"""
        for i in range(len(tokens) - 1):
            curr_id = self.get_word_id(tokens[i])
            next_id = self.get_word_id(tokens[i + 1])
            self.adjacency_list[curr_id].add(next_id)
    
    def parse_directory(self, directory: str):
        """Parse all LEAN 4 files in directory and subdirectories"""
        lean_files = list(Path(directory).rglob('*.lean'))
        print(f"Found {len(lean_files)} LEAN files")
        
        total_tokens = 0
        for filepath in lean_files:
            print(f"Parsing {filepath}")
            try:
                tokens = self.tokenize_file(str(filepath))
                total_tokens += len(tokens)
                
                # Extract declarations
                self.extract_declarations(tokens, str(filepath))
                
                # Build adjacency list
                self.build_adjacency_list(tokens)
                
            except Exception as e:
                print(f"Error parsing {filepath}: {e}")
        
        print(f"\nParsing complete:")
        print(f"  Total tokens: {total_tokens}")
        print(f"  Unique words: {len(self.word_to_id)}")
        print(f"  Declarations found: {len(self.lemmas)}")
        print(f"  Compression ratio: {total_tokens / len(self.word_to_id):.2f}x")
        
    def save(self, output_file: str):
        """Save the compressed representation as JSON"""
        # Convert sets to lists for JSON serialization
        adjacency_list_json = {
            str(k): list(v) for k, v in self.adjacency_list.items()
        }
        
        # Convert integer keys to strings for JSON
        id_to_word_json = {str(k): v for k, v in self.id_to_word.items()}
        
        data = {
            'adjacency_list': adjacency_list_json,
            'word_to_id': self.word_to_id,
            'id_to_word': id_to_word_json,
            'lemmas': self.lemmas,
            'stats': {
                'unique_words': len(self.word_to_id),
                'total_declarations': len(self.lemmas),
                'graph_edges': sum(len(v) for v in self.adjacency_list.values())
            }
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"\nSaved to {output_file}")
        print(f"  File size: {os.path.getsize(output_file) / 1024 / 1024:.2f} MB")
        print(f"  Format: JSON (human-readable)")
    
    def load(self, input_file: str):
        """Load compressed representation from JSON"""
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Convert adjacency list back to defaultdict with sets
        self.adjacency_list = defaultdict(set)
        for k, v in data['adjacency_list'].items():
            self.adjacency_list[int(k)] = set(v)
        
        self.word_to_id = data['word_to_id']
        
        # Convert string keys back to integers
        self.id_to_word = {int(k): v for k, v in data['id_to_word'].items()}
        
        self.lemmas = data['lemmas']
        
        print(f"Loaded from {input_file}")
        print(f"  Unique words: {len(self.word_to_id)}")
        print(f"  Declarations: {len(self.lemmas)}")
        if 'stats' in data:
            print(f"  Graph edges: {data['stats']['graph_edges']}")
    
    def find_lemmas_with_word(self, word: str) -> List[str]:
        """Find all lemmas containing a specific word"""
        if word not in self.word_to_id:
            return []
        
        word_id = self.word_to_id[word]
        result = []
        
        # Check which lemmas have edges from/to this word
        for lemma_name, locations in self.lemmas.items():
            # This is a simple heuristic - in practice you'd want to
            # actually check the token sequence around the lemma
            if lemma_name.find(word) != -1:
                result.append(lemma_name)
        
        return result
    
    def get_word_neighbors(self, word: str) -> Dict[str, int]:
        """Get words that frequently follow a given word"""
        if word not in self.word_to_id:
            return {}
        
        word_id = self.word_to_id[word]
        neighbors = {}
        
        for next_id in self.adjacency_list[word_id]:
            next_word = self.id_to_word[next_id]
            neighbors[next_word] = neighbors.get(next_word, 0) + 1
        
        return dict(sorted(neighbors.items(), key=lambda x: x[1], reverse=True))
    
    def find_pattern(self, pattern: List[str]) -> int:
        """Count occurrences of a word pattern"""
        if not pattern or pattern[0] not in self.word_to_id:
            return 0
        
        count = 0
        current_ids = {self.word_to_id[pattern[0]]}
        
        for i in range(1, len(pattern)):
            if pattern[i] not in self.word_to_id:
                return 0
            
            next_id = self.word_to_id[pattern[i]]
            new_current = set()
            
            for curr_id in current_ids:
                if next_id in self.adjacency_list[curr_id]:
                    new_current.add(next_id)
                    if i == len(pattern) - 1:
                        count += 1
            
            current_ids = new_current
            if not current_ids:
                break
        
        return count


# Example usage
if __name__ == "__main__":
    parser = Lean4Parser()
    
    # Example: Parse a Lean 4 project
    # parser.parse_directory("/path/to/mathlib4")
    # parser.save("lean4_corpus.json")
    
    # Example: Load and query
    # parser.load("lean4_corpus.json")
    # 
    # # Find lemmas containing "prime"
    # prime_lemmas = parser.find_lemmas_with_word("prime")
    # print(f"Found {len(prime_lemmas)} lemmas with 'prime'")
    # 
    # # See what commonly follows "lemma"
    # next_words = parser.get_word_neighbors("lemma")
    # print(f"Common words after 'lemma': {list(next_words.items())[:10]}")
    # 
    # # Count pattern occurrences
    # count = parser.find_pattern(["by", "simp"])
    # print(f"Pattern 'by simp' appears {count} times")
    
    print("Parser ready to begin.\n\nUsage: lean_parser.py <directory> <output_file.json>")

def main():
    import sys
    
    all_params = len(sys.argv)

    if all_params < 2:
        print("Usage: python3 lean_parser.py <directory> <output_file.json>")
        sys.exit(1)
    
    directory = sys.argv[1]
    
    print(f"Parsing LEAN files in {directory}...")

    # Get output filename from command line args or use default
    output_file = sys.argv[2] if len(sys.argv[2]) > 2 else "definitions.json"

    parser.parse_directory(directory)
    parser.save(output_file)

if __name__ == "__main__":
    main()