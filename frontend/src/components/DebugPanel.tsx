import { Bug, ChevronDown, ChevronUp, Trash2, X } from "lucide-react";
import { useDebug } from "@/lib/debug";
import { cn } from "@/lib/utils";

function sourceColor(source: string) {
  switch (source) {
    case "server":
      return "text-link";
    case "pipeline":
      return "text-primary";
    default:
      return "text-muted-foreground";
  }
}

export function DebugToggle() {
  const { available, panelOpen, togglePanel, backendDebug } = useDebug();
  if (!available) return null;

  return (
    <button
      type="button"
      onClick={togglePanel}
      title={
        backendDebug
          ? "Debug panel (server DEBUG=1)"
          : "Debug panel (client only — set DEBUG=1 on API)"
      }
      className={cn(
        "inline-flex h-9 w-9 items-center justify-center rounded-md transition-colors",
        panelOpen
          ? "bg-primary/15 text-primary"
          : "opacity-75 hover:bg-foreground/10 hover:opacity-100",
      )}
      aria-label="Toggle debug panel"
      aria-pressed={panelOpen}
    >
      <Bug className="h-4 w-4" />
    </button>
  );
}

export function DebugPanel() {
  const {
    available,
    panelOpen,
    setPanelOpen,
    backendDebug,
    entries,
    clearLogs,
    refreshServerLogs,
  } = useDebug();

  if (!available || !panelOpen) return null;

  return (
    <div className="fixed inset-x-0 bottom-0 z-50 border-t border-border bg-card shadow-2xl">
      <div className="mx-auto flex max-h-[40vh] max-w-7xl flex-col">
        <div className="flex items-center justify-between gap-2 border-b border-border px-4 py-2">
          <div className="flex items-center gap-2 text-sm font-medium">
            <Bug className="h-4 w-4 text-primary" />
            Debug
            <span
              className={cn(
                "rounded px-1.5 py-0.5 text-xs font-normal",
                backendDebug
                  ? "bg-primary/15 text-primary"
                  : "bg-muted text-muted-foreground",
              )}
            >
              API {backendDebug ? "on" : "off"}
            </span>
          </div>
          <div className="flex items-center gap-1">
            {backendDebug && (
              <button
                type="button"
                onClick={() => void refreshServerLogs()}
                className="rounded px-2 py-1 text-xs text-muted-foreground hover:bg-muted"
              >
                Refresh server logs
              </button>
            )}
            <button
              type="button"
              onClick={clearLogs}
              className="inline-flex items-center gap-1 rounded px-2 py-1 text-xs text-muted-foreground hover:bg-muted"
            >
              <Trash2 className="h-3 w-3" />
              Clear
            </button>
            <button
              type="button"
              onClick={() => setPanelOpen(false)}
              className="inline-flex h-7 w-7 items-center justify-center rounded hover:bg-muted"
              aria-label="Close debug panel"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>

        {!backendDebug && (
          <p className="border-b border-border bg-muted/40 px-4 py-2 text-xs text-muted-foreground">
            Server debug is off. Restart with{" "}
            <code className="rounded bg-muted px-1">./scripts/dev.sh --debug</code>{" "}
            or set <code className="rounded bg-muted px-1">DEBUG=1</code> in{" "}
            <code className="rounded bg-muted px-1">.env</code> for scrape details
            and tracebacks.
          </p>
        )}

        <div className="overflow-y-auto px-4 py-2 font-mono text-xs">
          {entries.length === 0 ? (
            <p className="py-4 text-center text-muted-foreground">
              No log entries yet. Run an import to see pipeline events.
            </p>
          ) : (
            <ul className="space-y-1">
              {entries.map((entry) => (
                <LogLine key={entry.id} entry={entry} />
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}

function LogLine({
  entry,
}: {
  entry: {
    timestamp: string;
    source: string;
    category: string;
    message: string;
    data?: Record<string, unknown>;
  };
}) {
  const time = entry.timestamp.slice(11, 23);
  const hasData = entry.data && Object.keys(entry.data).length > 0;

  return (
    <li className="group">
      <details className={cn(!hasData && "pointer-events-none")}>
        <summary
          className={cn(
            "flex cursor-default list-none items-baseline gap-2 py-0.5",
            hasData && "cursor-pointer hover:bg-muted/50",
          )}
        >
          <span className="shrink-0 text-muted-foreground">{time}</span>
          <span
            className={cn("shrink-0 uppercase", sourceColor(entry.source))}
          >
            {entry.source}
          </span>
          <span className="shrink-0 text-muted-foreground">
            [{entry.category}]
          </span>
          <span className="min-w-0 truncate">{entry.message}</span>
          {hasData && (
            <ChevronDown className="ml-auto h-3 w-3 shrink-0 opacity-0 group-open:hidden group-hover:opacity-50" />
          )}
          {hasData && (
            <ChevronUp className="ml-auto hidden h-3 w-3 shrink-0 group-open:block opacity-50" />
          )}
        </summary>
        {hasData && (
          <pre className="mb-1 ml-16 overflow-x-auto rounded bg-muted/60 p-2 text-[11px] leading-relaxed">
            {JSON.stringify(entry.data, null, 2)}
          </pre>
        )}
      </details>
    </li>
  );
}
