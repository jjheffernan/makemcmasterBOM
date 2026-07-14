import { getDebugFetch, getPipelineLogger } from "./debug";

async function apiFetch(
  input: RequestInfo | URL,
  init?: RequestInit,
): Promise<Response> {
  const dbg = getDebugFetch();
  if (dbg) return dbg(input, init);
  return fetch(input, init);
}

export type ImportStageId =
  | "validate"
  | "scrape"
  | "extract_bom"
  | "parse_bom"
  | "match_mcmaster"
  | "enrich_mcmaster"
  | "finalize";

export type ImportStageStatus =
  | "pending"
  | "running"
  | "done"
  | "error"
  | "skipped";

export interface ImportStageDefinition {
  id: ImportStageId;
  notebook: string;
  label: string;
  description: string;
}

export interface ImportStageEvent {
  stage: ImportStageId;
  status: ImportStageStatus;
  message: string;
  thumbnail_url?: string | null;
  debug?: Record<string, unknown> | null;
}

export interface ImportResponse {
  project_id: string;
  project: Project;
}

export type McMasterStatus =
  | "likely"
  | "possible"
  | "unlikely"
  | "not_applicable";

export type MatchTier =
  | "catalog"
  | "rule"
  | "part_number"
  | "filtered_browse"
  | "category_search"
  | "site_search"
  | "api_verified"
  | "";

export type HardwareMatchStatus =
  | "verified"
  | "corrected"
  | "size_mismatch"
  | "length_mismatch"
  | "spec_conflict"
  | "length_unknown"
  | "unchecked"
  | "not_applicable";

export interface MatchAlternative {
  mcmaster_url: string;
  mcmaster_part_number: string;
  mcmaster_category: string;
  mcmaster_metacategory?: string;
  mcmaster_metacategory_label?: string;
  match_tier: MatchTier;
  confidence: number;
  confidence_low?: number | null;
  confidence_high?: number | null;
  mcmaster_reason: string;
  guess_scope?: "same_size" | "wider_scope";
  guess_label?: string;
}

export interface BrowseFinishOption {
  finish_id: string;
  label: string;
  mcmaster_url: string;
  mcmaster_part_number?: string;
  product_url?: string;
  unit_cost?: number | null;
  price_min_qty?: number;
  price_batch_cost?: number | null;
  price_listing_note?: string;
}

export interface Part {
  quantity: number;
  original_name: string;
  normalized_name: string;
  specification: string;
  notes: string;
  mcmaster_url: string;
  mcmaster_part_number: string;
  mcmaster_category: string;
  mcmaster_metacategory?: string;
  mcmaster_metacategory_label?: string;
  confidence: number;
  confidence_low?: number | null;
  confidence_high?: number | null;
  mcmaster_status: McMasterStatus;
  mcmaster_reason: string;
  match_tier?: MatchTier;
  match_alternatives?: MatchAlternative[];
  browse_finish_options?: BrowseFinishOption[];
  selected_finish_id?: string;
  mcmaster_detail_description?: string;
  mcmaster_product_status?: string;
  hardware_diameter_mm?: number | null;
  hardware_length_mm?: number | null;
  hardware_match_status?: HardwareMatchStatus;
  price_min_qty?: number;
  price_batch_cost?: number | null;
  unit_cost?: number | null;
  price_source?: string;
  price_listing_note?: string;
  match_selection_policy?: string;
  match_option_count?: number;
}

export interface Project {
  title: string;
  makerworld_url: string;
  description: string;
  thumbnail_url?: string;
  parts: Part[];
  bom_status?: "file" | "embedded" | "description" | "none" | "upload";
  warnings?: string[];
  bom_headings?: Partial<Record<"bom" | "not_applicable", string>>;
}

export interface ProjectHistoryItem {
  project_id: string;
  title: string;
  thumbnail_url: string;
  makerworld_url: string;
  parts_count: number;
  bom_status: Project["bom_status"];
  imported_at: string;
  updated_at: string;
}

export interface BomHistoryResponse {
  items: ProjectHistoryItem[];
  limit: number;
}

export interface NotebookInfo {
  filename: string;
  title: string;
  description: string;
  stage: string;
  jupyter_path: string;
}

export interface NotebooksResponse {
  notebooks: NotebookInfo[];
  jupyter_url: string;
}

export interface ImportSourceDefinition {
  id: string;
  label: string;
  description: string;
}

export interface MakerWorldExample {
  url: string;
  label: string;
}

export interface ImportSourcesResponse {
  sources: ImportSourceDefinition[];
  makerworld_examples: MakerWorldExample[];
  upload_formats: string[];
  upload_extensions: string[];
}

export const CUSTOM_MAKERWORLD_URL = "__custom__";

export async function fetchImportStages(): Promise<ImportStageDefinition[]> {
  const res = await apiFetch("/api/import/stages");
  if (!res.ok) {
    if (res.status === 404) return [];
    throw new Error("Failed to load import stages");
  }
  const body = await res.json();
  return body.stages;
}

export async function fetchImportSources(): Promise<ImportSourcesResponse> {
  const res = await apiFetch("/api/import/sources");
  if (!res.ok) {
    throw new Error("Failed to load import options");
  }
  return res.json();
}

async function readImportStream(
  res: Response,
  onStage: (event: ImportStageEvent) => void,
): Promise<ImportResponse> {
  if (!res.body) {
    throw new Error("Import failed — empty response from server");
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";

    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      const payload = JSON.parse(line.slice(6));

      if (payload.type === "stage") {
        const event: ImportStageEvent = {
          stage: payload.stage,
          status: payload.status,
          message: payload.message,
          thumbnail_url: payload.thumbnail_url,
          debug: payload.debug,
        };
        getPipelineLogger()?.(
          event.stage,
          event.status,
          event.message,
          event.debug ?? undefined,
        );
        onStage(event);
      } else if (payload.type === "complete") {
        getPipelineLogger()?.(
          "import",
          "done",
          `Project ${payload.project_id} ready`,
          { parts: payload.project?.parts?.length },
        );
        return {
          project_id: payload.project_id,
          project: payload.project,
        };
      } else if (payload.type === "error") {
        getPipelineLogger()?.("import", "error", payload.detail ?? "Import failed", {
          traceback: payload.traceback,
        });
        const detail = payload.detail ?? "Import failed";
        throw new Error(
          payload.traceback ? `${detail}\n\n${payload.traceback}` : detail,
        );
      }
    }
  }

  throw new Error("Import ended unexpectedly");
}

export async function importProjectWithProgress(
  url: string,
  onStage: (event: ImportStageEvent) => void,
): Promise<ImportResponse> {
  const res = await apiFetch("/api/import/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });

  if (res.status === 404) {
    onStage({
      stage: "validate",
      status: "running",
      message: "Connecting to API (legacy mode)…",
    });
    const result = await importProject(url);
    onStage({
      stage: "finalize",
      status: "done",
      message: "Ready to edit",
    });
    return result;
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    const detail = err.detail;
    throw new Error(
      typeof detail === "string"
        ? detail
        : "Import failed — is the API running on port 8000?",
    );
  }

  return readImportStream(res, onStage);
}

export async function importFileWithProgress(
  file: File,
  onStage: (event: ImportStageEvent) => void,
  title = "",
): Promise<ImportResponse> {
  const form = new FormData();
  form.append("file", file);
  if (title.trim()) form.append("title", title.trim());

  const res = await apiFetch("/api/import/file/stream", {
    method: "POST",
    body: form,
  });

  if (res.status === 404) {
    onStage({
      stage: "validate",
      status: "running",
      message: "Connecting to API (legacy mode)…",
    });
    const fallback = new FormData();
    fallback.append("file", file);
    if (title.trim()) fallback.append("title", title.trim());
    const plain = await apiFetch("/api/import/file", {
      method: "POST",
      body: fallback,
    });
    if (!plain.ok) {
      const err = await plain.json().catch(() => ({}));
      throw new Error(
        typeof err.detail === "string"
          ? err.detail
          : "BOM upload failed — restart ./scripts/dev.sh to load the latest API",
      );
    }
    const result = await plain.json();
    onStage({
      stage: "finalize",
      status: "done",
      message: "Ready to edit",
    });
    return result;
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    const detail = err.detail;
    throw new Error(
      typeof detail === "string"
        ? detail
        : "BOM upload failed — is the API running on port 8000?",
    );
  }

  return readImportStream(res, onStage);
}

export async function importProject(url: string): Promise<ImportResponse> {
  const res = await apiFetch("/api/import", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Import failed");
  }
  return res.json();
}

export interface SpecificationIssue {
  part_index: number;
  original_name: string;
  specification: string;
  code: string;
  message: string;
  severity: "error" | "warning";
  hint: string;
}

export interface ValidateSpecificationsResponse {
  issues: SpecificationIssue[];
  error_count: number;
  warning_count: number;
}

export async function validateSpecifications(
  parts: Part[],
): Promise<ValidateSpecificationsResponse> {
  const res = await apiFetch("/api/bom/validate-specifications", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ parts }),
  });
  if (!res.ok) {
    throw new Error("Failed to validate specifications");
  }
  return res.json();
}

export async function getProject(projectId: string): Promise<Project> {
  const res = await apiFetch(`/api/bom/${projectId}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(
      typeof err.detail === "string"
        ? err.detail
        : "Project not found — the server may have restarted. Please import again.",
    );
  }
  return res.json();
}

export async function updateProject(
  projectId: string,
  parts: Part[],
  bomHeadings?: Project["bom_headings"],
): Promise<Project> {
  const res = await apiFetch(`/api/bom/${projectId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      parts,
      ...(bomHeadings != null ? { bom_headings: bomHeadings } : {}),
    }),
  });
  if (!res.ok) throw new Error("Update failed");
  return res.json();
}

export type BomExportFormat = "csv" | "tsv" | "xlsx";

export function exportBomUrl(
  projectId: string,
  format: BomExportFormat = "csv",
): string {
  const params = format === "csv" ? "" : `?format=${format}`;
  return `/api/bom/${projectId}/export${params}`;
}

/** @deprecated Prefer exportBomUrl — kept for callers that always want CSV. */
export function exportCsvUrl(projectId: string): string {
  return exportBomUrl(projectId, "csv");
}

export async function fetchBomHistory(): Promise<BomHistoryResponse> {
  const res = await apiFetch("/api/bom/history");
  if (!res.ok) throw new Error("Failed to load BOM history");
  return res.json();
}

export async function listNotebooks(): Promise<NotebooksResponse> {
  const res = await apiFetch("/api/notebooks");
  if (!res.ok) throw new Error("Failed to load notebooks");
  return res.json();
}

export type ReportSide = "mcmaster" | "makerworld";

export type MatchIssueType =
  | "wrong_part_number"
  | "wrong_category_or_search"
  | "missed_hardware"
  | "wrong_finish_or_material"
  | "should_be_not_applicable"
  | "other";

export type MakerWorldIssueType =
  | "makerworld_wrong_line"
  | "makerworld_missing_hardware"
  | "makerworld_wrong_quantity"
  | "makerworld_parse_error"
  | "makerworld_other";

export type AnyIssueType = MatchIssueType | MakerWorldIssueType;

export interface MatchErrorReportRequest {
  project_id: string;
  project_title?: string;
  makerworld_url?: string;
  report_side?: ReportSide;
  part_index?: number | null;
  part?: Part | null;
  issue_type: AnyIssueType;
  message: string;
  expected_part_number?: string;
  expected_url?: string;
  expected_finish?: string;
  makerworld_line_text?: string;
  expected_line_text?: string;
  expected_quantity?: number | null;
  parse_context?: string;
  page_url?: string;
  reporter_email?: string;
}

export interface FeedbackDispatchChannelResult {
  channel: "email" | "github" | "webhook";
  ok: boolean;
  detail: string;
  url: string;
}

export interface MatchErrorReportResponse {
  id: string;
  reported_at: string;
  message: string;
  dispatch?: FeedbackDispatchChannelResult[];
}

export interface SyncPricingResponse {
  parts: Part[];
  synced_count: number;
}

export async function syncPartsPricing(
  parts: Part[],
): Promise<SyncPricingResponse> {
  const res = await apiFetch("/api/bom/sync-pricing", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ parts }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(
      typeof err.detail === "string"
        ? err.detail
        : "Could not sync pricing from McMaster listings",
    );
  }
  return res.json();
}

export async function submitMatchErrorReport(
  body: MatchErrorReportRequest,
): Promise<MatchErrorReportResponse> {
  const res = await apiFetch("/api/feedback/match-error", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(
      typeof err.detail === "string"
        ? err.detail
        : "Could not submit report — is the API running?",
    );
  }
  return res.json();
}
