import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

export interface DebugLogEntry {
  id: string;
  timestamp: string;
  source: "client" | "server" | "pipeline";
  category: string;
  message: string;
  data?: Record<string, unknown>;
}

interface DebugStatus {
  debug: boolean;
  python?: string;
  proxy_env?: Record<string, string>;
}

interface DebugContextValue {
  available: boolean;
  panelOpen: boolean;
  setPanelOpen: (open: boolean) => void;
  togglePanel: () => void;
  backendDebug: boolean;
  entries: DebugLogEntry[];
  log: (
    source: DebugLogEntry["source"],
    category: string,
    message: string,
    data?: Record<string, unknown>,
  ) => void;
  logPipeline: (
    stage: string,
    status: string,
    message: string,
    data?: Record<string, unknown>,
  ) => void;
  refreshServerLogs: () => Promise<void>;
  clearLogs: () => void;
}

const DebugContext = createContext<DebugContextValue | null>(null);

const MAX_ENTRIES = 150;
const UI_STORAGE_KEY = "makerworld-bom-debug-panel";

function nextId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

const frontendDebug =
  import.meta.env.VITE_DEBUG === "true" || import.meta.env.DEV;

type PipelineLogger = (
  stage: string,
  status: string,
  message: string,
  data?: Record<string, unknown>,
) => void;

type FetchLogger = (
  input: RequestInfo | URL,
  init?: RequestInit,
) => Promise<Response>;

let pipelineLogger: PipelineLogger | null = null;
let debugFetchFn: FetchLogger | null = null;

export function registerDebugHooks(hooks: {
  logPipeline: PipelineLogger;
  debugFetch: FetchLogger;
}) {
  pipelineLogger = hooks.logPipeline;
  debugFetchFn = hooks.debugFetch;
}

export function getPipelineLogger() {
  return pipelineLogger;
}

export function getDebugFetch() {
  return debugFetchFn;
}

export function DebugProvider({ children }: { children: React.ReactNode }) {
  const [panelOpen, setPanelOpen] = useState(
    () => localStorage.getItem(UI_STORAGE_KEY) === "open",
  );
  const [backendDebug, setBackendDebug] = useState(false);
  const [entries, setEntries] = useState<DebugLogEntry[]>([]);

  useEffect(() => {
    localStorage.setItem(UI_STORAGE_KEY, panelOpen ? "open" : "closed");
  }, [panelOpen]);

  useEffect(() => {
    fetch("/api/debug")
      .then((res) => (res.ok ? res.json() : null))
      .then((body: DebugStatus | null) => {
        if (body) setBackendDebug(Boolean(body.debug));
      })
      .catch(() => {});
  }, []);

  const log = useCallback(
    (
      source: DebugLogEntry["source"],
      category: string,
      message: string,
      data?: Record<string, unknown>,
    ) => {
      setEntries((prev) => {
        const entry: DebugLogEntry = {
          id: nextId(),
          timestamp: new Date().toISOString(),
          source,
          category,
          message,
          data,
        };
        return [...prev, entry].slice(-MAX_ENTRIES);
      });
    },
    [],
  );

  const logPipeline = useCallback(
    (
      stage: string,
      status: string,
      message: string,
      data?: Record<string, unknown>,
    ) => {
      log("pipeline", stage, `[${status}] ${message}`, data);
    },
    [log],
  );

  useEffect(() => {
    registerDebugHooks({
      logPipeline,
      debugFetch: (input, init) => debugFetch(input, init, log),
    });
    return () =>
      registerDebugHooks({
        logPipeline: () => {},
        debugFetch: fetch,
      });
  }, [log, logPipeline]);

  const refreshServerLogs = useCallback(async () => {
    if (!backendDebug) return;
    const res = await fetch("/api/debug/logs?limit=100");
    if (!res.ok) return;
    const body = await res.json();
    const serverEntries: DebugLogEntry[] = (body.entries ?? []).map(
      (e: {
        timestamp: string;
        category: string;
        message: string;
        data?: Record<string, unknown>;
      }) => ({
        id: `srv-${e.timestamp}-${e.category}`,
        timestamp: e.timestamp,
        source: "server" as const,
        category: e.category,
        message: e.message,
        data: e.data,
      }),
    );
    setEntries((prev) => {
      const clientOnly = prev.filter((e) => e.source !== "server");
      return [...clientOnly, ...serverEntries].slice(-MAX_ENTRIES);
    });
  }, [backendDebug]);

  useEffect(() => {
    if (!panelOpen || !backendDebug) return;
    void refreshServerLogs();
    const timer = window.setInterval(() => void refreshServerLogs(), 3000);
    return () => window.clearInterval(timer);
  }, [panelOpen, backendDebug, refreshServerLogs]);

  const clearLogs = useCallback(() => {
    setEntries([]);
    if (backendDebug) {
      void fetch("/api/debug/logs", { method: "DELETE" });
    }
  }, [backendDebug]);

  const value = useMemo(
    () => ({
      available: frontendDebug || backendDebug,
      panelOpen,
      setPanelOpen,
      togglePanel: () => setPanelOpen((o) => !o),
      backendDebug,
      entries,
      log,
      logPipeline,
      refreshServerLogs,
      clearLogs,
    }),
    [
      panelOpen,
      backendDebug,
      entries,
      log,
      logPipeline,
      refreshServerLogs,
      clearLogs,
    ],
  );

  return (
    <DebugContext.Provider value={value}>{children}</DebugContext.Provider>
  );
}

export function useDebug() {
  const ctx = useContext(DebugContext);
  if (!ctx) {
    throw new Error("useDebug must be used within DebugProvider");
  }
  return ctx;
}

export async function debugFetch(
  input: RequestInfo | URL,
  init?: RequestInit,
  log?: DebugContextValue["log"],
): Promise<Response> {
  const method = init?.method ?? "GET";
  const url = typeof input === "string" ? input : input.toString();
  const started = performance.now();

  log?.("client", "fetch", `${method} ${url}`);

  try {
    const res = await fetch(input, init);
    const ms = Math.round(performance.now() - started);
    log?.("client", "fetch", `${method} ${url} → ${res.status} (${ms}ms)`);
    return res;
  } catch (err) {
    const ms = Math.round(performance.now() - started);
    log?.("client", "fetch", `${method} ${url} → failed (${ms}ms)`, {
      error: err instanceof Error ? err.message : String(err),
    });
    throw err;
  }
}
