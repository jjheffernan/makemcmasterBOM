import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import {
  flexRender,
  getCoreRowModel,
  useReactTable,
  type ColumnDef,
  type ColumnSizingState,
  type RowSelectionState,
} from "@tanstack/react-table";
import { Download, ExternalLink, Flag, Loader2, Trash2 } from "lucide-react";
import { BomDragHandle, readBomPartDragIndex } from "@/components/BomDragHandle";
import { HardwareCheckHint } from "@/components/HardwareCheckHint";
import { Button, buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { ProjectThumbnail } from "@/components/ProjectThumbnail";
import { DescriptionPreview } from "@/components/DescriptionPreview";
import { BomPricingTab } from "@/components/BomPricingTab";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  exportCsvUrl,
  getProject,
  updateProject,
  validateSpecifications,
  type McMasterStatus,
  type Part,
  type Project,
  type SpecificationIssue,
} from "@/lib/api";
import { getMatchPreferences } from "@/lib/matchPreferences";
import {
  mcmasterStatusClass,
  mcmasterStatusLabel,
  countNeedsVerification,
  alternativeOptionLabel,
  formatConfidence,
  hardwareMatchClass,
  hardwareMatchLabel,
  matchTierLabel,
  needsMcMasterVerification,
  summarizeMcMasterParts,
} from "@/lib/mcmaster";
import type { BrowseFinishOption, MatchAlternative } from "@/lib/api";
import { formatCurrency } from "@/lib/pricing";
import {
  specInputClassName,
  specPlaceholderForPart,
  worstSpecIssue,
} from "@/lib/specMetadata";
import { hardwareCheckTooltip, hardwareCategoryLabel, inferHardwareCategory } from "@/lib/hardwareCheckTips";
import { useReportMatchError } from "@/lib/reportContext";
import {
  buildBomDisplayRows,
  buildPartIndexMap,
  normalizePartsOrder,
  remapRowSelection,
  remapSpecIssuesByIndex,
  reorderPartWithinSection,
  resolveBomHeadings,
  type BomSectionKey,
} from "@/lib/bomSections";

function confidenceDisplay(part: Part): string {
  if (part.mcmaster_status === "not_applicable") return "—";
  return formatConfidence(part);
}

function confidenceColor(part: Part): string {
  if (part.mcmaster_status === "not_applicable") return "text-muted-foreground";
  if (part.confidence >= 0.7) return "text-success";
  if (part.confidence >= 0.4) return "text-warning";
  return "text-danger";
}

const compactInput =
  "h-8 min-h-8 px-2 text-xs shadow-none";
const compactSelect = "h-8 min-h-8 px-2 text-xs shadow-none";

type BomViewTab = "parts" | "pricing";

export function BomEditorPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const location = useLocation();
  const [project, setProject] = useState<Project | null>(
    (location.state as { project?: Project } | null)?.project ?? null,
  );
  const [parts, setParts] = useState<Part[]>(
    normalizePartsOrder(project?.parts ?? []),
  );
  const [loading, setLoading] = useState(!project);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [specIssuesByIndex, setSpecIssuesByIndex] = useState<
    Record<number, SpecificationIssue[]>
  >({});
  const [rowSelection, setRowSelection] = useState<RowSelectionState>({});
  const [columnSizing, setColumnSizing] = useState<ColumnSizingState>({});
  const [bulkQuantity, setBulkQuantity] = useState("");
  const [activeTab, setActiveTab] = useState<BomViewTab>("parts");
  const [bomHeadings, setBomHeadings] = useState(() =>
    resolveBomHeadings(project?.bom_headings),
  );
  const [dragPartIndex, setDragPartIndex] = useState<number | null>(null);
  const [dropTargetIndex, setDropTargetIndex] = useState<number | null>(null);
  const { openReport, registerBomContext } = useReportMatchError();

  useEffect(() => {
    if (!projectId) return;
    if (project) return;

    getProject(projectId)
      .then((p) => {
        setProject(p);
        setParts(normalizePartsOrder(p.parts));
        setBomHeadings(resolveBomHeadings(p.bom_headings));
      })
      .catch(() => setError("Could not load project"))
      .finally(() => setLoading(false));
  }, [projectId, project]);

  useEffect(() => {
    if (!projectId || !project) {
      registerBomContext(null);
      return;
    }
    registerBomContext({ projectId, project, parts });
    return () => registerBomContext(null);
  }, [projectId, project, parts, registerBomContext]);

  const applyFinish = useCallback(
    (index: number, finishId: string) => {
      setParts((prev) =>
        prev.map((p, i) => {
          if (i !== index) return p;
          const option = p.browse_finish_options?.find(
            (candidate) => candidate.finish_id === finishId,
          );
          if (!option) return p;
          const productUrl = option.product_url || option.mcmaster_url;
          return {
            ...p,
            selected_finish_id: finishId,
            match_selection_policy: "finish",
            mcmaster_url: productUrl,
            mcmaster_part_number:
              option.mcmaster_part_number ?? p.mcmaster_part_number,
            unit_cost: option.unit_cost ?? p.unit_cost,
            price_min_qty: option.price_min_qty ?? p.price_min_qty,
            price_batch_cost: option.price_batch_cost ?? p.price_batch_cost,
            price_listing_note: option.price_listing_note ?? p.price_listing_note,
            price_source: option.unit_cost != null ? "listing" : p.price_source,
          };
        }),
      );
    },
    [],
  );

  const applyAlternative = useCallback(
    (index: number, alt: MatchAlternative) => {
      setParts((prev) =>
        prev.map((p, i) => {
          if (i !== index) return p;
          const previous: MatchAlternative = {
            mcmaster_url: p.mcmaster_url,
            mcmaster_part_number: p.mcmaster_part_number,
            mcmaster_category: p.mcmaster_category,
            match_tier: (p.match_tier ?? "") as MatchAlternative["match_tier"],
            confidence: p.confidence,
            confidence_low: p.confidence_low ?? null,
            confidence_high: p.confidence_high ?? null,
            mcmaster_reason: p.mcmaster_reason,
          };
          const remaining = (p.match_alternatives ?? []).filter(
            (candidate) => candidate.mcmaster_url !== alt.mcmaster_url,
          );
          return {
            ...p,
            mcmaster_url: alt.mcmaster_url,
            mcmaster_part_number: alt.mcmaster_part_number,
            mcmaster_category: alt.mcmaster_category,
            match_tier: alt.match_tier,
            confidence: alt.confidence,
            confidence_low: alt.confidence_low ?? null,
            confidence_high: alt.confidence_high ?? null,
            mcmaster_reason: alt.mcmaster_reason,
            match_alternatives: [previous, ...remaining],
          };
        }),
      );
    },
    [],
  );

  const updatePart = useCallback((index: number, patch: Partial<Part>) => {
    setParts((prev) =>
      prev.map((p, i) => (i === index ? { ...p, ...patch } : p)),
    );
  }, []);

  const deleteRows = useCallback((indices: Iterable<number>) => {
    const toDelete = new Set(indices);
    setParts((prev) => prev.filter((_, i) => !toDelete.has(i)));
    setRowSelection({});
    setSpecIssuesByIndex({});
  }, []);

  const deleteRow = useCallback(
    (index: number) => {
      deleteRows([index]);
    },
    [deleteRows],
  );

  const applyBulkQuantity = useCallback(() => {
    const qty = Number(bulkQuantity);
    if (!Number.isFinite(qty) || qty < 0) return;
    const selected = Object.keys(rowSelection);
    if (!selected.length) return;
    const indices = new Set(
      selected.map((id) => Number(id)).filter((n) => !Number.isNaN(n)),
    );
    setParts((prev) =>
      prev.map((part, index) =>
        indices.has(index) ? { ...part, quantity: qty } : part,
      ),
    );
    setBulkQuantity("");
  }, [bulkQuantity, rowSelection]);

  const validateRowSpec = useCallback(async (index: number, snapshot?: Part[]) => {
    const source = snapshot ?? parts;
    const part = source[index];
    if (!part) return;
    try {
      const result = await validateSpecifications([part]);
      setSpecIssuesByIndex((prev) => ({
        ...prev,
        [index]: result.issues.map((issue) => ({ ...issue, part_index: index })),
      }));
    } catch {
      /* validation is best-effort in the editor */
    }
  }, [parts]);

  const coverage = useMemo(() => summarizeMcMasterParts(parts), [parts]);
  const notApplicableCount = coverage.not_applicable ?? 0;
  const verifyCount = useMemo(() => countNeedsVerification(parts), [parts]);
  const displayRows = useMemo(
    () => buildBomDisplayRows(parts, bomHeadings),
    [parts, bomHeadings],
  );

  const updateBomHeading = useCallback((key: BomSectionKey, text: string) => {
    setBomHeadings((prev) => ({ ...prev, [key]: text }));
  }, []);

  const reorderParts = useCallback(
    (fromIndex: number, toIndex: number) => {
      const next = reorderPartWithinSection(parts, fromIndex, toIndex);
      if (!next) return;

      const indexMap = buildPartIndexMap(parts, next);
      setParts(next);
      setSpecIssuesByIndex((prev) => remapSpecIssuesByIndex(prev, indexMap));
      setRowSelection((prev) => remapRowSelection(prev, indexMap));
    },
    [parts],
  );

  const clearDragState = useCallback(() => {
    setDragPartIndex(null);
    setDropTargetIndex(null);
  }, []);

  const columns = useMemo<ColumnDef<Part>[]>(
    () => [
      {
        id: "drag",
        size: 36,
        minSize: 36,
        maxSize: 36,
        enableResizing: false,
        header: () => <span className="sr-only">Reorder</span>,
        cell: ({ row }) => (
          <BomDragHandle
            partIndex={row.index}
            label={`Reorder ${row.original.original_name || "row"}`}
            onDragStart={setDragPartIndex}
            onDragEnd={clearDragState}
          />
        ),
      },
      {
        id: "select",
        size: 32,
        minSize: 32,
        maxSize: 32,
        enableResizing: false,
        header: ({ table }) => (
          <input
            type="checkbox"
            className="h-4 w-4 rounded border-border"
            checked={table.getIsAllPageRowsSelected()}
            ref={(el) => {
              if (el) {
                el.indeterminate =
                  table.getIsSomePageRowsSelected() &&
                  !table.getIsAllPageRowsSelected();
              }
            }}
            onChange={table.getToggleAllPageRowsSelectedHandler()}
            aria-label="Select all rows"
          />
        ),
        cell: ({ row }) => (
          <input
            type="checkbox"
            className="h-4 w-4 rounded border-border"
            checked={row.getIsSelected()}
            disabled={!row.getCanSelect()}
            onChange={row.getToggleSelectedHandler()}
            aria-label={`Select row ${row.index + 1}`}
          />
        ),
      },
      {
        header: "Qty",
        accessorKey: "quantity",
        size: 52,
        minSize: 48,
        maxSize: 64,
        cell: ({ row }) => (
          <Input
            type="number"
            min={0}
            step={1}
            className={cn(compactInput, "w-14 tabular-nums")}
            value={row.original.quantity}
            onChange={(e) =>
              updatePart(row.index, {
                quantity: Number(e.target.value) || 0,
              })
            }
          />
        ),
      },
      {
        header: "Part",
        accessorKey: "original_name",
        size: 128,
        minSize: 96,
        cell: ({ row }) => (
          <div className="flex min-w-0 items-start gap-1">
            <Input
              className={cn(compactInput, "min-w-0 flex-1")}
              value={row.original.original_name}
              onChange={(e) =>
                updatePart(row.index, { original_name: e.target.value })
              }
            />
            <HardwareCheckHint part={row.original} className="mt-1.5" />
          </div>
        ),
      },
      {
        header: "Specification",
        accessorKey: "specification",
        size: 148,
        minSize: 120,
        cell: ({ row }) => {
          const issue = worstSpecIssue(specIssuesByIndex[row.index]);
          const finishOptions = row.original.browse_finish_options ?? [];
          const showFinishPicker =
            row.original.match_tier === "filtered_browse" &&
            finishOptions.length > 1;
          return (
            <div className="space-y-1">
              <Input
                value={row.original.specification}
                placeholder={specPlaceholderForPart(row.original)}
                className={cn(compactInput, specInputClassName(issue))}
                onChange={(e) =>
                  updatePart(row.index, { specification: e.target.value })
                }
                onBlur={() => validateRowSpec(row.index)}
              />
              {showFinishPicker && (
                <Select
                  id={`finish-${row.index}`}
                  className={compactSelect}
                  aria-label="McMaster finish"
                  value={
                    row.original.selected_finish_id || finishOptions[0]?.finish_id
                  }
                  onChange={(e) => applyFinish(row.index, e.target.value)}
                >
                  {finishOptions.map((option: BrowseFinishOption) => (
                    <option key={option.finish_id} value={option.finish_id}>
                      Finish: {option.label}
                      {option.mcmaster_part_number
                        ? ` · ${option.mcmaster_part_number}`
                        : ""}
                      {option.unit_cost != null
                        ? ` · ${formatCurrency(option.unit_cost)}/ea`
                        : ""}
                    </option>
                  ))}
                </Select>
              )}
              {finishOptions.length > 1 && (
                <p className="text-[10px] text-muted-foreground">
                  {row.original.match_selection_policy === "finish"
                    ? "Finish selected manually"
                    : "Default: simplest standard row from McMaster table"}
                </p>
              )}
              {issue && (
                <p
                  className={cn(
                    "line-clamp-2 text-[10px] leading-snug",
                    issue.severity === "error" ? "text-danger" : "text-warning",
                  )}
                  title={issue.hint || issue.message}
                >
                  {issue.message}
                </p>
              )}
            </div>
          );
        },
      },
      {
        header: "Match",
        accessorKey: "mcmaster_status",
        size: 108,
        minSize: 88,
        cell: ({ row }) => {
          const status = (row.original.mcmaster_status ??
            "possible") as McMasterStatus;
          const hardwareCategory = inferHardwareCategory(row.original);
          const checkTooltip = hardwareCheckTooltip(row.original);
          return (
            <div className="space-y-0.5" title={checkTooltip}>
              <div className="flex flex-wrap items-center gap-1">
                <span
                  className={cn(
                    "inline-flex rounded-full px-1.5 py-0 text-[10px] font-medium",
                    mcmasterStatusClass(status),
                  )}
                >
                  {mcmasterStatusLabel(status)}
                </span>
                <HardwareCheckHint part={row.original} />
                <span
                  className={cn(
                    "font-mono text-[10px]",
                    confidenceColor(row.original),
                  )}
                >
                  {confidenceDisplay(row.original)}
                </span>
              </div>
              {row.original.match_tier && (
                <p className="truncate text-[10px] text-muted-foreground">
                  {matchTierLabel(row.original.match_tier)}
                  {hardwareCategory !== "unknown" && (
                    <span className="text-muted-foreground/80">
                      {" "}
                      · {hardwareCategoryLabel(hardwareCategory)}
                    </span>
                  )}
                  {row.original.mcmaster_metacategory_label && (
                    <span
                      className="text-muted-foreground/80"
                      title={`McMaster department: ${row.original.mcmaster_metacategory_label}`}
                    >
                      {" "}
                      · {row.original.mcmaster_metacategory_label}
                    </span>
                  )}
                </p>
              )}
              {(row.original.match_option_count ?? 0) > 3 && (
                <p
                  className="truncate text-[10px] text-warning"
                  title="Many McMaster paths match this line — confirm finish and link"
                >
                  {row.original.match_option_count} match options — verify pick
                </p>
              )}
              {hardwareMatchLabel(row.original.hardware_match_status) && (
                <p
                  className={cn(
                    "truncate text-[10px]",
                    hardwareMatchClass(row.original.hardware_match_status),
                  )}
                  title={hardwareMatchLabel(row.original.hardware_match_status)}
                >
                  {hardwareMatchLabel(row.original.hardware_match_status)}
                </p>
              )}
            </div>
          );
        },
      },
      {
        header: "Link",
        accessorKey: "mcmaster_url",
        size: 132,
        minSize: 100,
        cell: ({ row }) => {
          const isNa = row.original.mcmaster_status === "not_applicable";
          const alternatives = row.original.match_alternatives ?? [];
          const showWider =
            getMatchPreferences().show_wider_scope_alternatives;
          const sameSizeAlts = alternatives.filter(
            (alt) => alt.guess_scope === "same_size",
          );
          const widerAlts = showWider
            ? alternatives.filter((alt) => alt.guess_scope !== "same_size")
            : [];
          const visibleAlts = [...sameSizeAlts, ...widerAlts];
          return (
            <div className="space-y-1">
              <div className="flex min-w-0 items-center gap-1">
                <Input
                  value={row.original.mcmaster_url}
                  placeholder={isNa ? "N/A" : "McMaster URL"}
                  disabled={isNa}
                  className={cn(compactInput, "min-w-0 flex-1 font-mono text-[10px]")}
                  onChange={(e) =>
                    updatePart(row.index, { mcmaster_url: e.target.value })
                  }
                />
                {row.original.mcmaster_url && (
                  <a
                    href={row.original.mcmaster_url}
                    target="_blank"
                    rel="noreferrer"
                    className="shrink-0 text-link hover:text-[var(--link-hover)]"
                    title={`Open on McMaster-Carr\n\n${hardwareCheckTooltip(row.original)}`}
                  >
                    <ExternalLink className="h-3.5 w-3.5" />
                  </a>
                )}
              </div>
              {row.original.mcmaster_part_number && (
                <p className="truncate font-mono text-[10px] text-muted-foreground">
                  {row.original.mcmaster_part_number}
                </p>
              )}
              {visibleAlts.length > 0 && (
                <Select
                  key={`${row.index}-${row.original.mcmaster_url}-${showWider}`}
                  defaultValue=""
                  className={compactSelect}
                  aria-label="Other McMaster guesses"
                  onChange={(e) => {
                    const alt = alternatives.find(
                      (candidate) => candidate.mcmaster_url === e.target.value,
                    );
                    if (alt) applyAlternative(row.index, alt);
                  }}
                >
                  <option value="">Other guess…</option>
                  {sameSizeAlts.length > 0 && (
                    <optgroup label="Same size">
                      {sameSizeAlts.map((alt) => (
                        <option key={alt.mcmaster_url} value={alt.mcmaster_url}>
                          {alternativeOptionLabel(alt)}
                          {alt.mcmaster_part_number
                            ? ""
                            : ` · ${formatConfidence(alt)}`}
                        </option>
                      ))}
                    </optgroup>
                  )}
                  {widerAlts.length > 0 && (
                    <optgroup label="Wider search">
                      {widerAlts.map((alt) => (
                        <option key={alt.mcmaster_url} value={alt.mcmaster_url}>
                          {alternativeOptionLabel(alt)}
                          {alt.mcmaster_part_number
                            ? ` · ${alt.mcmaster_part_number}`
                            : ` · ${formatConfidence(alt)}`}
                        </option>
                      ))}
                    </optgroup>
                  )}
                </Select>
              )}
            </div>
          );
        },
      },
      {
        header: "Notes",
        accessorKey: "notes",
        size: 88,
        minSize: 72,
        cell: ({ row }) => (
          <Input
            className={compactInput}
            value={row.original.notes}
            onChange={(e) => updatePart(row.index, { notes: e.target.value })}
          />
        ),
      },
      {
        id: "actions",
        header: "",
        size: 64,
        minSize: 64,
        maxSize: 72,
        enableResizing: false,
        cell: ({ row }) => (
          <div className="flex items-center gap-0.5">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => openReport({ partIndex: row.index })}
              aria-label="Report matching error for this row"
              title="Report matching error"
            >
              <Flag className="h-4 w-4 text-muted-foreground" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => deleteRow(row.index)}
              aria-label="Delete row"
            >
              <Trash2 className="h-4 w-4 text-destructive" />
            </Button>
          </div>
        ),
      },
    ],
    [applyAlternative, applyFinish, clearDragState, deleteRow, openReport, specIssuesByIndex, updatePart, validateRowSpec],
  );

  const table = useReactTable({
    data: parts,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getRowId: (_row, index) => String(index),
    enableRowSelection: true,
    enableColumnResizing: true,
    columnResizeMode: "onChange",
    onRowSelectionChange: setRowSelection,
    onColumnSizingChange: setColumnSizing,
    state: { rowSelection, columnSizing },
  });

  const selectedCount = table.getSelectedRowModel().rows.length;

  async function handleSave() {
    if (!projectId) return;
    setSaving(true);
    setError(null);
    try {
      const updated = await updateProject(projectId, parts, bomHeadings);
      setProject(updated);
      setParts(normalizePartsOrder(updated.parts));
      setBomHeadings(resolveBomHeadings(updated.bom_headings));
      void validateSpecifications(updated.parts).then((result) => {
        const byIndex: Record<number, SpecificationIssue[]> = {};
        for (const issue of result.issues) {
          const list = byIndex[issue.part_index] ?? [];
          list.push(issue);
          byIndex[issue.part_index] = list;
        }
        setSpecIssuesByIndex(byIndex);
      });
    } catch {
      setError("Failed to save changes");
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center gap-2 py-20 text-muted-foreground">
        <Loader2 className="h-5 w-5 animate-spin" />
        Loading BOM…
      </div>
    );
  }

  if (!project || !projectId) {
    return (
      <Card>
        <CardContent className="py-10 text-center">
          <p className="text-muted-foreground">Project not found.</p>
          <Link
            to="/"
            className={cn(buttonVariants({ variant: "outline" }), "mt-4")}
          >
            Back to import
          </Link>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader className="flex flex-row items-start justify-between gap-4">
          <div className="flex min-w-0 flex-1 gap-4">
            <ProjectThumbnail
              url={project.thumbnail_url}
              title={project.title || "Project"}
              size="lg"
            />
            <div className="min-w-0">
              <CardTitle>{project.title || "Untitled Project"}</CardTitle>
              <CardDescription className="mt-1 space-y-1">
                <DescriptionPreview
                  description={project.description}
                  fallback={
                    project.makerworld_url
                      ? project.makerworld_url
                      : "Uploaded BOM"
                  }
                />
                {project.makerworld_url && (
                  <a
                    href={project.makerworld_url}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-block text-link hover:text-[var(--link-hover)]"
                  >
                    View on MakerWorld
                  </a>
                )}
              </CardDescription>
            </div>
          </div>
          <div className="flex shrink-0 flex-wrap gap-2">
            <Button variant="outline" onClick={handleSave} disabled={saving}>
              {saving ? "Saving…" : "Save"}
            </Button>
            <a
              href={exportCsvUrl(projectId)}
              download
              className={buttonVariants({ variant: "outline" })}
            >
              <Download className="h-4 w-4" />
              Export CSV
            </a>
          </div>
        </CardHeader>
        <CardContent>
          {parts.length > 0 && (
            <div className="mb-4 flex gap-1 rounded-lg border border-border bg-muted/40 p-1">
              <button
                type="button"
                className={cn(
                  "rounded-md px-4 py-2 text-sm font-medium transition-colors",
                  activeTab === "parts"
                    ? "bg-card text-foreground shadow-sm"
                    : "text-muted-foreground hover:text-foreground",
                )}
                onClick={() => setActiveTab("parts")}
              >
                Parts
              </button>
              <button
                type="button"
                className={cn(
                  "rounded-md px-4 py-2 text-sm font-medium transition-colors",
                  activeTab === "pricing"
                    ? "bg-card text-foreground shadow-sm"
                    : "text-muted-foreground hover:text-foreground",
                )}
                onClick={() => setActiveTab("pricing")}
              >
                Pricing
              </button>
            </div>
          )}
          {error && <p className="mb-4 text-sm text-destructive">{error}</p>}
          {project.warnings && project.warnings.length > 0 && (
            <div className="mb-4 rounded-lg border border-warning/30 bg-warning/10 px-4 py-3 text-sm">
              {project.warnings.map((warning) => (
                <p key={warning} className="text-warning">
                  {warning}
                </p>
              ))}
            </div>
          )}
          {parts.length > 0 && verifyCount > 0 && activeTab === "parts" && (
            <div className="mb-4 rounded-lg border border-warning/30 bg-warning/10 px-4 py-3 text-sm">
              <p className="font-medium text-warning">
                {verifyCount} part{verifyCount === 1 ? "" : "s"} need manual McMaster
                verification
              </p>
              <p className="mt-1 text-muted-foreground">
                Rows marked <span className="font-medium">Verify</span> or{" "}
                <span className="font-medium">Unlikely</span> use category or site search —
                open the link and confirm the SKU. Catalog matches show a part number and
                higher confidence. Wrong guess? Use{" "}
                <button
                  type="button"
                  className="font-medium text-link underline hover:text-[var(--link-hover)]"
                  onClick={() => openReport()}
                >
                  Report error
                </button>
                .
              </p>
            </div>
          )}
          {parts.length > 0 && notApplicableCount > 0 && activeTab === "parts" && (
            <div className="mb-4 rounded-lg border border-border bg-muted/40 px-4 py-3 text-sm text-muted-foreground">
              Items under{" "}
              <span className="font-medium text-foreground">
                {bomHeadings.not_applicable}
              </span>{" "}
              (3D-printed parts, electronics, filament, etc.) stay in your BOM with
              a blank McMaster link.
            </div>
          )}
          {parts.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No parts in this BOM.
              {project.bom_status === "none"
                ? " This MakerWorld project has no bill of materials — try uploading a BOM file (CSV, JSON, Markdown, etc.) from the import page."
                : " Parsing rules may need tuning in the notebooks."}
            </p>
          ) : activeTab === "pricing" ? (
            <BomPricingTab
              parts={parts}
              bomHeadings={bomHeadings}
              onUpdatePart={updatePart}
              onPartsSynced={(next) => setParts(normalizePartsOrder(next))}
              onReorderPart={reorderParts}
            />
          ) : (
            <>
              {selectedCount > 0 && (
                <div className="mb-3 flex flex-wrap items-center gap-2 rounded-lg border border-border bg-muted/30 px-3 py-2 text-sm">
                  <span className="font-medium">
                    {selectedCount} row{selectedCount === 1 ? "" : "s"} selected
                  </span>
                  <div className="flex flex-wrap items-center gap-2">
                    <Input
                      type="number"
                      min={0}
                      step={1}
                      className="h-8 w-24"
                      placeholder="Qty"
                      value={bulkQuantity}
                      onChange={(e) => setBulkQuantity(e.target.value)}
                    />
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={applyBulkQuantity}
                      disabled={!bulkQuantity.trim()}
                    >
                      Set quantity
                    </Button>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() =>
                        deleteRows(
                          table
                            .getSelectedRowModel()
                            .rows.map((row) => row.index),
                        )
                      }
                    >
                      <Trash2 className="mr-1 h-4 w-4 text-destructive" />
                      Delete selected
                    </Button>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => setRowSelection({})}
                    >
                      Clear
                    </Button>
                  </div>
                </div>
              )}
              <Table className="bom-editor-table w-full">
              <TableHeader>
                {table.getHeaderGroups().map((hg) => (
                  <TableRow key={hg.id}>
                    {hg.headers.map((header) => (
                      <TableHead
                        key={header.id}
                        className="relative px-1.5 py-1.5"
                        style={{ width: header.getSize() }}
                      >
                        {flexRender(
                          header.column.columnDef.header,
                          header.getContext(),
                        )}
                        {header.column.getCanResize() && (
                          <div
                            onMouseDown={header.getResizeHandler()}
                            onTouchStart={header.getResizeHandler()}
                            className={cn(
                              "absolute right-0 top-0 h-full w-1 cursor-col-resize touch-none select-none",
                              header.column.getIsResizing() && "bg-primary/50",
                            )}
                            aria-hidden
                          />
                        )}
                      </TableHead>
                    ))}
                  </TableRow>
                ))}
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
                          colSpan={table.getVisibleLeafColumns().length}
                          className="px-2 py-2"
                        >
                          <Input
                            value={displayRow.text}
                            onChange={(e) =>
                              updateBomHeading(displayRow.id, e.target.value)
                            }
                            aria-label={`${displayRow.id} section heading`}
                            className="h-8 border-transparent bg-transparent px-1 text-sm font-semibold tracking-tight shadow-none focus-visible:border-border"
                          />
                        </TableCell>
                      </TableRow>
                    );
                  }

                  const row = table.getRow(String(displayRow.partIndex));
                  if (!row) return null;

                  return (
                    <TableRow
                      key={row.id}
                      className={cn(
                        row.getIsSelected() && "bg-primary/5",
                        needsMcMasterVerification(row.original) &&
                          "bg-warning/5 hover:bg-warning/10",
                        dragPartIndex === displayRow.partIndex && "opacity-60",
                        dropTargetIndex === displayRow.partIndex &&
                          "outline outline-2 -outline-offset-2 outline-primary/60",
                      )}
                      onDragOver={(event) => {
                        event.preventDefault();
                        event.dataTransfer.dropEffect = "move";
                        setDropTargetIndex(displayRow.partIndex);
                      }}
                      onDragLeave={() => {
                        setDropTargetIndex((current) =>
                          current === displayRow.partIndex ? null : current,
                        );
                      }}
                      onDrop={(event) => {
                        event.preventDefault();
                        const fromIndex = readBomPartDragIndex(event.dataTransfer);
                        if (fromIndex != null) {
                          reorderParts(fromIndex, displayRow.partIndex);
                        }
                        clearDragState();
                      }}
                    >
                      {row.getVisibleCells().map((cell) => (
                        <TableCell
                          key={cell.id}
                          className="px-1.5 py-1.5 align-top"
                          style={{ width: cell.column.getSize() }}
                        >
                          {flexRender(
                            cell.column.columnDef.cell,
                            cell.getContext(),
                          )}
                        </TableCell>
                      ))}
                    </TableRow>
                  );
                })}
              </TableBody>
              </Table>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
