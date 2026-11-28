"""Small, restricted Python-like language for player station scripts.

This interprets a deliberately limited AST. It never uses Python ``eval`` or
``exec`` and exposes only the functions supplied by the game.
"""

import ast
import math
import operator
import re


class StationScriptError(ValueError):
    """A syntax, sandbox, or runtime error in a station script."""


_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
}
_UNARYOPS = {ast.UAdd: operator.pos, ast.USub: operator.neg,
             ast.Not: operator.not_}
_COMPARES = {ast.Eq: operator.eq, ast.NotEq: operator.ne,
             ast.Lt: operator.lt, ast.LtE: operator.le,
             ast.Gt: operator.gt, ast.GtE: operator.ge,
             ast.In: lambda a, b: a in b,
             ast.NotIn: lambda a, b: a not in b}
_SAFE_BUILTINS = {
    "abs": abs, "all": all, "any": any, "bool": bool, "float": float, "int": int,
    "len": len, "max": max, "min": min, "round": round,
    "str": str, "sum": sum,
}
# Shell names can be written bare, e.g. produce_railgun_ammo(nuclear).
_SHELL_NAME_CONSTANTS = {
    name: name for name in (
        "kinetic", "plasma", "piercer", "nuclear",
        "railkinetic", "railplasma", "railpiercer", "rail_nuclear",
    )
}
_EVENT_NAMES = {"tick", "low_energy", "project_complete", "ship_complete"}
_EVENT_LINE = re.compile(r"^on\s+([a-z][a-z0-9_]*)\s*:\s*(?:#.*)?$")
_LEGACY_CALLS = {
    "build_hub": "station.build_hub",
    "build_module": "station.build_module",
    "set_priority": "station.set_priority",
    "move_module": "station.move_module",
    "has_hub": "station.has_hub",
    "resource": "station.resource",
    "module_count": "station.module_count",
    "queue_count": "station.queue_count",
    "energy_generation": "station.energy_generation",
    "energy_demand": "station.energy_demand",
    "deliver": "station.deliver",
    "log": "station.log",
    "build_freighter": "freighter.build",
    "available_freighters": "freighter.available",
    "buy_freighter": "freighter.buy",
    "send_freighter": "freighter.send",
    "credits": "player.credits",
    "produce_railgun_ammo": "station.produce_railgun_ammo",
}


def run_station_script(source, api, output=None, instruction_limit=2000,
                       event=None, automatic=False):
    """Run source using a small safe subset of Python syntax.

    Supported statements: expressions/API calls, simple assignments, if/else,
    bounded ``for`` loops over ``range`` or literal sequences, ``pass``, and
    top-level station event blocks. The expression language includes common
    literals, containers, indexing, f-strings, and a small safe builtin set.
    Imports, arbitrary attribute access, comprehensions, arbitrary calls, and
    all other syntax are rejected. Game APIs use the station/freighter/player
    namespaces; a small set of legacy bare names is retained for old saves.
    Returns the script's local variables.
    """
    source = str(source)
    if len(source) > 5000:
        raise StationScriptError("script is too long (maximum 5000 characters)")
    normalized_lines = []
    for line_number, line in enumerate(source.splitlines(), 1):
        match = _EVENT_LINE.fullmatch(line)
        if match:
            event_name = match.group(1)
            if event_name not in _EVENT_NAMES:
                raise StationScriptError(
                    "line %s: unknown event: %s" % (line_number, event_name))
            line = 'if __station_event__("%s"):' % event_name
        normalized_lines.append(line)
    source = "\n".join(normalized_lines)
    try:
        tree = ast.parse(source, mode="exec")
    except SyntaxError as exc:
        raise StationScriptError("line %s: %s" % (exc.lineno or 1, exc.msg)) from None
    except RecursionError:
        raise StationScriptError("script nesting is too deep") from None

    variables = {}
    budget = [max(1, int(instruction_limit))]
    output = output if output is not None else []

    def consume(node):
        budget[0] -= 1
        if budget[0] < 0:
            raise StationScriptError("instruction limit exceeded")

    def bounded(value):
        if isinstance(value, (str, list, tuple, dict)) and len(value) > 1000:
            raise StationScriptError("value is too large")
        if isinstance(value, float) and not math.isfinite(value):
            raise StationScriptError("number must be finite")
        if isinstance(value, (int, float)) and abs(value) > 1e12:
            raise StationScriptError("number is out of range")
        return value

    def expression(node):
        consume(node)
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (str, int, float, bool, type(None))):
                return bounded(node.value)
            raise StationScriptError("unsupported value")
        if isinstance(node, ast.Name):
            if node.id in variables:
                return variables[node.id]
            if node.id in _SHELL_NAME_CONSTANTS:
                return _SHELL_NAME_CONSTANTS[node.id]
            if node.id in ("True", "False", "None"):
                return {"True": True, "False": False, "None": None}[node.id]
            raise StationScriptError("unknown name: %s" % node.id)
        if isinstance(node, (ast.List, ast.Tuple)):
            values = [expression(item) for item in node.elts]
            return bounded(values if isinstance(node, ast.List) else tuple(values))
        if isinstance(node, ast.Dict):
            if any(key is None for key in node.keys):
                raise StationScriptError("dictionary unpacking is not supported")
            return bounded({expression(key): expression(value)
                            for key, value in zip(node.keys, node.values)})
        if isinstance(node, ast.Subscript):
            value, index = expression(node.value), expression(node.slice)
            valid_index = (type(index) is int
                           or (isinstance(value, dict)
                               and isinstance(index, (str, int))
                               and type(index) is not bool))
            if not valid_index or not isinstance(value, (str, list, tuple, dict)):
                raise StationScriptError(
                    "indexing supports integer list indexes and string/integer dictionary keys")
            try:
                return bounded(value[index])
            except (IndexError, KeyError) as exc:
                raise StationScriptError(str(exc) or "index out of range") from None
        if isinstance(node, ast.BinOp) and type(node.op) in _BINOPS:
            left, right = expression(node.left), expression(node.right)
            if isinstance(node.op, ast.Mult):
                if isinstance(left, (str, list, tuple)) and isinstance(right, int):
                    if len(left) * max(0, right) > 1000:
                        raise StationScriptError("value is too large")
                if isinstance(right, (str, list, tuple)) and isinstance(left, int):
                    if len(right) * max(0, left) > 1000:
                        raise StationScriptError("value is too large")
            try:
                return bounded(_BINOPS[type(node.op)](left, right))
            except (ArithmeticError, TypeError, ValueError) as exc:
                raise StationScriptError(str(exc)) from None
        if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARYOPS:
            try:
                return bounded(_UNARYOPS[type(node.op)](expression(node.operand)))
            except (ArithmeticError, TypeError, ValueError) as exc:
                raise StationScriptError(str(exc)) from None
        if isinstance(node, ast.BoolOp):
            result = expression(node.values[0])
            for item in node.values[1:]:
                if isinstance(node.op, ast.And) and not result:
                    return result
                if isinstance(node.op, ast.Or) and result:
                    return result
                result = expression(item)
            return result
        if isinstance(node, ast.Compare):
            left = expression(node.left)
            for op, comparator in zip(node.ops, node.comparators):
                if type(op) not in _COMPARES:
                    raise StationScriptError("comparison is not supported")
                right = expression(comparator)
                try:
                    matched = _COMPARES[type(op)](left, right)
                except (TypeError, ValueError) as exc:
                    raise StationScriptError(str(exc)) from None
                if not matched:
                    return False
                left = right
            return True
        if isinstance(node, ast.IfExp):
            return expression(node.body if expression(node.test)
                              else node.orelse)
        if isinstance(node, ast.JoinedStr):
            parts = []
            for value in node.values:
                if isinstance(value, ast.Constant) and isinstance(value.value, str):
                    parts.append(value.value)
                elif isinstance(value, ast.FormattedValue):
                    if value.format_spec is not None:
                        raise StationScriptError(
                            "f-string format specifiers are not supported")
                    item = expression(value.value)
                    if value.conversion == 114:
                        item = repr(item)
                    elif value.conversion == 97:
                        item = ascii(item)
                    else:
                        item = str(item)
                    parts.append(item)
                else:
                    raise StationScriptError("unsupported f-string expression")
            return bounded("".join(parts))
        if isinstance(node, ast.Call):
            if node.keywords:
                raise StationScriptError(
                    "only positional game function arguments are allowed")
            original_name = None
            if isinstance(node.func, ast.Name):
                original_name = node.func.id
                name = _LEGACY_CALLS.get(original_name, original_name)
                if (name not in ("range", "__station_event__")
                        and original_name not in _SAFE_BUILTINS
                        and name == original_name):
                    raise StationScriptError(
                        "game commands must use a namespace, such as station.resource()")
            elif (isinstance(node.func, ast.Attribute)
                  and isinstance(node.func.value, ast.Name)
                  and node.func.value.id in ("station", "freighter", "player")):
                name = node.func.value.id + "." + node.func.attr
            else:
                raise StationScriptError("only named game functions are allowed")
            args = [expression(arg) for arg in node.args]
            if original_name == "send_freighter" and len(args) == 3:
                # Older scripts specified a player-station index. Freighters
                # now buy from an NPC market and return to the scripted station.
                args = args[1:]
            if name == "__station_event__":
                if len(args) != 1 or args[0] not in _EVENT_NAMES:
                    raise StationScriptError("invalid event handler")
                return event == args[0]
            if name == "range":
                if not 1 <= len(args) <= 3 or any(type(arg) is not int for arg in args):
                    raise StationScriptError("range expects 1–3 integer arguments")
                if len(args) == 1:
                    start, stop, step = 0, args[0], 1
                elif len(args) == 2:
                    start, stop, step = args[0], args[1], 1
                else:
                    start, stop, step = args
                if step == 0:
                    raise StationScriptError("range step cannot be zero")
                count = (max(0, (stop - start + step - 1) // step)
                         if step > 0 else
                         max(0, (start - stop - step - 1) // -step))
                if count > 100:
                    raise StationScriptError("range is limited to 100 steps")
                values = range(*args)
                return values
            if isinstance(node.func, ast.Name) and original_name in _SAFE_BUILTINS:
                try:
                    return bounded(_SAFE_BUILTINS[original_name](*args))
                except (ArithmeticError, TypeError, ValueError) as exc:
                    raise StationScriptError(str(exc)) from None
            function = api.get(name)
            if function is None:
                raise StationScriptError("unknown game function: %s" % name)
            try:
                return bounded(function(*args))
            except StationScriptError:
                raise
            except Exception as exc:
                raise StationScriptError(str(exc) or type(exc).__name__) from None
        raise StationScriptError("unsupported expression: %s" % type(node).__name__)

    def is_event_handler(node):
        return (isinstance(node, ast.If)
                and isinstance(node.test, ast.Call)
                and isinstance(node.test.func, ast.Name)
                and node.test.func.id == "__station_event__")

    def statements(items, top_level=False):
        for node in items:
            consume(node)
            event_handler = top_level and is_event_handler(node)
            if top_level and automatic and not event_handler:
                continue
            if top_level and not automatic and event is None and event_handler:
                continue
            if isinstance(node, ast.Expr):
                expression(node.value)
            elif isinstance(node, ast.Assign):
                if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
                    raise StationScriptError("assign to one variable at a time")
                variables[node.targets[0].id] = expression(node.value)
            elif isinstance(node, ast.AugAssign):
                if not isinstance(node.target, ast.Name) or type(node.op) not in _BINOPS:
                    raise StationScriptError("unsupported assignment")
                if node.target.id not in variables:
                    raise StationScriptError("unknown variable: %s" % node.target.id)
                left = variables[node.target.id]
                right = expression(node.value)
                try:
                    variables[node.target.id] = bounded(
                        _BINOPS[type(node.op)](left, right))
                except (ArithmeticError, TypeError, ValueError) as exc:
                    raise StationScriptError(str(exc)) from None
            elif isinstance(node, ast.If):
                statements(node.body if expression(node.test) else node.orelse)
            elif isinstance(node, ast.For):
                if (not isinstance(node.target, ast.Name) or node.orelse
                        or not isinstance(node.iter, (ast.Call, ast.List, ast.Tuple))
                        or (isinstance(node.iter, ast.Call)
                            and (not isinstance(node.iter.func, ast.Name)
                                 or node.iter.func.id != "range"))):
                    raise StationScriptError("for loops must use range() or a literal sequence")
                values = expression(node.iter)
                if not isinstance(values, (range, list, tuple)) or len(values) > 100:
                    raise StationScriptError("for loop is limited to 100 steps")
                for value in values:
                    variables[node.target.id] = value
                    statements(node.body)
            elif isinstance(node, ast.Pass):
                continue
            else:
                raise StationScriptError("unsupported statement: %s" % type(node).__name__)

    try:
        statements(tree.body, top_level=True)
    except StationScriptError as exc:
        raise exc
    except Exception as exc:
        raise StationScriptError(str(exc) or type(exc).__name__) from None
    return variables
