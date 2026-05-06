from dataclasses import dataclass

from mzt.ir import Cell, ColonDef, Literal, PrimRef


@dataclass(frozen=True)
class Rule:
    name: str
    pattern: tuple[Cell, ...]
    replacement: tuple[Cell, ...]


_RULES: list[Rule] = [
    Rule(
        name="zero-push",
        pattern=(Literal(0),),
        replacement=(PrimRef("zero"),),
    ),
    Rule(
        name="swap-drop-as-nip",
        pattern=(PrimRef("swap"), PrimRef("drop")),
        replacement=(PrimRef("nip"),),
    ),
]


def all_rules() -> list[Rule]:
    return list(_RULES)


def optimize(defs: list[ColonDef]) -> list[ColonDef]:
    return [_optimize_def(d) for d in defs]


def optimize_body(body: tuple[Cell, ...]) -> tuple[Cell, ...]:
    rules = _rules_by_specificity()
    while True:
        rewritten, changed = _apply_pass(body, rules)
        if not changed:
            return rewritten
        body = rewritten


def _optimize_def(d: ColonDef) -> ColonDef:
    return ColonDef(name=d.name, body=optimize_body(d.body))


def _rules_by_specificity() -> list[Rule]:
    return sorted(_RULES, key=lambda r: len(r.pattern), reverse=True)


def _apply_pass(body: tuple[Cell, ...], rules: list[Rule]) -> tuple[tuple[Cell, ...], bool]:
    out: list[Cell] = []
    i = 0
    changed = False
    while i < len(body):
        rule = _find_match(body, i, rules)
        if rule is None:
            out.append(body[i])
            i += 1
            continue
        out.extend(rule.replacement)
        i += len(rule.pattern)
        changed = True
    return tuple(out), changed


def _find_match(body: tuple[Cell, ...], i: int, rules: list[Rule]) -> Rule | None:
    for rule in rules:
        end = i + len(rule.pattern)
        if end > len(body):
            continue
        if body[i:end] == rule.pattern:
            return rule
    return None
