"""Error hierarchy for the Haxor language runtime and tooling."""


class HaxorError(Exception):
    def __init__(self, message, line=0, col=0):
        super().__init__(message)
        self.line = line
        self.col = col

    def __str__(self):
        loc = f" [line {self.line}:{self.col}]" if self.line else ""
        return f"{type(self).__name__}{loc}: {self.args[0]}"


class LexError(HaxorError): pass
class ParseError(HaxorError): pass
class HaxorRuntimeError(HaxorError): pass
class HaxorTypeError(HaxorError): pass
class HaxorNameError(HaxorError): pass
class VerificationError(HaxorError): pass
class HaxorImportError(HaxorError): pass
class PluginError(HaxorError): pass
class HaxorAttributeError(HaxorError): pass
class HaxorIndexError(HaxorError): pass
class HaxorKeyError(HaxorError): pass
class HaxorStopIteration(HaxorError): pass


# Control-flow signals — not real errors
class _Return(Exception):
    def __init__(self, value): self.value = value

class _Break(Exception): pass
class _Continue(Exception): pass
