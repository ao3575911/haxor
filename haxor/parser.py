"""Haxor recursive-descent parser.

Operator precedence (low → high):
  lambda
  if-else (ternary)
  or
  and
  not
  in / not in / is / is not / < <= > >= == !=
  | (bitwise or)
  ^ (bitwise xor)
  & (bitwise and)
  << >>
  + -
  * / // % @
  +x -x ~x (unary)
  **
  await
  x[i] x[a:b] x(…) x.attr
  (expr,) [list] {dict/set} 'string' number name
"""
from __future__ import annotations
from typing import List, Optional, Tuple
from .lexer import Token, TT
from .ast_nodes import *
from .errors import ParseError


class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = [t for t in tokens if t.type not in (TT.SEMICOLON,)]
        self.pos = 0

    # ── Public API ────────────────────────────────────────────────────────────

    def parse(self) -> Program:
        body = self._block_until(TT.EOF)
        self._expect(TT.EOF)
        return Program(body=body, line=1, col=1)

    def parse_expression(self) -> Node:
        """Parse a single expression (used by f-string sub-parser)."""
        return self._expr()

    # ── Token management ──────────────────────────────────────────────────────

    def _cur(self) -> Token:
        return self.tokens[self.pos]

    def _peek(self, offset: int = 1) -> Token:
        idx = self.pos + offset
        return self.tokens[idx] if idx < len(self.tokens) else self.tokens[-1]

    def _at(self, *types: TT) -> bool:
        return self._cur().type in types

    def _advance(self) -> Token:
        t = self.tokens[self.pos]
        if self.pos < len(self.tokens) - 1:
            self.pos += 1
        return t

    def _expect(self, tt: TT) -> Token:
        if not self._at(tt):
            cur = self._cur()
            raise ParseError(
                f"Expected {tt.name}, got {cur.type.name} ({cur.value!r})",
                cur.line, cur.col,
            )
        return self._advance()

    def _skip_newlines(self) -> None:
        while self._at(TT.NEWLINE):
            self._advance()

    # ── Block / statement parsing ─────────────────────────────────────────────

    def _block_until(self, *end_types: TT) -> List[Node]:
        stmts: List[Node] = []
        self._skip_newlines()
        while not self._at(*end_types):
            stmt = self._statement()
            if stmt is not None:
                stmts.append(stmt)
            self._skip_newlines()
        return stmts

    def _indented_block(self) -> List[Node]:
        self._expect(TT.COLON)
        self._skip_newlines()
        self._expect(TT.INDENT)
        body = self._block_until(TT.DEDENT, TT.EOF)
        if self._at(TT.DEDENT):
            self._advance()
        return body

    def _statement(self) -> Optional[Node]:  # noqa: C901
        cur = self._cur()
        tt = cur.type

        if tt == TT.NEWLINE:
            self._advance()
            return None
        if tt == TT.PASS:
            self._advance()
            self._eat_newline()
            return PassStmt(line=cur.line, col=cur.col)
        if tt == TT.LET:
            return self._let_stmt()
        if tt == TT.FN:
            return self._fn_def(decorators=[])
        if tt == TT.CLASS:
            return self._class_def(decorators=[])
        if tt == TT.AT:
            return self._decorated()
        if tt == TT.IF:
            return self._if_stmt()
        if tt == TT.FOR:
            return self._for_stmt()
        if tt == TT.WHILE:
            return self._while_stmt()
        if tt == TT.RETURN:
            return self._return_stmt()
        if tt == TT.BREAK:
            self._advance(); self._eat_newline()
            return BreakStmt(line=cur.line, col=cur.col)
        if tt == TT.CONTINUE:
            self._advance(); self._eat_newline()
            return ContinueStmt(line=cur.line, col=cur.col)
        if tt == TT.IMPORT:
            return self._import_stmt()
        if tt == TT.FROM:
            return self._from_import_stmt()
        if tt == TT.ASSERT:
            return self._assert_stmt()
        return self._expr_stmt()

    def _eat_newline(self) -> None:
        if self._at(TT.NEWLINE):
            self._advance()

    # ── Statement parsers ─────────────────────────────────────────────────────

    def _let_stmt(self) -> LetStmt:
        tok = self._expect(TT.LET)
        name_tok = self._expect(TT.NAME)
        annotation = None
        if self._at(TT.COLON):
            self._advance()
            annotation = self._expect(TT.NAME).value
        self._expect(TT.EQ)
        value = self._expr()
        self._eat_newline()
        return LetStmt(name=name_tok.value, annotation=annotation, value=value,
                       line=tok.line, col=tok.col)

    def _fn_def(self, decorators: List[Node]) -> FnDef:
        tok = self._expect(TT.FN)
        name = self._expect(TT.NAME).value
        self._expect(TT.LPAREN)
        params, defaults = self._param_list()
        self._expect(TT.RPAREN)
        return_type = None
        if self._at(TT.ARROW):
            self._advance()
            return_type = self._expect(TT.NAME).value
        body = self._indented_block()
        return FnDef(name=name, params=params, return_type=return_type,
                     body=body, decorators=decorators, defaults=defaults,
                     line=tok.line, col=tok.col)

    def _param_list(self) -> Tuple[List[Tuple[str, Optional[str]]], dict]:
        params: List[Tuple[str, Optional[str]]] = []
        defaults: dict = {}
        while not self._at(TT.RPAREN, TT.EOF):
            pname = self._expect(TT.NAME).value
            ann = None
            if self._at(TT.COLON):
                self._advance()
                ann = self._expect(TT.NAME).value
            params.append((pname, ann))
            if self._at(TT.EQ):
                self._advance()
                defaults[pname] = self._expr()
            if not self._at(TT.COMMA):
                break
            self._advance()
        return params, defaults

    def _class_def(self, decorators: List[Node]) -> ClassDef:
        tok = self._expect(TT.CLASS)
        name = self._expect(TT.NAME).value
        bases: List[str] = []
        if self._at(TT.LPAREN):
            self._advance()
            while not self._at(TT.RPAREN, TT.EOF):
                bases.append(self._expect(TT.NAME).value)
                if not self._at(TT.COMMA):
                    break
                self._advance()
            self._expect(TT.RPAREN)
        body = self._indented_block()
        return ClassDef(name=name, bases=bases, body=body,
                        decorators=decorators, line=tok.line, col=tok.col)

    def _decorated(self) -> Node:
        decorators: List[Node] = []
        while self._at(TT.AT):
            at_tok = self._advance()
            name = self._expect(TT.NAME).value
            if name == 'verify':
                dec = self._verify_decorator(at_tok)
            else:
                # Generic decorator: @name or @name(args)
                node: Node = Name(id=name, line=at_tok.line, col=at_tok.col)
                if self._at(TT.LPAREN):
                    args, kwargs = self._call_args()
                    node = Call(func=node, args=args, kwargs=kwargs,
                                line=at_tok.line, col=at_tok.col)
                dec = node
            decorators.append(dec)
            self._eat_newline()
        self._skip_newlines()
        if self._at(TT.FN):
            return self._fn_def(decorators)
        if self._at(TT.CLASS):
            return self._class_def(decorators)
        raise ParseError("Expected 'fn' or 'class' after decorator",
                         self._cur().line, self._cur().col)

    def _verify_decorator(self, at_tok: Token) -> VerifyDecorator:
        self._expect(TT.LPAREN)
        pre = post = invariant = None
        while not self._at(TT.RPAREN, TT.EOF):
            key = self._expect(TT.NAME).value
            self._expect(TT.EQ)
            val_tok = self._cur()
            if val_tok.type != TT.STRING:
                raise ParseError("@verify arguments must be string literals",
                                 val_tok.line, val_tok.col)
            self._advance()
            if key == 'pre':
                pre = val_tok.value
            elif key == 'post':
                post = val_tok.value
            elif key == 'invariant':
                invariant = val_tok.value
            else:
                raise ParseError(f"Unknown @verify key: {key!r}",
                                 val_tok.line, val_tok.col)
            if not self._at(TT.COMMA):
                break
            self._advance()
        self._expect(TT.RPAREN)
        return VerifyDecorator(pre=pre, post=post, invariant=invariant,
                               line=at_tok.line, col=at_tok.col)

    def _if_stmt(self) -> IfStmt:
        tok = self._expect(TT.IF)
        cond = self._expr()
        body = self._indented_block()
        elif_clauses: List[Tuple[Node, List[Node]]] = []
        else_body = None
        self._skip_newlines()
        while self._at(TT.ELIF):
            self._advance()
            ec = self._expr()
            eb = self._indented_block()
            elif_clauses.append((ec, eb))
            self._skip_newlines()
        if self._at(TT.ELSE):
            self._advance()
            else_body = self._indented_block()
        return IfStmt(condition=cond, then_body=body, elif_clauses=elif_clauses,
                      else_body=else_body, line=tok.line, col=tok.col)

    def _for_stmt(self) -> ForStmt:
        tok = self._expect(TT.FOR)
        target = self._expect(TT.NAME).value
        self._expect(TT.IN)
        iterable = self._expr()
        body = self._indented_block()
        return ForStmt(target=target, iterable=iterable, body=body,
                       line=tok.line, col=tok.col)

    def _while_stmt(self) -> WhileStmt:
        tok = self._expect(TT.WHILE)
        cond = self._expr()
        body = self._indented_block()
        return WhileStmt(condition=cond, body=body, line=tok.line, col=tok.col)

    def _return_stmt(self) -> ReturnStmt:
        tok = self._expect(TT.RETURN)
        value = None
        if not self._at(TT.NEWLINE, TT.EOF, TT.DEDENT):
            value = self._expr()
        self._eat_newline()
        return ReturnStmt(value=value, line=tok.line, col=tok.col)

    def _import_stmt(self) -> ImportStmt:
        tok = self._expect(TT.IMPORT)
        module = self._dotted_name()
        self._eat_newline()
        return ImportStmt(module=module, line=tok.line, col=tok.col)

    def _from_import_stmt(self) -> ImportStmt:
        tok = self._expect(TT.FROM)
        from_mod = self._dotted_name()
        self._expect(TT.IMPORT)
        names: List[Tuple[str, Optional[str]]] = []
        if self._at(TT.STAR):
            self._advance()
            names = [('*', None)]
        else:
            while True:
                name = self._expect(TT.NAME).value
                alias = None
                # future: 'as alias'
                names.append((name, alias))
                if not self._at(TT.COMMA):
                    break
                self._advance()
        self._eat_newline()
        return ImportStmt(from_module=from_mod, names=names,
                          line=tok.line, col=tok.col)

    def _dotted_name(self) -> str:
        parts = [self._expect(TT.NAME).value]
        while self._at(TT.DOT):
            self._advance()
            parts.append(self._expect(TT.NAME).value)
        return '.'.join(parts)

    def _assert_stmt(self) -> AssertStmt:
        tok = self._expect(TT.ASSERT)
        cond = self._expr()
        msg = None
        if self._at(TT.COMMA):
            self._advance()
            msg = self._expr()
        self._eat_newline()
        return AssertStmt(condition=cond, message=msg, line=tok.line, col=tok.col)

    def _expr_stmt(self) -> ExprStmt:
        tok = self._cur()
        expr = self._expr()
        # Check for augmented/plain assignment
        if self._at(TT.EQ, TT.PLUSEQ, TT.MINUSEQ, TT.STAREQ,
                    TT.SLASHEQ, TT.PERCENTEQ, TT.DSTAREQ):
            op_tok = self._advance()
            op = '' if op_tok.type == TT.EQ else op_tok.value[0]
            rhs = self._expr()
            self._eat_newline()
            return ExprStmt(
                expr=Assign(target=expr, value=rhs, op=op,
                            line=tok.line, col=tok.col),
                line=tok.line, col=tok.col,
            )
        self._eat_newline()
        return ExprStmt(expr=expr, line=tok.line, col=tok.col)

    # ── Expression parsers (precedence climbing) ──────────────────────────────

    def _expr(self) -> Node:
        return self._ternary()

    def _ternary(self) -> Node:
        node = self._or_expr()
        if self._at(TT.IF):
            self._advance()
            cond = self._or_expr()
            self._expect(TT.ELSE)
            alt = self._ternary()
            node = IfExpr(condition=cond, then_val=node, else_val=alt,
                          line=node.line, col=node.col)
        return node

    def _or_expr(self) -> Node:
        node = self._and_expr()
        while self._at(TT.OR):
            self._advance()
            right = self._and_expr()
            if isinstance(node, BoolOp) and node.op == 'or':
                node.values.append(right)
            else:
                node = BoolOp(op='or', values=[node, right],
                              line=node.line, col=node.col)
        return node

    def _and_expr(self) -> Node:
        node = self._not_expr()
        while self._at(TT.AND):
            self._advance()
            right = self._not_expr()
            if isinstance(node, BoolOp) and node.op == 'and':
                node.values.append(right)
            else:
                node = BoolOp(op='and', values=[node, right],
                              line=node.line, col=node.col)
        return node

    def _not_expr(self) -> Node:
        if self._at(TT.NOT):
            tok = self._advance()
            return UnaryOp(op='not', operand=self._not_expr(),
                           line=tok.line, col=tok.col)
        return self._compare()

    _CMP_OPS = {TT.EQEQ, TT.NEQ, TT.LT, TT.GT, TT.LEQ, TT.GEQ, TT.IN, TT.IS}
    _CMP_OP_STR = {
        TT.EQEQ: '==', TT.NEQ: '!=', TT.LT: '<', TT.GT: '>',
        TT.LEQ: '<=', TT.GEQ: '>=',
    }

    def _compare(self) -> Node:
        node = self._bitor()
        ops: List[str] = []
        cmps: List[Node] = []
        while self._at(*self._CMP_OPS) or (self._at(TT.NOT) and self._peek().type == TT.IN) \
                or (self._at(TT.IS) and self._peek().type == TT.NOT):
            if self._at(TT.NOT):
                self._advance(); self._expect(TT.IN)
                ops.append('not in')
            elif self._at(TT.IS) and self._peek().type == TT.NOT:
                self._advance(); self._advance()
                ops.append('is not')
            elif self._at(TT.IS):
                self._advance(); ops.append('is')
            elif self._at(TT.IN):
                self._advance(); ops.append('in')
            else:
                tok = self._advance()
                ops.append(self._CMP_OP_STR[tok.type])
            cmps.append(self._bitor())
        if ops:
            return Compare(left=node, ops=ops, comparators=cmps,
                           line=node.line, col=node.col)
        return node

    def _bitor(self) -> Node:
        return self._binop(self._bitxor, {TT.PIPE: '|'})

    def _bitxor(self) -> Node:
        return self._binop(self._bitand, {TT.CARET: '^'})

    def _bitand(self) -> Node:
        return self._binop(self._shift, {TT.AMP: '&'})

    def _shift(self) -> Node:
        return self._binop(self._add, {TT.LSHIFT: '<<', TT.RSHIFT: '>>'})

    def _add(self) -> Node:
        return self._binop(self._mul, {TT.PLUS: '+', TT.MINUS: '-'})

    def _mul(self) -> Node:
        return self._binop(self._unary, {
            TT.STAR: '*', TT.SLASH: '/', TT.DOUBLESLASH: '//',
            TT.PERCENT: '%', TT.AT: '@',
        })

    def _binop(self, next_level, ops: dict) -> Node:
        node = next_level()
        while self._at(*ops):
            op = ops[self._advance().type]
            right = next_level()
            node = BinOp(left=node, op=op, right=right,
                         line=node.line, col=node.col)
        return node

    def _unary(self) -> Node:
        if self._at(TT.MINUS, TT.PLUS, TT.TILDE):
            tok = self._advance()
            return UnaryOp(op=tok.value, operand=self._unary(),
                           line=tok.line, col=tok.col)
        return self._power()

    def _power(self) -> Node:
        base = self._postfix()
        if self._at(TT.DSTAR):
            self._advance()
            exp = self._unary()  # right-associative
            return BinOp(left=base, op='**', right=exp, line=base.line, col=base.col)
        return base

    def _postfix(self) -> Node:
        node = self._primary()
        while True:
            if self._at(TT.DOT):
                self._advance()
                attr = self._expect(TT.NAME).value
                node = Attribute(obj=node, attr=attr, line=node.line, col=node.col)
            elif self._at(TT.LBRACKET):
                self._advance()
                idx = self._subscript_or_slice(node)
                self._expect(TT.RBRACKET)
                node = Subscript(obj=node, index=idx, line=node.line, col=node.col)
            elif self._at(TT.LPAREN):
                args, kwargs = self._call_args()
                node = Call(func=node, args=args, kwargs=kwargs,
                            line=node.line, col=node.col)
            else:
                break
        return node

    def _subscript_or_slice(self, obj_node: Node) -> Node:
        """Parse index or slice inside []. Cursor is after the opening [."""
        line, col = obj_node.line, obj_node.col
        # Leading colon → slice with no start
        if self._at(TT.COLON):
            self._advance()
            stop = None if self._at(TT.RBRACKET, TT.COLON) else self._expr()
            step = None
            if self._at(TT.COLON):
                self._advance()
                step = None if self._at(TT.RBRACKET) else self._expr()
            return Slice(start=None, stop=stop, step=step, line=line, col=col)
        first = self._expr()
        # Colon after first expr → slice
        if self._at(TT.COLON):
            self._advance()
            stop = None if self._at(TT.RBRACKET, TT.COLON) else self._expr()
            step = None
            if self._at(TT.COLON):
                self._advance()
                step = None if self._at(TT.RBRACKET) else self._expr()
            return Slice(start=first, stop=stop, step=step, line=line, col=col)
        return first

    def _call_args(self) -> Tuple[List[Node], List[Tuple[str, Node]]]:
        self._expect(TT.LPAREN)
        args: List[Node] = []
        kwargs: List[Tuple[str, Node]] = []
        while not self._at(TT.RPAREN, TT.EOF):
            # keyword arg: name=expr
            if self._at(TT.NAME) and self._peek().type == TT.EQ:
                key = self._advance().value
                self._advance()  # skip =
                val = self._expr()
                kwargs.append((key, val))
            else:
                args.append(self._expr())
            if not self._at(TT.COMMA):
                break
            self._advance()
        self._expect(TT.RPAREN)
        return args, kwargs

    def _primary(self) -> Node:  # noqa: C901
        tok = self._cur()
        tt = tok.type

        if tt == TT.INT:
            self._advance()
            return Literal(value=tok.value, line=tok.line, col=tok.col)
        if tt == TT.FLOAT:
            self._advance()
            return Literal(value=tok.value, line=tok.line, col=tok.col)
        if tt == TT.STRING:
            self._advance()
            # Adjacent string concatenation
            val = tok.value
            while self._at(TT.STRING):
                val += self._advance().value
            return Literal(value=val, line=tok.line, col=tok.col)
        if tt == TT.FSTRING:
            self._advance()
            return self._parse_fstring(tok.value, tok.line, tok.col)
        if tt == TT.TRUE:
            self._advance()
            return Literal(value=True, line=tok.line, col=tok.col)
        if tt == TT.FALSE:
            self._advance()
            return Literal(value=False, line=tok.line, col=tok.col)
        if tt == TT.NONE:
            self._advance()
            return Literal(value=None, line=tok.line, col=tok.col)
        if tt == TT.NAME:
            self._advance()
            return Name(id=tok.value, line=tok.line, col=tok.col)
        if tt == TT.LPAREN:
            return self._paren_expr()
        if tt == TT.LBRACKET:
            return self._list_expr()
        if tt == TT.LBRACE:
            return self._dict_or_set()
        if tt == TT.LAMBDA:
            return self._lambda_expr()
        if tt == TT.FN:
            # Anonymous function: fn(params): body_expr
            return self._anon_fn()
        if tt == TT.ELLIPSIS:
            self._advance()
            return Literal(value=..., line=tok.line, col=tok.col)
        raise ParseError(
            f"Unexpected token {tok.type.name} ({tok.value!r})",
            tok.line, tok.col,
        )

    def _paren_expr(self) -> Node:
        tok = self._expect(TT.LPAREN)
        if self._at(TT.RPAREN):
            self._advance()
            return TupleExpr(elements=[], line=tok.line, col=tok.col)
        first = self._expr()
        if self._at(TT.COMMA):
            # Tuple
            elements = [first]
            while self._at(TT.COMMA):
                self._advance()
                if self._at(TT.RPAREN):
                    break
                elements.append(self._expr())
            self._expect(TT.RPAREN)
            return TupleExpr(elements=elements, line=tok.line, col=tok.col)
        self._expect(TT.RPAREN)
        return first

    def _list_expr(self) -> Node:
        tok = self._expect(TT.LBRACKET)
        if self._at(TT.RBRACKET):
            self._advance()
            return ListExpr(elements=[], line=tok.line, col=tok.col)
        first = self._expr()
        # List comprehension: [expr for name in iterable [if cond]]
        if self._at(TT.FOR):
            self._advance()
            target = self._expect(TT.NAME).value
            self._expect(TT.IN)
            iterable = self._or_expr()  # no ternary — avoids if/else ambiguity
            cond = None
            if self._at(TT.IF):
                self._advance()
                cond = self._or_expr()  # filter condition; ternary would require 'else'
            self._expect(TT.RBRACKET)
            return ListComp(element=first, target=target, iterable=iterable,
                            condition=cond, line=tok.line, col=tok.col)
        elements = [first]
        while self._at(TT.COMMA):
            self._advance()
            if self._at(TT.RBRACKET):
                break
            elements.append(self._expr())
        self._expect(TT.RBRACKET)
        return ListExpr(elements=elements, line=tok.line, col=tok.col)

    def _dict_or_set(self) -> Node:
        tok = self._expect(TT.LBRACE)
        if self._at(TT.RBRACE):
            self._advance()
            return DictExpr(keys=[], values=[], line=tok.line, col=tok.col)
        first = self._expr()
        if self._at(TT.COLON):
            # Dict
            self._advance()
            first_val = self._expr()
            keys = [first]; values = [first_val]
            while self._at(TT.COMMA):
                self._advance()
                if self._at(TT.RBRACE):
                    break
                keys.append(self._expr())
                self._expect(TT.COLON)
                values.append(self._expr())
            self._expect(TT.RBRACE)
            return DictExpr(keys=keys, values=values, line=tok.line, col=tok.col)
        # Set
        elements = [first]
        while self._at(TT.COMMA):
            self._advance()
            if self._at(TT.RBRACE):
                break
            elements.append(self._expr())
        self._expect(TT.RBRACE)
        return SetExpr(elements=elements, line=tok.line, col=tok.col)

    def _lambda_expr(self) -> LambdaExpr:
        tok = self._expect(TT.LAMBDA)
        params: List[str] = []
        while not self._at(TT.COLON, TT.EOF):
            params.append(self._expect(TT.NAME).value)
            if not self._at(TT.COMMA):
                break
            self._advance()
        self._expect(TT.COLON)
        body = self._expr()
        return LambdaExpr(params=params, body=body, line=tok.line, col=tok.col)

    def _anon_fn(self) -> FnDef:
        tok = self._expect(TT.FN)
        self._expect(TT.LPAREN)
        params, defaults = self._param_list()
        self._expect(TT.RPAREN)
        return_type = None
        if self._at(TT.ARROW):
            self._advance()
            return_type = self._expect(TT.NAME).value
        # Single-expression body: fn(x): x * 2
        if self._at(TT.COLON) and not self._peek_is_block():
            self._advance()
            expr = self._expr()
            body = [ReturnStmt(value=expr, line=expr.line, col=expr.col)]
        else:
            body = self._indented_block()
        return FnDef(name='<lambda>', params=params, return_type=return_type,
                     body=body, decorators=[], defaults=defaults,
                     line=tok.line, col=tok.col)

    def _peek_is_block(self) -> bool:
        """Return True if the colon is followed by NEWLINE+INDENT (a block)."""
        i = self.pos + 1
        while i < len(self.tokens) and self.tokens[i].type == TT.NEWLINE:
            i += 1
        return i < len(self.tokens) and self.tokens[i].type == TT.INDENT

    def _parse_fstring(self, raw: str, line: int, col: int) -> FStringExpr:
        """Split f-string raw content into literal and expression parts."""
        parts: List[Node] = []
        i = 0
        buf = []
        while i < len(raw):
            if raw[i] == '{' and i + 1 < len(raw) and raw[i + 1] == '{':
                buf.append('{'); i += 2
            elif raw[i] == '}' and i + 1 < len(raw) and raw[i + 1] == '}':
                buf.append('}'); i += 2
            elif raw[i] == '{':
                if buf:
                    parts.append(FStringLiteral(value=''.join(buf), line=line, col=col))
                    buf = []
                depth = 1; j = i + 1
                while j < len(raw) and depth:
                    if raw[j] == '{': depth += 1
                    elif raw[j] == '}': depth -= 1
                    j += 1
                expr_src = raw[i + 1:j - 1]
                from .lexer import Lexer as _Lex
                sub_tokens = _Lex(expr_src).tokenize()
                parts.append(Parser(sub_tokens).parse_expression())
                i = j
            else:
                buf.append(raw[i]); i += 1
        if buf:
            parts.append(FStringLiteral(value=''.join(buf), line=line, col=col))
        return FStringExpr(parts=parts, line=line, col=col)
