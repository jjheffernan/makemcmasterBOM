import type { ComponentType } from "react";
import { Check, Circle, Loader2, Minus, X } from "lucide-react";
import { ProjectThumbnail } from "@/components/ProjectThumbnail";
import { cn } from "@/lib/utils";
import type {
  ImportStageDefinition,
  ImportStageEvent,
  ImportStageId,
  ImportStageStatus,
} from "@/lib/api";

export type StageState = {
  status: ImportStageStatus;
  message: string;
  thumbnailUrl?: string;
  /** Hydration step: parts completed before the current line (0-based). */
  progressCurrent?: number;
  progressTotal?: number;
};

const STATUS_ICON: Record<ImportStageStatus, ComponentType<{ className?: string }>> = {
  pending: Circle,
  running: Loader2,
  done: Check,
  error: X,
  skipped: Minus,
};

const STATUS_STYLE: Record<ImportStageStatus, string> = {
  pending: "text-muted-foreground",
  running: "text-primary",
  done: "text-success",
  error: "text-destructive",
  skipped: "text-muted-foreground",
};

/** Fallback when /api/import/stages has not loaded yet. */
export const DEFAULT_IMPORT_STAGES: ImportStageDefinition[] = [
  {
    id: "validate",
    notebook: "01_scrape.ipynb",
    label: "Validate URL",
    description: "Confirm this is a MakerWorld project link",
  },
  {
    id: "scrape",
    notebook: "01_scrape.ipynb",
    label: "Scrape project page",
    description: "Download the project page and read title & description",
  },
  {
    id: "extract_bom",
    notebook: "02_extract_bom.ipynb",
    label: "Extract BOM file",
    description: "Locate and download the bill of materials attachment",
  },
  {
    id: "parse_bom",
    notebook: "03_parse_bom.ipynb",
    label: "Parse BOM",
    description: "Read spreadsheet rows into structured parts",
  },
  {
    id: "match_mcmaster",
    notebook: "04_match_mcmaster.ipynb",
    label: "Match McMaster-Carr",
    description: "Rank browse links and default part options",
  },
  {
    id: "enrich_mcmaster",
    notebook: "05_api_payload.ipynb",
    label: "Hydrate McMaster listings",
    description: "Fetch live SKUs, finishes, and listing prices from McMaster-Carr",
  },
  {
    id: "finalize",
    notebook: "05_api_payload.ipynb",
    label: "Prepare results",
    description: "Assemble the editable BOM for the editor",
  },
];

function parseHydrationProgress(debug?: Record<string, unknown> | null): {
  progressCurrent?: number;
  progressTotal?: number;
} {
  if (!debug) return {};
  const total =
    typeof debug.part_total === "number" && debug.part_total > 0
      ? debug.part_total
      : undefined;
  if (total === undefined) return {};
  const rawIndex =
    typeof debug.part_index === "number" ? debug.part_index : undefined;
  if (rawIndex === undefined || rawIndex < 0) {
    return { progressTotal: total };
  }
  return { progressCurrent: rawIndex, progressTotal: total };
}

function runningStageFraction(
  stageId: ImportStageId,
  state: StageState | undefined,
): number {
  if (stageId === "enrich_mcmaster") {
    const total = state?.progressTotal ?? 0;
    if (total > 0 && state?.progressCurrent !== undefined) {
      return (state.progressCurrent + 1) / total;
    }
    if (total > 0) {
      return 0.12;
    }
  }
  return 0.4;
}

function computePipelineProgress(
  stages: ImportStageDefinition[],
  stageState: Partial<Record<ImportStageId, StageState>>,
): { percent: number; label: string; indeterminate: boolean } {
  const totalStages = stages.length;
  if (totalStages === 0) {
    return { percent: 0, label: "", indeterminate: false };
  }

  let units = 0;
  let runningStage: ImportStageDefinition | null = null;
  let runningState: StageState | undefined;

  for (const stage of stages) {
    const state = stageState[stage.id];
    const status = state?.status ?? "pending";
    if (status === "done" || status === "skipped") {
      units += 1;
      continue;
    }
    if (status === "running") {
      units += runningStageFraction(stage.id, state);
      runningStage = stage;
      runningState = state;
      break;
    }
    break;
  }

  const allComplete = units >= totalStages;
  const percent = allComplete
    ? 100
    : Math.min(99, Math.round((units / totalStages) * 100));

  if (allComplete) {
    return { percent: 100, label: "Import complete", indeterminate: false };
  }

  if (!runningStage) {
    const completed = stages.filter((stage) => {
      const status = stageState[stage.id]?.status ?? "pending";
      return status === "done" || status === "skipped";
    }).length;
    return {
      percent: Math.round((completed / totalStages) * 100),
      label: completed > 0 ? `Step ${completed + 1} of ${totalStages}` : "Starting import…",
      indeterminate: completed === 0,
    };
  }

  const completedBefore = stages.findIndex((s) => s.id === runningStage.id);
  const stepNumber = completedBefore + 1;
  let label = `Step ${stepNumber} of ${totalStages} — ${runningStage.label}`;

  if (
    runningStage.id === "enrich_mcmaster" &&
    (runningState?.progressTotal ?? 0) > 0
  ) {
    const partTotal = runningState?.progressTotal ?? 0;
    if (runningState?.progressCurrent !== undefined) {
      label = `Step ${stepNumber} of ${totalStages} — part ${runningState.progressCurrent + 1} of ${partTotal}`;
    } else {
      label = `Step ${stepNumber} of ${totalStages} — preparing ${partTotal} hardware lines`;
    }
  }

  const indeterminate =
    runningStage.id === "enrich_mcmaster" &&
    (runningState?.progressTotal ?? 0) > 0 &&
    runningState?.progressCurrent === undefined;

  return { percent, label, indeterminate };
}

function ProgressBar({
  percent,
  indeterminate,
  ariaLabel,
  size = "md",
}: {
  percent: number;
  indeterminate?: boolean;
  ariaLabel: string;
  size?: "md" | "sm";
}) {
  const height = size === "sm" ? "h-1.5" : "h-2";
  return (
    <div
      className={cn("w-full overflow-hidden rounded-full bg-muted", height)}
      role="progressbar"
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={indeterminate ? undefined : percent}
      aria-label={ariaLabel}
    >
      {indeterminate ? (
        <div
          className={cn(
            "h-full w-2/5 animate-pulse rounded-full bg-primary",
            height,
          )}
        />
      ) : (
        <div
          className={cn(
            "h-full rounded-full bg-primary transition-[width] duration-300 ease-out",
            height,
          )}
          style={{ width: `${Math.max(percent, percent > 0 ? 3 : 0)}%` }}
        />
      )}
    </div>
  );
}

function HydrationProgressBar({
  current,
  total,
  indeterminate,
}: {
  current: number;
  total: number;
  indeterminate?: boolean;
}) {
  const percent =
    !indeterminate && total > 0
      ? Math.min(100, Math.round(((current + 1) / total) * 100))
      : undefined;

  return (
    <div className="mt-3 space-y-1">
      <ProgressBar
        percent={percent ?? 0}
        indeterminate={percent === undefined}
        ariaLabel="McMaster listing hydration progress"
        size="sm"
      />
      {total > 0 && (
        <p className="text-xs text-muted-foreground tabular-nums">
          {indeterminate
            ? `Preparing ${total} hardware line${total === 1 ? "" : "s"}…`
            : `Part ${current + 1} of ${total}`}
        </p>
      )}
    </div>
  );
}

function activeStageId(
  stages: ImportStageDefinition[],
  stageState: Partial<Record<ImportStageId, StageState>>,
): ImportStageId | null {
  for (const stage of stages) {
    const status = stageState[stage.id]?.status ?? "pending";
    if (status === "running") return stage.id;
  }
  for (const stage of stages) {
    const status = stageState[stage.id]?.status ?? "pending";
    if (status === "pending") return stage.id;
  }
  return null;
}

interface ImportProgressProps {
  stages: ImportStageDefinition[];
  stageState: Partial<Record<ImportStageId, StageState>>;
  active: boolean;
  previewThumbnail?: string;
  previewTitle?: string;
}

export function ImportProgress({
  stages,
  stageState,
  active,
  previewThumbnail,
  previewTitle,
}: ImportProgressProps) {
  if (!active) return null;

  const displayStages = stages.length > 0 ? stages : DEFAULT_IMPORT_STAGES;
  const scrapeThumb =
    previewThumbnail || stageState.scrape?.thumbnailUrl;
  const currentId = activeStageId(displayStages, stageState);
  const currentStage = currentId
    ? displayStages.find((stage) => stage.id === currentId)
    : null;
  const currentState = currentId ? stageState[currentId] : null;
  const completedCount = displayStages.filter(
    (stage) => stageState[stage.id]?.status === "done",
  ).length;
  const isWorking = displayStages.some(
    (stage) => stageState[stage.id]?.status === "running",
  );
  const pipelineProgress = computePipelineProgress(displayStages, stageState);

  return (
    <div
      className="rounded-lg border border-border bg-muted/30 p-4"
      role="status"
      aria-live="polite"
      aria-label="Import progress"
    >
      <div className="mb-4 flex items-start justify-between gap-4">
        <div className="min-w-0 space-y-1">
          <p className="text-sm font-medium">Import pipeline</p>
          {currentStage && (
            <p className="text-xs text-muted-foreground">
              Step {Math.min(completedCount + 1, displayStages.length)} of{" "}
              {displayStages.length}
              {isWorking ? " — in progress" : ""}
            </p>
          )}
        </div>
        {scrapeThumb && (
          <ProjectThumbnail
            url={scrapeThumb}
            title={previewTitle || "MakerWorld project"}
            size="sm"
          />
        )}
      </div>

      <div className="mb-4 space-y-1.5">
        <div className="flex items-center justify-between gap-3 text-xs text-muted-foreground">
          <span className="min-w-0 truncate">{pipelineProgress.label}</span>
          {!pipelineProgress.indeterminate && (
            <span className="shrink-0 tabular-nums">{pipelineProgress.percent}%</span>
          )}
        </div>
        <ProgressBar
          percent={pipelineProgress.percent}
          indeterminate={pipelineProgress.indeterminate && isWorking}
          ariaLabel="Overall BOM import pipeline progress"
        />
      </div>

      {currentStage && currentState && (
        <div
          className={cn(
            "mb-4 rounded-md border px-3 py-2",
            currentState.status === "running"
              ? "border-primary/40 bg-primary/5"
              : currentState.status === "error"
                ? "border-destructive/30 bg-danger-muted"
                : "border-border bg-card/60",
          )}
        >
          <div className="flex items-start gap-2">
            {currentState.status === "running" && (
              <Loader2 className="mt-0.5 h-4 w-4 shrink-0 animate-spin text-primary" />
            )}
            <div className="min-w-0">
              <p className="text-sm font-medium">{currentStage.label}</p>
              <p
                className={cn(
                  "mt-0.5 text-sm",
                  currentState.status === "error"
                    ? "text-destructive"
                    : "text-muted-foreground",
                )}
              >
                {currentState.message}
              </p>
            </div>
          </div>
        </div>
      )}

      <ol className="space-y-3">
        {displayStages.map((stage, index) => {
          const state = stageState[stage.id] ?? {
            status: "pending" as const,
            message: stage.description,
          };
          const Icon = STATUS_ICON[state.status];
          const isRunning = state.status === "running";

          return (
            <li key={stage.id} className="flex gap-3">
              <div className="flex flex-col items-center">
                <div
                  className={cn(
                    "flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-border bg-card",
                    state.status === "running" && "border-primary",
                    state.status === "done" &&
                      "border-success/30 bg-success-muted",
                    state.status === "error" &&
                      "border-destructive/30 bg-danger-muted",
                  )}
                >
                  <Icon
                    className={cn(
                      "h-4 w-4",
                      STATUS_STYLE[state.status],
                      isRunning && "animate-spin",
                    )}
                  />
                </div>
                {index < displayStages.length - 1 && (
                  <div
                    className={cn(
                      "mt-1 w-px flex-1 min-h-4",
                      state.status === "done"
                        ? "bg-success/40"
                        : "bg-border",
                    )}
                  />
                )}
              </div>
              <div className="min-w-0 flex-1 pb-1">
                <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
                  <p
                    className={cn(
                      "text-sm font-medium",
                      state.status === "pending" && "text-muted-foreground",
                    )}
                  >
                    {stage.label}
                  </p>
                  <span className="text-xs text-muted-foreground">
                    {stage.notebook}
                  </span>
                </div>
                <p
                  className={cn(
                    "mt-0.5 text-sm",
                    state.status === "error"
                      ? "text-destructive"
                      : "text-muted-foreground",
                  )}
                >
                  {state.message}
                </p>
                {stage.id === "enrich_mcmaster" &&
                  isRunning &&
                  (state.progressTotal ?? 0) > 0 && (
                    <HydrationProgressBar
                      current={state.progressCurrent ?? 0}
                      total={state.progressTotal ?? 0}
                      indeterminate={state.progressCurrent === undefined}
                    />
                  )}
              </div>
            </li>
          );
        })}
      </ol>
    </div>
  );
}

export function applyStageEvent(
  prev: Partial<Record<ImportStageId, StageState>>,
  event: ImportStageEvent,
): Partial<Record<ImportStageId, StageState>> {
  const prior = prev[event.stage];
  const thumbnail = event.thumbnail_url
    ? { thumbnailUrl: event.thumbnail_url }
    : prior?.thumbnailUrl
      ? { thumbnailUrl: prior.thumbnailUrl }
      : {};

  let progress: Pick<StageState, "progressCurrent" | "progressTotal"> = {};
  if (event.stage === "enrich_mcmaster") {
    if (event.status === "running") {
      const hydration = parseHydrationProgress(event.debug);
      progress = {
        ...(hydration.progressCurrent !== undefined
          ? { progressCurrent: hydration.progressCurrent }
          : prior?.progressCurrent !== undefined
            ? { progressCurrent: prior.progressCurrent }
            : {}),
        ...(hydration.progressTotal !== undefined
          ? { progressTotal: hydration.progressTotal }
          : prior?.progressTotal !== undefined
            ? { progressTotal: prior.progressTotal }
            : {}),
      };
    } else if (event.status === "done" && prior?.progressTotal) {
      progress = {
        progressCurrent: prior.progressTotal,
        progressTotal: prior.progressTotal,
      };
    }
  }

  return {
    ...prev,
    [event.stage]: {
      status: event.status,
      message: event.message,
      ...thumbnail,
      ...progress,
    },
  };
}

export function initialStageState(
  stages: ImportStageDefinition[],
): Partial<Record<ImportStageId, StageState>> {
  const source = stages.length > 0 ? stages : DEFAULT_IMPORT_STAGES;
  return Object.fromEntries(
    source.map((s) => [s.id, { status: "pending", message: s.description }]),
  ) as Partial<Record<ImportStageId, StageState>>;
}
