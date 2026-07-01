import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Loader2, Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label, Select } from "@/components/ui/select";
import {
  ImportProgress,
  applyStageEvent,
  initialStageState,
  type StageState,
} from "@/components/ImportProgress";
import { BomHistory } from "@/components/BomHistory";
import {
  fetchImportSources,
  fetchImportStages,
  importFileWithProgress,
  importProjectWithProgress,
  type ImportSourcesResponse,
  type ImportStageDefinition,
  type ImportStageId,
  type MakerWorldExample,
} from "@/lib/api";

const DEFAULT_UPLOAD_ACCEPT =
  ".csv,.tsv,.xlsx,.xls,.json,.md,.markdown,.html,.htm,.txt";

export function ImportPage() {
  const [sourceId, setSourceId] = useState("makerworld");
  const [projectUrl, setProjectUrl] = useState("");
  const [exampleUrl, setExampleUrl] = useState("");
  const [importSources, setImportSources] = useState<ImportSourcesResponse | null>(
    null,
  );
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [stages, setStages] = useState<ImportStageDefinition[]>([]);
  const [stageState, setStageState] = useState<
    Partial<Record<ImportStageId, StageState>>
  >({});
  const [historyRefresh, setHistoryRefresh] = useState(0);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const urlInputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();

  const makerworldExamples: MakerWorldExample[] =
    importSources?.makerworld_examples ?? [];
  const uploadAccept =
    importSources?.upload_extensions.map((ext) => ext).join(",") ||
    DEFAULT_UPLOAD_ACCEPT;
  const uploadFormatHint =
    importSources?.upload_formats.join(", ") ||
    "CSV, TSV, XLSX, JSON, Markdown, HTML, plain text";

  const resolvedUrl = projectUrl.trim();

  useEffect(() => {
    fetchImportStages()
      .then((defs) => {
        setStages(defs);
        setStageState(initialStageState(defs));
      })
      .catch(() => {
        /* optional */
      });

    fetchImportSources()
      .then((sources) => {
        setImportSources(sources);
      })
      .catch(() => {
        /* optional */
      });
  }, []);

  function onExamplePick(url: string) {
    setExampleUrl(url);
    if (url) {
      setProjectUrl(url);
      urlInputRef.current?.focus();
    }
  }

  function resetProgress() {
    if (stages.length) {
      setStageState(initialStageState(stages));
    }
  }

  function onStage(event: Parameters<typeof applyStageEvent>[1]) {
    setStageState((prev) => applyStageEvent(prev, event));
  }

  async function handleUrlImport(e: React.FormEvent) {
    e.preventDefault();
    if (!resolvedUrl) return;

    setError(null);
    setLoading(true);
    resetProgress();

    try {
      const result = await importProjectWithProgress(resolvedUrl, onStage);
      setHistoryRefresh((n) => n + 1);
      navigate(`/bom/${result.project_id}`, {
        state: { project: result.project },
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Import failed");
    } finally {
      setLoading(false);
    }
  }

  async function handleFileImport(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return;

    setError(null);
    setLoading(true);
    resetProgress();

    try {
      const result = await importFileWithProgress(file, onStage);
      setHistoryRefresh((n) => n + 1);
      navigate(`/bom/${result.project_id}`, {
        state: { project: result.project },
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Import project</CardTitle>
          <CardDescription>
            Paste a MakerWorld project URL or pick an example below.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleUrlImport} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="import-source">Source</Label>
              <Select
                id="import-source"
                value={sourceId}
                onChange={(e) => setSourceId(e.target.value)}
                disabled={loading}
              >
                {(importSources?.sources ?? [{ id: "makerworld", label: "MakerWorld project" }]).map(
                  (source) => (
                    <option key={source.id} value={source.id}>
                      {source.label}
                    </option>
                  ),
                )}
              </Select>
            </div>

            {sourceId === "makerworld" && (
              <>
                <div className="space-y-2">
                  <Label htmlFor="makerworld-url">MakerWorld project URL</Label>
                  <Input
                    ref={urlInputRef}
                    id="makerworld-url"
                    type="url"
                    placeholder="https://makerworld.com/en/models/..."
                    value={projectUrl}
                    onChange={(e) => setProjectUrl(e.target.value)}
                    required
                    disabled={loading}
                    autoFocus
                  />
                </div>

                {makerworldExamples.length > 0 && (
                  <div className="space-y-2">
                    <Label htmlFor="makerworld-example">Example project (optional)</Label>
                    <Select
                      id="makerworld-example"
                      value={exampleUrl}
                      onChange={(e) => onExamplePick(e.target.value)}
                      disabled={loading}
                    >
                      <option value="">— paste URL above or choose example —</option>
                      {makerworldExamples.map((example) => (
                        <option key={example.url} value={example.url}>
                          {example.label}
                        </option>
                      ))}
                    </Select>
                  </div>
                )}
              </>
            )}

            <Button type="submit" disabled={loading || !resolvedUrl}>
              {loading && resolvedUrl ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Importing…
                </>
              ) : (
                "Import"
              )}
            </Button>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Upload BOM file</CardTitle>
          <CardDescription>
            Upload any structured BOM we can parse — spreadsheets, JSON part
            lists, or hardware lists in Markdown/HTML/text.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleFileImport} className="space-y-4">
            <input
              ref={fileInputRef}
              type="file"
              accept={uploadAccept}
              className="hidden"
              disabled={loading}
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />
            <div className="flex flex-wrap items-center gap-3">
              <Button
                type="button"
                variant="outline"
                disabled={loading}
                onClick={() => fileInputRef.current?.click()}
              >
                <Upload className="h-4 w-4" />
                Choose file
              </Button>
              <span className="text-sm text-muted-foreground">
                {file ? file.name : "No file chosen"}
              </span>
            </div>
            <p className="text-xs text-muted-foreground">{uploadFormatHint}</p>
            <Button type="submit" disabled={loading || !file}>
              {loading && file ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Uploading…
                </>
              ) : (
                "Upload & match"
              )}
            </Button>
          </form>
        </CardContent>
      </Card>

      {error && (
        <p className="text-sm text-destructive" role="alert">
          {error}
        </p>
      )}

      <ImportProgress
        stages={stages}
        stageState={stageState}
        active={
          loading ||
          Object.values(stageState).some((s) => s && s.status !== "pending")
        }
      />

      <BomHistory refreshKey={historyRefresh} />
    </div>
  );
}
