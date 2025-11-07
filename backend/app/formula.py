from __future__ import annotations

import operator
import re
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable

FormulaContext = Dict[str, float]


@dataclass
class FormulaResult:
    value: float
    details: Dict[str, float]


class FormulaEngine:
    """Very small Excel-like formula interpreter."""

    _ops: Dict[str, Callable[[float, float], float]] = {
        "+": operator.add,
        "-": operator.sub,
        "*": operator.mul,
        "/": operator.truediv,
    }

    def __init__(self, context: FormulaContext):
        self.context = context

    def eval(self, formula: str) -> FormulaResult:
        formula = formula.strip()
        if formula.upper().startswith("SUM(") and formula.endswith(")"):
            inside = formula[4:-1]
            parts = [p.strip() for p in inside.split(",") if p.strip()]
            total = 0.0
            details: Dict[str, float] = {}
            for part in parts:
                if ":" in part:
                    start, end = [s.strip() for s in part.split(":", 1)]
                    values = self._expand_range(start, end)
                else:
                    values = [self._resolve(part)]
                for key, value in values:
                    total += value
                    details[key] = value
            return FormulaResult(value=total, details=details)

        tokens = re.split(r"\s*([+\-*/])\s*", formula)
        if not tokens:
            return FormulaResult(0.0, {})
        value = self._resolve(tokens[0])[1]
        details = {tokens[0]: value}
        i = 1
        while i < len(tokens) - 1:
            op = tokens[i]
            operand = tokens[i + 1]
            rhs_name, rhs_value = self._resolve(operand)
            value = self._ops[op](value, rhs_value)
            details[rhs_name] = rhs_value
            i += 2
        return FormulaResult(value=value, details=details)

    def _resolve(self, token: str) -> tuple[str, float]:
        token = token.strip()
        if token in self.context:
            return token, float(self.context[token])
        try:
            return token, float(token)
        except ValueError as exc:
            raise KeyError(f"Unknown token {token}") from exc

    def _expand_range(self, start: str, end: str) -> Iterable[tuple[str, float]]:
        """Expand a simplified cell range that maps to dot-separated identifiers."""
        prefix = start.rstrip("0123456789")
        start_idx = int(start[len(prefix) :])
        end_idx = int(end[len(prefix) :])
        for idx in range(start_idx, end_idx + 1):
            key = f"{prefix}{idx}"
            yield key, self.context.get(key, 0.0)
