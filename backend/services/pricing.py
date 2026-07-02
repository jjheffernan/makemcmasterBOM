"""McMaster-style batch / pack pricing for BOM line totals."""

from __future__ import annotations

import math
from dataclasses import dataclass

from backend.models.part import Part


@dataclass(frozen=True)
class LinePricing:
    bom_qty: float
    min_qty: float
    batch_cost: float | None
    unit_cost: float | None
    unit_cost_override: bool
    order_qty: float
    packs_ordered: int
    line_total: float | None
    unit_cost_expression: str
    batch_note: str


def _round_qty(value: float) -> float:
    if math.isclose(value, round(value), rel_tol=0, abs_tol=1e-9):
        return float(round(value))
    return value


def compute_line_pricing(part: Part) -> LinePricing:
    """
    Derive unit and line totals from BOM quantity and batch fields.

    When ``price_min_qty`` > 1, McMaster often sells in packs — order quantity
    rounds up to whole packs and line total uses ``price_batch_cost`` per pack.
    """
    bom_qty = max(float(part.quantity or 0), 0.0)
    min_qty = max(float(part.price_min_qty or 1), 1.0)
    batch_cost = part.price_batch_cost
    unit_override = part.unit_cost is not None

    if unit_override:
        unit_cost = float(part.unit_cost)
        unit_expression = f"manual: ${unit_cost:.4f}/ea"
    elif batch_cost is not None and min_qty > 0:
        unit_cost = float(batch_cost) / min_qty
        unit_expression = f"${float(batch_cost):.2f} ÷ {_round_qty(min_qty)} = ${unit_cost:.4f}/ea"
    else:
        unit_cost = None
        unit_expression = ""

    packs = 1
    batch_note = ""
    if min_qty > 1:
        packs = max(1, math.ceil(bom_qty / min_qty)) if bom_qty > 0 else 0
        order_qty = packs * min_qty
        if batch_cost is not None:
            line_total = packs * float(batch_cost) if bom_qty > 0 else 0.0
            batch_note = (
                f"{packs}× pack of {_round_qty(min_qty)} @ ${float(batch_cost):.2f}"
            )
        elif unit_cost is not None:
            line_total = order_qty * unit_cost if bom_qty > 0 else 0.0
            batch_note = f"order {_round_qty(order_qty)} (min pack {_round_qty(min_qty)})"
        else:
            line_total = None
            batch_note = f"min pack {_round_qty(min_qty)}"
    else:
        order_qty = bom_qty
        if unit_cost is not None and bom_qty > 0:
            line_total = bom_qty * unit_cost
        else:
            line_total = None

    if bom_qty > 0 and order_qty > bom_qty and not batch_note:
        batch_note = f"order {_round_qty(order_qty)} to meet minimum"

    return LinePricing(
        bom_qty=bom_qty,
        min_qty=min_qty,
        batch_cost=batch_cost,
        unit_cost=unit_cost,
        unit_cost_override=unit_override,
        order_qty=order_qty,
        packs_ordered=packs,
        line_total=line_total,
        unit_cost_expression=unit_expression,
        batch_note=batch_note,
    )


def summarize_project_pricing(parts: list[Part]) -> dict[str, float | int]:
    totals = [compute_line_pricing(part).line_total for part in parts]
    priced = [value for value in totals if value is not None]
    return {
        "line_count": len(parts),
        "priced_lines": len(priced),
        "project_total": sum(priced) if priced else 0.0,
    }
