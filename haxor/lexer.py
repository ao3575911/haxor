"""Haxor lexer — converts source text into a flat token stream.

Indentation handling mirrors CPython's tokenize module:
- An indent stack tracks current levels.
- On each logical-line start, INDENT/DEDENT tokens are emitted.
- Implicit line continuation inside brackets suppresses NEWLINE/INDENT/DEDENT.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, List
from .errors import LexError


class TT(Enum):
    # Literals
    INT = auto(); FLOAT = auto(); STRING = auto(); FSTRING = auto()
    TRUE = auto(); FALSE = auto(); NONE = auto()
    # Names / keywords
    NAME = auto()
    LET = auto(); FN = auto(); CLASS = auto()
    IF = auto(); ELIF = auto(); ELSE = auto()
    FOR = auto(); WHILE = auto()
    RETURN = auto(); BREAK = auto(); CONTINUE = auto(); PASS = auto()
    IMPORT = auto(); FROM = auto()
    AND = auto(); OR = auto(); NOT = auto()
    IN = auto(); IS = auto()
    LAMBDA = auto(); ASSERT = auto()
    # Operators
    PLUS = auto(); MINUS = auto(); STAR = auto(); SLASH = auto()
    DOUBLESLASH = auto(); PERCENT = auto(); DSTAR = auto()
    EQ = auto(); EQEQ = auto(); NEQ = auto()
    LT = auto(); GT = auto(); LEQ = auto(); GEQ = auto()
    PLUSEQ = auto(); MINUSEQ = auto(); STAREQ = auto(); SLASHEQ = auto()
    PERCENTEQ = auto(); DSTAREQ = auto()
    ARROW = auto(); AT = auto(); TILDE = auto()
    AMP = auto(); PIPE = auto(); CARET = auto()
    LSHIFT = auto(); RSHIFT = auto()
    # Delimiters
    LPAREN = auto(); RPAREN = auto()
    LBRACKET = auto(); RBRACKET = auto()
    LBRACE = auto(); RBRACE = auto()
    COMMA = auto(); COLON = auto(); DOT = auto(); SEMICOLON = auto()
    ELLIPSIS = auto()
    # Structure
    NEWLINE = auto(); INDENT = auto(); DEDENT = auto(); EOF = auto()


KEYWORDS: dict[str, TT] = {
    "let": TT.LET, "fn": TT.FN, "class": TT.CLASS,
    "if": TT.IF, "elif": TT.ELIF, "else": TT.ELSE,
    "for": TT.FOR, "while": TT.WHILE,
    "return": TT.RETURN, "break": TT.BREAK, "continue": TT.CONTINUE,
    "pass": TT.PASS, "import": TT.IMPORT, "from": TT.FROM,
    "and": TT.AND, "or": TT.OR, "not": TT.NOT,
    "in": TT.IN, "is": TT.IS,
    "True": TT.TRUE, "False": TT.FALSE, "None": TT.NONE,
    "lambda": TT.LAMBDA, "assert": TT.ASSERT,
}


@dataclass
class Token:
    type: TT
    value: Any
    line: int
    col: int

    def __repr__(self) -> str:
        return f"Token({self.type.name}, {self.value!r}, {self.line}:{self.col})"


class Lexer:
    def __init__(self, source: str):
        self.src = source
        self.pos = 0
        self.line = 1
        self.col = 1
        self.tokens: List[Token] = []
        self.indent_stack: List[int] = [0]
        self.bracket_depth = 0

    # ── Public API ────────────────────────────────────────────────────────────

    def tokenize(self) -> List[Token]:
        self._handle_line_start()
        while self.pos < len(self.src):
            self._scan()
        # Flush remaining DEDENTs before EOF
        if self.bracket_depth == 0:
            self._emit_newline_if_needed()
            while len(self.indent_stack) > 1:
                self.indent_stack.pop()
                self._add(TT.DEDENT, None)
        self._add(TT.EOF, None)
        return self.tokens

    # ── Internal scanners ─────────────────────────────────────────────────────

    def _scan(self) -> None:
        ch = self._peek()
        if ch == '\n':
            self._newline()
        elif ch in ' \t':
            self._advance()
        elif ch == '#':
            while self.pos < len(self.src) and self._peek() != '\n':
                self._advance()
        elif ch == '\\' and self._peek(1) == '\n':
            # Explicit line continuation
            self._advance(); self._advance()
            self.line += 1; self.col = 1
        elif ch in ('"', "'"):
            self._string()
        elif ch == 'f' and self._peek(1) in ('"', "'"):
            self._fstring()
        elif ch == 'r' and self._peek(1) in ('"', "'"):
            self._advance()  # consume r
            self._string(raw=True)
        elif ch.isdigit() or (ch == '.' and self._peek(1).isdigit()):
            self._number()
        elif ch.isalpha() or ch == '_':
            self._name()
        else:
            self._operator()

    def _newline(self) -> None:
        self._advance()
        self.line += 1
        self.col = 1
        if self.bracket_depth > 0:
            return
        self._emit_newline_if_needed()
        # Skip blank / comment-only lines before handling indent
        while self.pos < len(self.src):
            if self.src[self.pos] == '\n':
                self.pos += 1; self.line += 1; self.col = 1
            elif self.src[self.pos] == '#':
                while self.pos < len(self.src) and self.src[self.pos] != '\n':
                    self.pos += 1
            else:
                break
        if self.pos < len(self.src):
            self._handle_line_start()

    def _emit_newline_if_needed(self) -> None:
        if self.tokens and self.tokens[-1].type not in (
            TT.NEWLINE, TT.INDENT, TT.DEDENT, TT.EOF
        ):
            self._add(TT.NEWLINE, '\n')

    def _handle_line_start(self) -> None:
        """Count leading whitespace and emit INDENT/DEDENT tokens."""
        indent = 0
        start_pos = self.pos
        while self.pos < len(self.src) and self.src[self.pos] in (' ', '\t'):
            indent += 1 if self.src[self.pos] == ' ' else 4
            self.pos += 1
            self.col += 1
        if self.pos >= len(self.src) or self.src[self.pos] in ('\n', '#'):
            self.pos = start_pos
            self.col = 1
            return  # blank line
        current = self.indent_stack[-1]
        if indent > current:
            self.indent_stack.append(indent)
            self._add(TT.INDENT, indent)
        elif indent < current:
            while self.indent_stack[-1] > indent:
                self.indent_stack.pop()
                self._add(TT.DEDENT, indent)
            if self.indent_stack[-1] != indent:
                raise LexError(
                    f"Inconsistent indentation (expected {self.indent_stack[-1]}, got {indent})",
                    self.line, self.col
                )

    def _string(self, raw: bool = False) -> None:
        quote = self._advance()
        triple = self._src[self.pos:self.pos + 2] == quote * 2
        if triple:
            self._advance(); self._advance()
            end = quote * 3
        else:
            end = quote
        buf = []
        while self.pos < len(self.src):
            if self.src[self.pos:self.pos + len(end)] == end:
                for _ in end:
                    self._advance()
                self._add(TT.STRING, ''.join(buf))
                return
            ch = self._advance()
            if ch == '\\' and not raw:
                esc = self._advance()
                buf.append({'n': '\n', 't': '\t', 'r': '\r', '\\': '\\',
                            '"': '"', "'": "'", '0': '\0'}.get(esc, '\\' + esc))
            else:
                if ch == '\n':
                    self.line += 1; self.col = 1
                buf.append(ch)
        raise LexError("Unterminated string literal", self.line, self.col)

    def _fstring(self) -> None:
        self._advance()  # consume 'f'
        quote = self._advance()
        triple = self.src[self.pos:self.pos + 2] == quote * 2
        if triple:
            self._advance(); self._advance()
            end = quote * 3
        else:
            end = quote
        buf = []
        while self.pos < len(self.src):
            if self.src[self.pos:self.pos + len(end)] == end:
                for _ in end:
                    self._advance()
                self._add(TT.FSTRING, ''.join(buf))
                return
            ch = self._advance()
            if ch == '\\':
                esc = self._advance()
                buf.append({'n': '\n', 't': '\t', 'r': '\r', '\\': '\\',
                            '"': '"', "'": "'"}.get(esc, '\\' + esc))
            else:
                if ch == '\n':
                    self.line += 1; self.col = 1
                buf.append(ch)
        raise LexError("Unterminated f-string", self.line, self.col)

    def _number(self) -> None:
        start = self.pos
        is_float = False
        if self.src[self.pos:self.pos + 2] in ('0x', '0X'):
            self._advance(); self._advance()
            while self.pos < len(self.src) and self.src[self.pos] in '0123456789abcdefABCDEF_':
                self._advance()
            self._add(TT.INT, int(self.src[start:self.pos].replace('_', ''), 16))
            return
        if self.src[self.pos:self.pos + 2] in ('0b', '0B'):
            self._advance(); self._advance()
            while self.pos < len(self.src) and self.src[self.pos] in '01_':
                self._advance()
            self._add(TT.INT, int(self.src[start:self.pos].replace('_', ''), 2))
            return
        while self.pos < len(self.src) and (self.src[self.pos].isdigit() or self.src[self.pos] == '_'):
            self._advance()
        if self.pos < len(self.src) and self.src[self.pos] == '.':
            is_float = True
            self._advance()
            while self.pos < len(self.src) and (self.src[self.pos].isdigit() or self.src[self.pos] == '_'):
                self._advance()
        if self.pos < len(self.src) and self.src[self.pos] in ('e', 'E'):
            is_float = True
            self._advance()
            if self.pos < len(self.src) and self.src[self.pos] in ('+', '-'):
                self._advance()
            while self.pos < len(self.src) and self.src[self.pos].isdigit():
                self._advance()
        raw = self.src[start:self.pos].replace('_', '')
        if is_float:
            self._add(TT.FLOAT, float(raw))
        else:
            self._add(TT.INT, int(raw))

    def _name(self) -> None:
        start = self.pos
        while self.pos < len(self.src) and (self.src[self.pos].isalnum() or self.src[self.pos] == '_'):
            self._advance()
        word = self.src[start:self.pos]
        tt = KEYWORDS.get(word, TT.NAME)
        self._add(tt, word)

    def _operator(self) -> None:  # noqa: C901
        ch = self._advance()
        nxt = self._peek()
        line, col = self.line, self.col - 1

        def two(c2: str, tt2: TT, tt1: TT) -> TT:
            if nxt == c2:
                self._advance()
                return tt2
            return tt1

        m: dict[str, TT] = {}
        if ch == '+':
            tt = two('=', TT.PLUSEQ, TT.PLUS)
        elif ch == '-':
            if nxt == '>':
                self._advance(); tt = TT.ARROW
            elif nxt == '=':
                self._advance(); tt = TT.MINUSEQ
            else:
                tt = TT.MINUS
        elif ch == '*':
            if nxt == '*':
                self._advance()
                tt = TT.DSTAREQ if self._peek() == '=' and self._advance() else TT.DSTAR
            elif nxt == '=':
                self._advance(); tt = TT.STAREQ
            else:
                tt = TT.STAR
        elif ch == '/':
            if nxt == '/':
                self._advance(); tt = TT.DOUBLESLASH
            elif nxt == '=':
                self._advance(); tt = TT.SLASHEQ
            else:
                tt = TT.SLASH
        elif ch == '%':
            tt = two('=', TT.PERCENTEQ, TT.PERCENT)
        elif ch == '=':
            tt = two('=', TT.EQEQ, TT.EQ)
        elif ch == '!':
            if nxt == '=':
                self._advance(); tt = TT.NEQ
            else:
                raise LexError(f"Unexpected character '!'", line, col)
        elif ch == '<':
            if nxt == '=':
                self._advance(); tt = TT.LEQ
            elif nxt == '<':
                self._advance(); tt = TT.LSHIFT
            else:
                tt = TT.LT
        elif ch == '>':
            if nxt == '=':
                self._advance(); tt = TT.GEQ
            elif nxt == '>':
                self._advance(); tt = TT.RSHIFT
            else:
                tt = TT.GT
        elif ch == '(':
            self.bracket_depth += 1; tt = TT.LPAREN
        elif ch == ')':
            self.bracket_depth -= 1; tt = TT.RPAREN
        elif ch == '[':
            self.bracket_depth += 1; tt = TT.LBRACKET
        elif ch == ']':
            self.bracket_depth -= 1; tt = TT.RBRACKET
        elif ch == '{':
            self.bracket_depth += 1; tt = TT.LBRACE
        elif ch == '}':
            self.bracket_depth -= 1; tt = TT.RBRACE
        elif ch == ',':
            tt = TT.COMMA
        elif ch == ':':
            tt = TT.COLON
        elif ch == '.':
            if self.src[self.pos:self.pos + 2] == '..':
                self._advance(); self._advance(); tt = TT.ELLIPSIS
            else:
                tt = TT.DOT
        elif ch == ';':
            tt = TT.SEMICOLON
        elif ch == '@':
            tt = TT.AT
        elif ch == '~':
            tt = TT.TILDE
        elif ch == '&':
            tt = TT.AMP
        elif ch == '|':
            tt = TT.PIPE
        elif ch == '^':
            tt = TT.CARET
        else:
            raise LexError(f"Unexpected character {ch!r}", line, col)
        self.tokens.append(Token(tt, ch, line, col))

    # ── Helpers ───────────────────────────────────────────────────────────────

    @property
    def _src(self) -> str:
        return self.src

    def _peek(self, offset: int = 0) -> str:
        idx = self.pos + offset
        return self.src[idx] if idx < len(self.src) else ''

    def _advance(self) -> str:
        ch = self.src[self.pos]
        self.pos += 1
        self.col += 1
        return ch

    def _add(self, tt: TT, value: Any) -> None:
        self.tokens.append(Token(tt, value, self.line, self.col))
