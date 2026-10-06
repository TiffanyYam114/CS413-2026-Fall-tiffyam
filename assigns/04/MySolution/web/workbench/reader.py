"""Read constructor expressions as data. Never use eval/exec or import input."""
import ast
from . import lambda1 as lang
from .source import SourceError as InputError, validate_source


# Names, argument names, and expected types are an explicit allowlist.
SCHEMAS = {
    "D0Eint": (("arg1", int),),
    "D0Ebtf": (("arg1", bool),),
    "D0Evar": (("arg1", str),),
    "D0Eop1": (("name", str), ("arg1", lang.D0E000)),
    "D0Eop2": (("name", str), ("arg1", lang.D0E000), ("arg2", lang.D0E000)),
    "D0Elam": (("arg1", str), ("arg2", lang.D0E000)),
    "D0Efix": (("arg1", str), ("arg2", str), ("arg3", lang.D0E000)),
    "D0Eapp": (("arg1", lang.D0E000), ("arg2", lang.D0E000)),
    "D0Eif0": (("arg1", lang.D0E000), ("arg2", lang.D0E000), ("arg3", lang.D0E000)),
    "D0Elet": (("arg1", str), ("arg2", lang.D0E000), ("arg3", lang.D0E000)),
    "D0Epair": (("arg1", lang.D0E000), ("arg2", lang.D0E000)),
    "D0Epfst": (("arg1", lang.D0E000),),
    "D0Epsnd": (("arg1", lang.D0E000),),
}
MAX_AST_NODES = 4000
MAX_NESTING = 80


def read_expression(source: str) -> lang.d0exp:
    validate_source(source)
    try:
        tree = ast.parse(source.strip(), mode="eval")
    except (SyntaxError, ValueError, RecursionError) as exc:
        line = getattr(exc, "lineno", None)
        detail = getattr(exc, "msg", str(exc))
        raise InputError(f"Invalid constructor expression{f' on line {line}' if line else ''}: {detail}") from exc
    if sum(1 for _ in ast.walk(tree)) > MAX_AST_NODES:
        raise InputError(f"Input exceeds {MAX_AST_NODES} syntax nodes.")

    def build(node: ast.AST, depth: int = 0):
        if depth > MAX_NESTING:
            raise InputError(f"Constructor nesting exceeds {MAX_NESTING} levels.")
        if isinstance(node, ast.Constant) and type(node.value) in (int, bool, str):
            value = node.value
            if type(value) is int and value.bit_length() > 4096:
                raise InputError("Integer literals are limited to 4096 bits.")
            if type(value) is str and len(value) > 256:
                raise InputError("Names and operator strings are limited to 256 characters.")
            return value
        if (isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub))
                and isinstance(node.operand, ast.Constant) and type(node.operand.value) is int):
            value = build(node.operand, depth + 1)
            return -value if isinstance(node.op, ast.USub) else value
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id in SCHEMAS):
            raise InputError("Only LAMBDA constructor calls and literal arguments are allowed.")
        name = node.func.id
        schema = SCHEMAS[name]
        if len(node.args) > len(schema):
            raise InputError(f"{name} expects {len(schema)} arguments.")
        values = {schema[i][0]: build(arg, depth + 1) for i, arg in enumerate(node.args)}
        for kw in node.keywords:
            if kw.arg not in dict(schema) or kw.arg in values:
                raise InputError(f"Invalid or duplicate argument for {name}: {kw.arg!r}.")
            values[kw.arg] = build(kw.value, depth + 1)
        for field, expected in schema:
            if field not in values:
                raise InputError(f"Missing {name} argument: {field}.")
            value = values[field]
            valid = isinstance(value, expected) if expected is lang.D0E000 else type(value) is expected
            if not valid:
                raise InputError(f"{name}.{field} expects {expected.__name__}.")
            if expected is str and not value:
                raise InputError(f"{name}.{field} cannot be empty.")
        if name == "D0Eop1" and values["name"] not in {"+1", "-1"}:
            raise InputError("Unary operators are +1 and -1.")
        if name == "D0Eop2" and values["name"] not in {"+", "-", "*", "/", "<", ">", "<=", ">=", "==", "!="}:
            raise InputError("Unsupported binary operator.")
        return getattr(lang, name)(**values)

    expression = build(tree.body)
    if not isinstance(expression, lang.D0E000):
        raise InputError("The outer expression must be a LAMBDA constructor.")
    return expression
