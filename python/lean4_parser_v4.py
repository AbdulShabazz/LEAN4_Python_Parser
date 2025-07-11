#!/usr/bin/env python3
"""
LEAN 4 State Machine Parser to properly handle nested delimiters and LEAN's complex syntax
"""

import os
import json
import csv
from pathlib import Path
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple

class TokenType(Enum):
    # Keywords
    LEMMA = auto()
    THEOREM = auto()
    DEF = auto()
    CLASS = auto()
    STRUCTURE = auto()
    INDUCTIVE = auto()
    VARIABLE = auto()
    WHERE = auto()
    BY = auto()
    
    # Delimiters
    LPAREN = auto()      # (
    RPAREN = auto()      # )
    LBRACKET = auto()    # [
    RBRACKET = auto()    # ]
    LBRACE = auto()      # {
    RBRACE = auto()      # }
    COLON = auto()       # :
    ASSIGN = auto()      # :=
    
    # Comments
    LINE_COMMENT = auto()    # --
    BLOCK_COMMENT = auto()   # /- -/
    DOC_COMMENT = auto()     # /--
    
    # Attributes
    ATTRIBUTE = auto()   # @[...]
    
    # Modifiers
    PRIVATE = auto()
    PROTECTED = auto()
    NONCOMPUTABLE = auto()
    
    # Other
    IDENTIFIER = auto()
    WHITESPACE = auto()
    NEWLINE = auto()
    STRING = auto()
    OTHER = auto()
    EOF = auto()

@dataclass
class Token:
    type: TokenType
    value: str
    line: int
    column: int

@dataclass
class Definition:
    doc_comment: str = ""
    attributes: List[str] = field(default_factory=list)
    modifiers: List[str] = field(default_factory=list)
    def_type: str = ""
    name: str = ""
    signature: str = ""
    body: str = ""
    file: str = ""
    line: int = 0

class Lexer:
    def __init__(self, content: str):
        self.content = content
        self.position = 0
        self.line = 1
        self.column = 1
        
    def peek(self, offset: int = 0) -> Optional[str]:
        pos = self.position + offset
        if pos < len(self.content):
            return self.content[pos]
        return None
    
    def advance(self) -> Optional[str]:
        if self.position >= len(self.content):
            return None
        char = self.content[self.position]
        self.position += 1
        if char == '\n':
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        return char
    
    def read_while(self, predicate) -> str:
        start = self.position
        while self.position < len(self.content) and predicate(self.content[self.position]):
            self.advance()
        return self.content[start:self.position]
    
    def skip_whitespace(self):
        self.read_while(lambda c: c in ' \t')
    
    def read_line_comment(self) -> Token:
        start_line, start_col = self.line, self.column
        self.advance()  # skip first -
        self.advance()  # skip second -
        value = self.read_while(lambda c: c != '\n')
        return Token(TokenType.LINE_COMMENT, '--' + value, start_line, start_col)
    
    def read_block_comment(self) -> Token:
        start_line, start_col = self.line, self.column
        self.advance()  # skip /
        self.advance()  # skip -
        
        # Check if it's a doc comment
        is_doc = self.peek() == '-'
        if is_doc:
            self.advance()
        
        comment_text = '/-' + ('-' if is_doc else '')
        depth = 1
        
        while depth > 0 and self.position < len(self.content):
            if self.peek() == '-' and self.peek(1) == '/':
                self.advance()
                self.advance()
                comment_text += '-/'
                depth -= 1
            elif self.peek() == '/' and self.peek(1) == '-':
                self.advance()
                self.advance()
                comment_text += '/-'
                depth += 1
            else:
                comment_text = f"{comment_text}{self.advance()}"
        
        return Token(
            TokenType.DOC_COMMENT if is_doc else TokenType.BLOCK_COMMENT,
            comment_text,
            start_line,
            start_col
        )
    
    def read_string(self) -> Token:
        start_line, start_col = self.line, self.column
        quote_char = self.advance()  # skip opening quote
        value = quote_char if quote_char else ''
        
        while self.position < len(self.content):
            char = self.advance()
            value = f"{value}{char}"
            if char == quote_char:
                break
            elif char == '\\' and self.position < len(self.content):
                value = f"{value}{self.advance()}" # skip escaped character
        
        return Token(TokenType.STRING, value, start_line, start_col)
    
    def read_identifier(self) -> Token:
        start_line, start_col = self.line, self.column
        value = self.read_while(lambda c: c.isalnum() or c in '_\'ₐₑₕᵢⱼₖₗₘₙₒₚᵣₛₜᵤᵥₓ₀₁₂₃₄₅₆₇₈₉')
        
        # Check for keywords
        keyword_map = {
            'lemma': TokenType.LEMMA,
            'theorem': TokenType.THEOREM,
            'def': TokenType.DEF,
            'class': TokenType.CLASS,
            'structure': TokenType.STRUCTURE,
            'inductive': TokenType.INDUCTIVE,
            'variable': TokenType.VARIABLE,
            'where': TokenType.WHERE,
            'by': TokenType.BY,
            'private': TokenType.PRIVATE,
            'protected': TokenType.PROTECTED,
            'noncomputable': TokenType.NONCOMPUTABLE,
        }
        
        token_type = keyword_map.get(value, TokenType.IDENTIFIER)
        return Token(token_type, value, start_line, start_col)
    
    def read_attribute(self) -> Token:
        start_line, start_col = self.line, self.column
        self.advance()  # skip @
        self.advance()  # skip [
        
        bracket_depth = 1
        value = '@['
        
        while bracket_depth > 0 and self.position < len(self.content):
            char = self.peek()
            if char == '[':
                bracket_depth += 1
            elif char == ']':
                bracket_depth -= 1
            value = f"{value}{self.advance()}"
        
        return Token(TokenType.ATTRIBUTE, value, start_line, start_col)
    
    def next_token(self) -> Token:
        self.skip_whitespace()
        
        if self.position >= len(self.content):
            return Token(TokenType.EOF, '', self.line, self.column)
        
        _c = self.peek()
        char = _c if _c else ''
        
        # Handle two-character tokens
        if char == '-' and self.peek(1) == '-':
            return self.read_line_comment()
        elif char == '/' and self.peek(1) == '-':
            return self.read_block_comment()
        elif char == ':' and self.peek(1) == '=':
            line, col = self.line, self.column
            self.advance()
            self.advance()
            return Token(TokenType.ASSIGN, ':=', line, col)
        elif char == '@' and self.peek(1) == '[':
            return self.read_attribute()
        
        # Handle single-character tokens
        line, col = self.line, self.column
        
        if char == '(':
            self.advance()
            return Token(TokenType.LPAREN, '(', line, col)
        elif char == ')':
            self.advance()
            return Token(TokenType.RPAREN, ')', line, col)
        elif char == '[':
            self.advance()
            return Token(TokenType.LBRACKET, '[', line, col)
        elif char == ']':
            self.advance()
            return Token(TokenType.RBRACKET, ']', line, col)
        elif char == '{':
            self.advance()
            return Token(TokenType.LBRACE, '{', line, col)
        elif char == '}':
            self.advance()
            return Token(TokenType.RBRACE, '}', line, col)
        elif char == ':':
            self.advance()
            return Token(TokenType.COLON, ':', line, col)
        elif char == '\n':
            self.advance()
            return Token(TokenType.NEWLINE, '\n', line, col)
        elif char in list('"\''):
            return self.read_string()
        elif char and char.isalpha() or char in list('_αβγδεζηθικλμνξοπρστυφχψω'):
            return self.read_identifier()
        else:
            self.advance()
            return Token(TokenType.OTHER, char, line, col)

class Parser:
    def __init__(self, content: str, filename: str = ""):
        self.lexer = Lexer(content)
        self.filename = filename
        self.current_token = None
        self.peek_token = None
        self.advance()
        self.advance()
        
    def advance(self):
        self.current_token = self.peek_token
        self.peek_token = self.lexer.next_token()
        
    def parse(self) -> List[Definition]:
        definitions = []
        
        while self.current_token and self.current_token.type != TokenType.EOF:
            # Skip whitespace and regular comments
            if self.current_token.type in [TokenType.WHITESPACE, TokenType.NEWLINE, 
                                          TokenType.LINE_COMMENT, TokenType.BLOCK_COMMENT]:
                self.advance()
                continue
            
            # Check for definition start
            if self.current_token.type == TokenType.DOC_COMMENT or \
               self.current_token.type == TokenType.ATTRIBUTE or \
               self.current_token.type in [TokenType.PRIVATE, TokenType.PROTECTED, TokenType.NONCOMPUTABLE] or \
               self.current_token.type in [TokenType.LEMMA, TokenType.THEOREM, TokenType.DEF, 
                                         TokenType.CLASS, TokenType.STRUCTURE, TokenType.INDUCTIVE, 
                                         TokenType.VARIABLE]:
                defn = self.parse_definition()
                if defn:
                    definitions.append(defn)
            else:
                self.advance()
        
        return definitions
    
    def parse_definition(self) -> Optional[Definition]:
        defn = Definition(file=self.filename)
        
        # Parse doc comment if present
        if self.current_token and self.current_token.type == TokenType.DOC_COMMENT:
            defn.doc_comment = self.current_token.value
            defn.line = self.current_token.line
            self.advance()
            # Skip whitespace after doc comment
            while self.current_token.type in [TokenType.WHITESPACE, TokenType.NEWLINE]:
                self.advance()
        
        # Parse attributes
        while self.current_token and self.current_token.type == TokenType.ATTRIBUTE:
            defn.attributes.append(self.current_token.value)
            if defn.line == 0:
                defn.line = self.current_token.line
            self.advance()
            # Skip whitespace after attributes
            while self.current_token.type in [TokenType.WHITESPACE, TokenType.NEWLINE]:
                self.advance()
        
        # Parse modifiers
        while self.current_token and self.current_token.type in [TokenType.PRIVATE, TokenType.PROTECTED, TokenType.NONCOMPUTABLE]:
            defn.modifiers.append(self.current_token.value)
            if defn.line == 0:
                defn.line = self.current_token.line
            self.advance()
            # Skip whitespace after modifiers
            while self.current_token.type == TokenType.WHITESPACE:
                self.advance()
        
        # Parse definition type
        if self.current_token and self.current_token.type not in [TokenType.LEMMA, TokenType.THEOREM, TokenType.DEF, 
                                          TokenType.CLASS, TokenType.STRUCTURE, TokenType.INDUCTIVE, 
                                          TokenType.VARIABLE]:
            return None
        
        defn.def_type = self.current_token.value if self.current_token else '' 

        if defn.line == 0:
            defn.line = self.current_token.line if self.current_token and self.current_token.line else 0
        self.advance()
        
        # Skip whitespace
        while self.current_token and self.current_token.type == TokenType.WHITESPACE:
            self.advance()
        
        # Parse name
        if self.current_token and self.current_token.type != TokenType.IDENTIFIER:
            return None
        
        defn.name = self.current_token.value if self.current_token and self.current_token.value else '' 
        self.advance()
        
        # Parse signature (everything until := or where or by)
        signature_tokens = []
        bracket_stack = []
        
        while self.current_token and self.current_token.type != TokenType.EOF:
            # Check for end of signature
            if not bracket_stack:  # Only at top level
                if self.current_token.type == TokenType.ASSIGN:
                    break
                if self.current_token.type == TokenType.WHERE:
                    break
                if self.current_token.type == TokenType.BY:
                    break
                # For variables, newline can end the definition
                if defn.def_type == 'variable' and self.current_token.type == TokenType.NEWLINE:
                    break
            
            # Track brackets
            if self.current_token.type in [TokenType.LPAREN, TokenType.LBRACKET, TokenType.LBRACE]:
                bracket_stack.append(self.current_token.type)
            elif self.current_token.type == TokenType.RPAREN and bracket_stack and bracket_stack[-1] == TokenType.LPAREN:
                bracket_stack.pop()
            elif self.current_token.type == TokenType.RBRACKET and bracket_stack and bracket_stack[-1] == TokenType.LBRACKET:
                bracket_stack.pop()
            elif self.current_token.type == TokenType.RBRACE and bracket_stack and bracket_stack[-1] == TokenType.LBRACE:
                bracket_stack.pop()
            
            signature_tokens.append(self.current_token.value)
            self.advance()
        
        defn.signature = ''.join(signature_tokens).strip()
        
        return defn

def parse_lean_files(directory: str) -> List[Dict]:
    """Parse all .lean files recursively."""
    results = []
    
    for lean_file in Path(directory).rglob("*.lean"):
        try:
            with open(lean_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            parser = Parser(content, str(lean_file))
            definitions = parser.parse()
            
            for defn in definitions:
                # Build the full definition text
                full_text = ""
                if defn.doc_comment:
                    full_text += defn.doc_comment + "\n"
                if defn.attributes:
                    full_text += ' '.join(defn.attributes) + ' '
                if defn.modifiers:
                    full_text += ' '.join(defn.modifiers) + ' '
                full_text += defn.def_type + ' ' + defn.name
                if defn.signature:
                    full_text += defn.signature
                
                results.append({
                    "full_definition": full_text.strip(),
                    "doc_comment": defn.doc_comment,
                    "attributes": defn.attributes,
                    "modifiers": defn.modifiers,
                    "definition_type": defn.def_type,
                    "name": defn.name,
                    "signature": defn.signature,
                    "file": defn.file,
                    "line": defn.line
                })
                
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