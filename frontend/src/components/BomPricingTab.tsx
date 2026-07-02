import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { syncPartsPricing, type Part } from "@/lib/api";
import {
  computeLinePricing,
  formatCurrency,
  parseOptionalNumber,
  summarizeProjectPricing,
} from "@/lib/pricing";

const compactInput =
  "h-8 min-h-8 px-2 text-xs shadow-none font-mono tabular-nums";

export interface BomPricingTabProps {
  parts: Part[];
  onUpdatePart: (index: number, patch: Partial<Part>) => void;
  onPartsSynced: (parts: Part[]) => void;
}

function markManualPricing(patch: Partial<Part>): Partial<Part> {
  return {
    ...patch,
    price_source: "manual",
    price_listing_note: "",
  };
}

function partsNeedPricingSync(parts: Part[]): boolean {
  return parts.some((part) => {
    if (part.mcmaster_status === "not_applicable") return false;
    if (part.price_source === "manual") return false;
    if (
      (part.price_source === "listing" || part.price_source === "api") &&
      (part.unit_cost != null || part.price_batch_cost != null)
    ) {
      return false;
    }
    return Boolean(part.mcmaster_part_number || part.mcmaster_url);
  });
}

export function BomPricingTab({
  parts,
  onUpdatePart,
  onPartsSynced,
}: BomPricingTabProps) {
  const [syncing, setSyncing] = useState(false);
  const [syncError, setSyncError] = useState<string | null>(null);
  const partsSnapshotRef = useRef(parts);
  partsSnapshotRef.current = parts;

  const runSync = useCallback(async () => {
    const snapshot = partsSnapshotRef.current;
    if (!partsNeedPricingSync(snapshot)) {
      setSyncing(false);
      setSyncError(null);
      return;
    }

    setSyncing(true);
    setSyncError(null);
    try {
      const result = await syncPartsPricing(snapshot);
      onPartsSynced(result.parts);
    } catch (err) {
      setSyncError(
        err instanceof Error ? err.message : "Could not load listing prices",
      );
    } finally {
      setSyncing(false);
    }
  }, [onPartsSynced]);

  useEffect(() => {
    void runSync();
  }, [runSync]);

  const rows = useMemo(
    () =>
      parts.map((part, index) => ({
        index,
        part,
        pricing: computeLinePricing(part),
      })),
    [parts],
  );

  const summary = useMemo(() => summarizeProjectPricing(parts), [parts]);
  const pendingCount = useMemo(
    () =>
      parts.filter((part) => {
        if (part.mcmaster_status === "not_applicable") return false;
        if (part.price_source === "manual") return false;
        return part.unit_cost == null && part.price_batch_cost == null;
      }).length,
    [parts],
  );

  if (parts.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        No parts to price — import or add BOM lines first.
      </p>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
        <p>
          Prices come from McMaster listings during import. This tab fills any
          missing lines and lets you override pack size or unit cost.
        </p>
        {syncing && (
          <span className="inline-flex items-center gap-1.5 text-xs text-primary">
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
            Syncing listing prices…
          </span>
        )}
        {!syncing && pendingCount > 0 && (
          <span className="text-xs text-warning">
            {pendingCount} line{pendingCount === 1 ? "" : "s"} still missing
            prices
          </span>
        )}
      </div>

      {syncError && (
        <p className="rounded-lg border border-warning/30 bg-warning/10 px-4 py-2 text-sm text-warning">
          {syncError}
        </p>
      )}

      <Table className="bom-pricing-table w-full">
        <TableHeader>
          <TableRow>
            <TableHead className="px-1.5 py-1.5">Part</TableHead>
            <TableHead className="px-1.5 py-1.5 w-16">BOM qty</TableHead>
            <TableHead className="px-1.5 py-1.5 w-20">Min / pack</TableHead>
            <TableHead className="px-1.5 py-1.5 w-24">Batch cost</TableHead>
            <TableHead className="px-1.5 py-1.5 w-28">Unit cost</TableHead>
            <TableHead className="px-1.5 py-1.5 w-20">Order qty</TableHead>
            <TableHead className="px-1.5 py-1.5 w-24">Line total</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map(({ index, part, pricing }) => {
            const showBatch = pricing.minQty > 1 || pricing.batchCost != null;
            const na = part.mcmaster_status === "not_applicable";
            const fromListing =
              part.price_source === "listing" || part.price_source === "api";
            return (
              <TableRow
                key={index}
                className={cn(
                  pricing.needsBatchOrder && "bg-warning/5 hover:bg-warning/10",
                  na && "opacity-70",
                )}
              >
                <TableCell className="px-1.5 py-1.5 align-top">
                  <div className="space-y-0.5">
                    <p className="text-xs font-medium leading-snug">
                      {part.original_name || "—"}
                    </p>
                    {part.mcmaster_part_number && (
                      <p className="font-mono text-[10px] text-muted-foreground">
                        {part.mcmaster_part_number}
                      </p>
                    )}
                    {fromListing && part.price_listing_note && (
                      <p
                        className="text-[10px] leading-snug text-success"
                        title={part.price_listing_note}
                      >
                        {part.price_listing_note}
                      </p>
                    )}
                    {part.price_source === "manual" && (
                      <p className="text-[10px] text-muted-foreground">
                        Manual override
                      </p>
                    )}
                    {na && (
                      <p className="text-[10px] text-muted-foreground">
                        Not on McMaster
                      </p>
                    )}
                  </div>
                </TableCell>
                <TableCell className="px-1.5 py-1.5 align-top tabular-nums text-xs">
                  {pricing.bomQty}
                </TableCell>
                <TableCell className="px-1.5 py-1.5 align-top">
                  <Input
                    type="number"
                    min={1}
                    step={1}
                    className={cn(compactInput, "w-20")}
                    value={part.price_min_qty ?? 1}
                    onChange={(e) => {
                      const value = parseOptionalNumber(e.target.value);
                      onUpdatePart(
                        index,
                        markManualPricing({
                          price_min_qty: value != null ? Math.max(1, value) : 1,
                        }),
                      );
                    }}
                  />
                </TableCell>
                <TableCell className="px-1.5 py-1.5 align-top">
                  <Input
                    type="number"
                    min={0}
                    step={0.01}
                    placeholder={showBatch ? "pack $" : "$"}
                    className={cn(compactInput, "w-24")}
                    value={part.price_batch_cost ?? ""}
                    onChange={(e) =>
                      onUpdatePart(
                        index,
                        markManualPricing({
                          price_batch_cost: parseOptionalNumber(e.target.value),
                          unit_cost: null,
                        }),
                      )
                    }
                  />
                  {showBatch && pricing.batchNote && (
                    <p
                      className="mt-1 text-[10px] leading-snug text-muted-foreground"
                      title={pricing.batchNote}
                    >
                      {pricing.batchNote}
                    </p>
                  )}
                </TableCell>
                <TableCell className="px-1.5 py-1.5 align-top">
                  <Input
                    type="number"
                    min={0}
                    step={0.0001}
                    placeholder="auto"
                    className={cn(compactInput, "w-28")}
                    value={part.unit_cost ?? ""}
                    onChange={(e) =>
                      onUpdatePart(
                        index,
                        markManualPricing({
                          unit_cost: parseOptionalNumber(e.target.value),
                        }),
                      )
                    }
                  />
                  {pricing.unitCostExpression ? (
                    <p
                      className={cn(
                        "mt-1 font-mono text-[10px] leading-snug",
                        pricing.unitCostOverride
                          ? "text-muted-foreground"
                          : "text-success",
                      )}
                      title="Computed unit cost"
                    >
                      = {pricing.unitCostExpression}
                    </p>
                  ) : (
                    <p className="mt-1 text-[10px] text-muted-foreground">
                      Enter batch cost or unit $
                    </p>
                  )}
                </TableCell>
                <TableCell className="px-1.5 py-1.5 align-top tabular-nums text-xs">
                  <span
                    className={cn(
                      pricing.needsBatchOrder && "font-medium text-warning",
                    )}
                    title={
                      pricing.needsBatchOrder
                        ? `Must order ${pricing.orderQty} (BOM needs ${pricing.bomQty})`
                        : undefined
                    }
                  >
                    {pricing.bomQty > 0 ? pricing.orderQty : "—"}
                  </span>
                </TableCell>
                <TableCell className="px-1.5 py-1.5 align-top font-mono text-xs tabular-nums">
                  {formatCurrency(pricing.lineTotal)}
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>

      <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border bg-muted/30 px-4 py-3 text-sm">
        <span className="text-muted-foreground">
          {summary.pricedLines} of {summary.lineCount} lines priced
        </span>
        <span className="font-semibold tabular-nums">
          Project total: {formatCurrency(summary.projectTotal)}
        </span>
      </div>
    </div>
  );
}
