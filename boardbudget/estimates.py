from __future__ import annotations

import ast
import operator
from math import isfinite
from typing import Any

from .models import WarningMessage


OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}

UNARY_OPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


class EstimateExpressionError(ValueError):
    pass


def is_blank(value: Any) -> bool:
    return value is None or str(value).strip() == ""


def parse_number_expression(value: Any) -> float | None:
    if is_blank(value):
        return None
    if isinstance(value, (int, float)):
        number = float(value)
        if isfinite(number):
            return number
        raise EstimateExpressionError("Number is not finite.")

    expression = str(value).strip()
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise EstimateExpressionError("Invalid numeric expression.") from exc
    return _eval_node(tree.body)


def _eval_node(node: ast.AST) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return _finite(float(node.value))
    if isinstance(node, ast.BinOp) and type(node.op) in OPS:
        right = _eval_node(node.right)
        if isinstance(node.op, ast.Div) and right == 0:
            raise EstimateExpressionError("Division by zero.")
        return _finite(OPS[type(node.op)](_eval_node(node.left), right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in UNARY_OPS:
        return _finite(UNARY_OPS[type(node.op)](_eval_node(node.operand)))
    raise EstimateExpressionError("Unsupported numeric expression.")


def _finite(number: float) -> float:
    if not isfinite(number):
        raise EstimateExpressionError("Number is not finite.")
    return number


def normalize_estimates(activity_id: str, estimated_days_value: Any, estimated_hours_value: Any) -> tuple[float | None, float, list[WarningMessage]]:
    warnings: list[WarningMessage] = []
    estimated_days: float | None = None
    estimated_hours: float | None = None

    try:
        estimated_days = parse_number_expression(estimated_days_value)
    except EstimateExpressionError:
        warnings.append(
            WarningMessage("WARNING", "INVALID_ESTIMATE_EXPRESSION", f"Activity {activity_id} has invalid estimated_days expression.")
        )

    try:
        estimated_hours = parse_number_expression(estimated_hours_value)
    except EstimateExpressionError:
        warnings.append(
            WarningMessage("WARNING", "INVALID_ESTIMATE_EXPRESSION", f"Activity {activity_id} has invalid estimated_hours expression.")
        )

    if estimated_hours is not None:
        normalized_hours = estimated_hours
        normalized_days = normalized_hours / 8
        if estimated_days is not None and abs(estimated_days * 8 - estimated_hours) > 0.000001:
            warnings.append(
                WarningMessage(
                    "WARNING",
                    "ESTIMATE_DAYS_HOURS_MISMATCH",
                    f"Activity {activity_id} has estimated_days and estimated_hours inconsistent; estimated_hours was used.",
                )
            )
        return normalized_days, normalized_hours, warnings

    if estimated_days is not None:
        return estimated_days, estimated_days * 8, warnings

    return None, 0, warnings

