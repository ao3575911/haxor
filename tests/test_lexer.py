"""Tests for the Haxor lexer."""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from haxor.lexer import Lexer, TT, Token
from haxor.errors import LexError


def tokenize(src):
    return Lexer(src).tokenize()


def types(src):
    return [t.type for t in tokenize(src) if t.type not in (TT.NEWLINE, TT.EOF)]


def values(src):
    toks = [t for t in tokenize(src) if t.type not in (TT.NEWLINE, TT.EOF)]
    return [(t.type, t.value) for t in toks]


# ── Literals ──────────────────────────────────────────────────────────────────

class TestLiterals:
    def test_integer(self):
        assert values("42") == [(TT.INT, 42)]

    def test_negative_integer(self):
        assert values("-1") == [(TT.MINUS, '-'), (TT.INT, 1)]

    def test_float(self):
        assert values("3.14") == [(TT.FLOAT, 3.14)]

    def test_scientific(self):
        toks = values("1e10")
        assert toks == [(TT.FLOAT, 1e10)]

    def test_hex(self):
        assert values("0xFF") == [(TT.INT, 255)]

    def test_binary(self):
        assert values("0b1010") == [(TT.INT, 10)]

    def test_underscore_number(self):
        assert values("1_000_000") == [(TT.INT, 1000000)]

    def test_string_double(self):
        assert values('"hello"') == [(TT.STRING, 'hello')]

    def test_string_single(self):
        assert values("'world'") == [(TT.STRING, 'world')]

    def test_string_escape(self):
        assert values(r'"line\nend"') == [(TT.STRING, 'line\nend')]

    def test_fstring(self):
        toks = [t for t in tokenize('f"hi {name}"') if t.type not in (TT.NEWLINE, TT.EOF)]
        assert toks[0].type == TT.FSTRING
        assert toks[0].value == 'hi {name}'

    def test_true_false_none(self):
        assert types("True False None") == [TT.TRUE, TT.FALSE, TT.NONE]


# ── Keywords ──────────────────────────────────────────────────────────────────

class TestKeywords:
    def test_let(self):
        assert types("let") == [TT.LET]

    def test_fn(self):
        assert types("fn") == [TT.FN]

    def test_class(self):
        assert types("class") == [TT.CLASS]

    def test_control_flow(self):
        assert types("if elif else for while") == [
            TT.IF, TT.ELIF, TT.ELSE, TT.FOR, TT.WHILE]

    def test_return_break_continue(self):
        assert types("return break continue") == [TT.RETURN, TT.BREAK, TT.CONTINUE]

    def test_import(self):
        assert types("import from") == [TT.IMPORT, TT.FROM]

    def test_logical(self):
        assert types("and or not") == [TT.AND, TT.OR, TT.NOT]

    def test_in_is(self):
        assert types("in is") == [TT.IN, TT.IS]


# ── Operators ─────────────────────────────────────────────────────────────────

class TestOperators:
    def test_arithmetic(self):
        assert types("+ - * / // % **") == [
            TT.PLUS, TT.MINUS, TT.STAR, TT.SLASH,
            TT.DOUBLESLASH, TT.PERCENT, TT.DSTAR]

    def test_comparison(self):
        assert types("== != < > <= >=") == [
            TT.EQEQ, TT.NEQ, TT.LT, TT.GT, TT.LEQ, TT.GEQ]

    def test_augmented(self):
        assert types("+= -= *= /=") == [
            TT.PLUSEQ, TT.MINUSEQ, TT.STAREQ, TT.SLASHEQ]

    def test_arrow(self):
        assert types("->") == [TT.ARROW]

    def test_at(self):
        assert types("@") == [TT.AT]


# ── Delimiters ────────────────────────────────────────────────────────────────

class TestDelimiters:
    def test_parens(self):
        assert types("()") == [TT.LPAREN, TT.RPAREN]

    def test_brackets(self):
        assert types("[]") == [TT.LBRACKET, TT.RBRACKET]

    def test_braces(self):
        assert types("{}") == [TT.LBRACE, TT.RBRACE]

    def test_comma_colon_dot(self):
        assert types(", : .") == [TT.COMMA, TT.COLON, TT.DOT]


# ── Indentation ───────────────────────────────────────────────────────────────

class TestIndentation:
    def test_indent_dedent(self):
        src = "if True:\n    x = 1\ny = 2\n"
        tts = [t.type for t in tokenize(src)]
        assert TT.INDENT in tts
        assert TT.DEDENT in tts

    def test_no_indent_on_flat(self):
        src = "x = 1\ny = 2\n"
        tts = [t.type for t in tokenize(src)]
        assert TT.INDENT not in tts
        assert TT.DEDENT not in tts

    def test_nested_indent(self):
        src = "if True:\n    if True:\n        x = 1\n"
        tts = [t.type for t in tokenize(src)]
        assert tts.count(TT.INDENT) == 2
        assert tts.count(TT.DEDENT) == 2

    def test_bracket_suppresses_indent(self):
        src = "x = (\n    1 +\n    2\n)\n"
        tts = [t.type for t in tokenize(src)]
        assert TT.INDENT not in tts


# ── Comments ──────────────────────────────────────────────────────────────────

class TestComments:
    def test_comment_ignored(self):
        assert types("x = 1  # this is a comment") == [TT.NAME, TT.EQ, TT.INT]

    def test_full_comment_line(self):
        src = "# full line\nx = 1"
        tts = [t.type for t in tokenize(src) if t.type not in (TT.NEWLINE, TT.EOF)]
        assert tts == [TT.NAME, TT.EQ, TT.INT]


# ── Error cases ───────────────────────────────────────────────────────────────

class TestErrors:
    def test_unterminated_string(self):
        with pytest.raises(LexError):
            tokenize('"unterminated')

    def test_unexpected_char(self):
        with pytest.raises(LexError):
            tokenize('x = 1 ! 2')
