import type { Part } from "@/lib/api";

export interface LinePricing {
  bomQty: number;
  minQty: number;
  batchCost: number | null;
  unitCost: number | null;
  unitCostOverride: boolean;
  orderQty: number;
  packsOrdered: number;
  lineTotal: number | null;
  unitCostExpression: string;
  batchNote: string;
  needsBatchOrder: boolean;
}

function roundQty(value: number): number {
  return Math.abs(value - Math.round(value)) < 1e-9
    ? Math.round(value)
    : value;
}

export function computeLinePricing(part: Part): LinePricing {
  const bomQty = Math.max(part.quantity || 0, 0);
  const minQty = Math.max(part.price_min_qty || 1, 1);
  const batchCost =
    part.price_batch_cost != null && !Number.isNaN(part.price_batch_cost)
      ? part.price_batch_cost
      : null;
  const unitOverride = part.unit_cost != null && !Number.isNaN(part.unit_cost);

  let unitCost: number | null;
  let unitCostExpression: string;

  if (unitOverride) {
    unitCost = part.unit_cost!;
    unitCostExpression = `manual: ${formatCurrency(unitCost)}/ea`;
  } else if (batchCost != null && minQty > 0) {
    unitCost = batchCost / minQty;
    unitCostExpression = `${formatCurrency(batchCost)} ÷ ${roundQty(minQty)} = ${formatCurrency(unitCost)}/ea`;
  } else {
    unitCost = null;
    unitCostExpression = "";
  }

  let packsOrdered = 1;
  let orderQty = bomQty;
  let lineTotal: number | null = null;
  let batchNote = "";

  if (minQty > 1) {
    packsOrdered = bomQty > 0 ? Math.max(1, Math.ceil(bomQty / minQty)) : 0;
    orderQty = packsOrdered * minQty;
    if (batchCost != null) {
      lineTotal = bomQty > 0 ? packsOrdered * batchCost : 0;
      batchNote = `${packsOrdered}× pack of ${roundQty(minQty)} @ ${formatCurrency(batchCost)}`;
    } else if (unitCost != null) {
      lineTotal = bomQty > 0 ? orderQty * unitCost : 0;
      batchNote = `order ${roundQty(orderQty)} (min pack ${roundQty(minQty)})`;
    } else {
      batchNote = `min pack ${roundQty(minQty)}`;
    }
  } else if (unitCost != null && bomQty > 0) {
    lineTotal = bomQty * unitCost;
  }

  const needsBatchOrder = bomQty > 0 && orderQty > bomQty;

  return {
    bomQty,
    minQty,
    batchCost,
    unitCost,
    unitCostOverride: unitOverride,
    orderQty,
    packsOrdered,
    lineTotal,
    unitCostExpression,
    batchNote,
    needsBatchOrder,
  };
}

export function summarizeProjectPricing(parts: Part[]): {
  lineCount: number;
  pricedLines: number;
  projectTotal: number;
} {
  const lines = parts.map(computeLinePricing);
  const priced = lines.filter((line) => line.lineTotal != null);
  return {
    lineCount: parts.length,
    pricedLines: priced.length,
    projectTotal: priced.reduce((sum, line) => sum + (line.lineTotal ?? 0), 0),
  };
}

export function formatCurrency(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "—";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 4,
  }).format(value);
}

export function parseOptionalNumber(raw: string): number | null {
  const trimmed = raw.trim();
  if (!trimmed) return null;
  const value = Number(trimmed);
  return Number.isFinite(value) && value >= 0 ? value : null;
}
