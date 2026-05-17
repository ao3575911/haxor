"""Tests for the Haxor static verifier (all three analysis passes)."""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import haxor
from haxor.verifier import Verifier, Severity, Diagnostic


def verify(src, strict=False):
    tree = haxor.parse(src)
    return Verifier(strict=strict).verify(tree)


def has_severity(diags, sev):
    return any(d.severity == sev for d in diags)


def errors(diags):
    return [d for d in diags if d.severity == Severity.ERROR]


def warnings(diags):
    return [d for d in diags if d.severity == Severity.WARNING]


# ── Type inference ────────────────────────────────────────────────────────────

class TestTypeInference:
    def test_no_issues_simple(self):
        diags = verify("let x = 42")
        assert not errors(diags)

    def test_type_mismatch_warning(self):
        diags = verify("let x: int = 'hello'")
        assert has_severity(diags, Severity.WARNING)

    def test_type_mismatch_float(self):
        diags = verify("let x: int = 3.14")
        assert has_severity(diags, Severity.WARNING)

    def test_compatible_types(self):
        diags = verify("let x: int = 42")
        # No mismatch warning
        type_warnings = [d for d in warnings(diags) if 'mismatch' in d.message.lower()]
        assert not type_warnings

    def test_undefined_variable_warning(self):
        # Without let — variable appears undefined at that point
        diags = verify("let r = undefined_name")
        assert has_severity(diags, Severity.WARNING)
        assert any('undefined_name' in d.message for d in diags)

    def test_fn_annotated_params(self):
        src = "fn add(a: int, b: int) -> int:\n    return a + b\n"
        diags = verify(src)
        assert not errors(diags)

    def test_class_defined(self):
        src = "class Foo:\n    pass\n"
        diags = verify(src)
        assert not errors(diags)


# ── Sign analysis ─────────────────────────────────────────────────────────────

class TestSignAnalysis:
    def test_div_by_zero_constant(self):
        diags = verify("let r = 5 / 0")
        err = [d for d in diags if 'division by zero' in d.message.lower()]
        assert err, "Expected division-by-zero error"

    def test_div_by_nonzero_ok(self):
        diags = verify("let r = 10 / 2")
        div_errs = [d for d in diags if 'division' in d.message.lower()]
        assert not div_errs

    def test_div_by_unknown(self):
        # When divisor is unknown, no static error (conservative)
        diags = verify("fn f(x):\n    return 10 / x\n")
        div_errs = [d for d in diags if 'division' in d.message.lower()]
        # Should not produce error when divisor is unknown
        assert not div_errs

    def test_sign_propagation(self):
        # x = 5 (pos), y = x (pos), z = y / 2 — no div by zero
        diags = verify("let x = 5\nlet y = x\nlet z = y / 2\n")
        div_errs = [d for d in diags if 'division' in d.message.lower()]
        assert not div_errs

    def test_floordiv_by_zero(self):
        diags = verify("let r = 10 // 0")
        err = [d for d in diags if 'division by zero' in d.message.lower()]
        assert err


# ── Control flow analysis ─────────────────────────────────────────────────────

class TestControlFlowAnalysis:
    def test_always_returns(self):
        src = "fn f(x) -> int:\n    return x + 1\n"
        diags = verify(src)
        ret_warns = [d for d in diags if 'return' in d.message.lower()]
        assert not ret_warns

    def test_missing_return_warning(self):
        src = "fn f(x) -> int:\n    x + 1\n"
        diags = verify(src)
        ret_warns = [d for d in diags if 'return' in d.message.lower()]
        assert ret_warns

    def test_if_else_returns(self):
        src = "fn sign(x) -> int:\n    if x > 0:\n        return 1\n    else:\n        return -1\n"
        diags = verify(src)
        ret_warns = [d for d in diags if 'return' in d.message.lower()]
        assert not ret_warns

    def test_if_without_else_missing_return(self):
        src = "fn f(x) -> int:\n    if x > 0:\n        return x\n"
        diags = verify(src)
        ret_warns = [d for d in diags if 'return' in d.message.lower()]
        assert ret_warns

    def test_no_return_annotation_no_warning(self):
        src = "fn f(x):\n    x + 1\n"
        diags = verify(src)
        ret_warns = [d for d in diags if 'return' in d.message.lower()]
        assert not ret_warns


# ── Strict mode ───────────────────────────────────────────────────────────────

class TestStrictMode:
    def test_strict_raises_on_error(self):
        from haxor.errors import VerificationError
        with pytest.raises(VerificationError):
            verify("let r = 5 / 0", strict=True)

    def test_strict_ok_on_clean_code(self):
        diags = verify("let x: int = 42", strict=True)
        # Should not raise
        assert not errors(diags)


# ── Diagnostic structure ──────────────────────────────────────────────────────

class TestDiagnosticStructure:
    def test_diagnostic_has_location(self):
        diags = verify("let r = 5 / 0")
        err = errors(diags)
        assert err
        assert err[0].line > 0 or err[0].col >= 0

    def test_diagnostic_str(self):
        d = Diagnostic(Severity.WARNING, "test warning", line=3, col=5, pass_name="test")
        s = str(d)
        assert 'WARNING' in s
        assert 'test warning' in s

    def test_pass_name_recorded(self):
        diags = verify("let r = 5 / 0")
        err = errors(diags)
        assert err[0].pass_name in ('sign', 'type', 'flow', '')
