import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { BomDragHandle, readBomPartDragIndex } from "@/components/BomDragHandle";
import { HardwareCheckHint } from "@/components/HardwareCheckHint";
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
  buildBomDisplayRows,
  resolveBomHeadings,
  type BomSectionKey,
} from "@/lib/bomSections";
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
  bomHeadings?: Partial<Record<BomSectionKey, string>>;
  onUpdatePart: (index: number, patch: Partial<Part>) => void;
  onPartsSynced: (parts: Part[]) => void;
  onReorderPart: (fromIndex: number, toIndex: number) => void;
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
  bomHeadings: bomHeadingsProp,
  onUpdatePart,
  onPartsSynced,
  onReorderPart,
}: BomPricingTabProps) {
  const [syncing, setSyncing] = useState(false);
  const [syncError, setSyncError] = useState<string | null>(null);
  const [dragPartIndex, setDragPartIndex] = useState<number | null>(null);
  const [dropTargetIndex, setDropTargetIndex] = useState<number | null>(null);
  const partsSnapshotRef = useRef(parts);
  partsSnapshotRef.current = parts;

  const headings = useMemo(
    () => resolveBomHeadings(bomHeadingsProp),
    [bomHeadingsProp],
  );
  const displayRows = useMemo(
    () => buildBomDisplayRows(parts, headings),
    [parts, headings],
  );

  const clearDragState = useCallback(() => {
    setDragPartIndex(null);
    setDropTargetIndex(null);
  }, []);

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

  const rowByIndex = useMemo(() => {
    const map = new Map<
      number,
      {
        index: number;
        part: Part;
        pricing: ReturnType<typeof computeLinePricing>;
      }
    >();
    for (let index = 0; index < parts.length; index += 1) {
      const part = parts[index];
      map.set(index, {
        index,
        part,
        pricing: computeLinePricing(part),
      });
    }
    return map;
  }, [parts]);

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
          missing lines and lets you override pack size or unit cost. Row order
          matches the Parts tab.
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
            <TableHead className="w-9 px-1.5 py-1.5">
              <span className="sr-only">Reorder</span>
            </TableHead>
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
          {displayRows.map((displayRow) => {
            if (displayRow.kind === "heading") {
              return (
                <TableRow
                  key={`heading-${displayRow.id}`}
                  className="bg-muted/40 hover:bg-muted/40"
                >
                  <TableCell
                    colSpan={8}
                    className="px-2 py-2 text-sm font-semibold tracking-tight"
                  >
                    {displayRow.text}
                  </TableCell>
                </TableRow>
              );
            }

            const row = rowByIndex.get(displayRow.partIndex);
            if (!row) return null;

            const { index, part, pricing } = row;
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
                  dragPartIndex === index && "opacity-60",
                  dropTargetIndex === index &&
                    "outline outline-2 -outline-offset-2 outline-primary/60",
                )}
                onDragOver={(event) => {
                  event.preventDefault();
                  event.dataTransfer.dropEffect = "move";
                  setDropTargetIndex(index);
                }}
                onDragLeave={() => {
                  setDropTargetIndex((current) =>
                    current === index ? null : current,
                  );
                }}
                onDrop={(event) => {
                  event.preventDefault();
                  const fromIndex = readBomPartDragIndex(event.dataTransfer);
                  if (fromIndex != null) {
                    onReorderPart(fromIndex, index);
                  }
                  clearDragState();
                }}
              >
                <TableCell className="px-1 py-1.5 align-top">
                  <BomDragHandle
                    partIndex={index}
                    label={`Reorder ${part.original_name || "row"}`}
                    onDragStart={setDragPartIndex}
                    onDragEnd={clearDragState}
                  />
                </TableCell>
                <TableCell className="px-1.5 py-1.5 align-top">
                  <div className="space-y-0.5">
                    <div className="flex items-start gap-1">
                      <p className="min-w-0 flex-1 text-xs font-medium leading-snug">
                        {part.original_name || "—"}
                      </p>
                      <HardwareCheckHint part={part} className="mt-0.5" />
                    </div>
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
