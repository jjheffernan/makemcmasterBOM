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

  const scrapeThumb =
    previewThumbnail || stageState.scrape?.thumbnailUrl;

  return (
    <div
      className="rounded-lg border border-border bg-muted/30 p-4"
      role="status"
      aria-live="polite"
      aria-label="Import progress"
    >
      <div className="mb-4 flex items-start justify-between gap-4">
        <p className="text-sm font-medium">Import pipeline</p>
        {scrapeThumb && (
          <ProjectThumbnail
            url={scrapeThumb}
            title={previewTitle || "MakerWorld project"}
            size="sm"
          />
        )}
      </div>
      <ol className="space-y-3">
        {stages.map((stage, index) => {
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
                {index < stages.length - 1 && (
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
  return {
    ...prev,
    [event.stage]: {
      status: event.status,
      message: event.message,
      ...(event.thumbnail_url
        ? { thumbnailUrl: event.thumbnail_url }
        : prev[event.stage]?.thumbnailUrl
          ? { thumbnailUrl: prev[event.stage]?.thumbnailUrl }
          : {}),
    },
  };
}

export function initialStageState(
  stages: ImportStageDefinition[],
): Partial<Record<ImportStageId, StageState>> {
  return Object.fromEntries(
    stages.map((s) => [s.id, { status: "pending", message: s.description }]),
  ) as Partial<Record<ImportStageId, StageState>>;
}
