import { useEffect, useRef, useState } from "react";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label, Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import {
  submitMatchErrorReport,
  type MatchIssueType,
  type Part,
  type Project,
} from "@/lib/api";
import { formatConfidence, matchTierLabel } from "@/lib/mcmaster";

const ISSUE_OPTIONS: { value: MatchIssueType; label: string }[] = [
  {
    value: "wrong_part_number",
    label: "Wrong McMaster part number / SKU",
  },
  {
    value: "wrong_category_or_search",
    label: "Wrong category or search link (not the right product type)",
  },
  {
    value: "missed_hardware",
    label: "Missed hardware — should have matched McMaster",
  },
  {
    value: "wrong_finish_or_material",
    label: "Wrong finish or material (e.g. stainless vs black oxide)",
  },
  {
    value: "should_be_not_applicable",
    label: "Should not match McMaster (3D print, electronics, etc.)",
  },
  { value: "other", label: "Other matching problem" },
];

export interface ReportMatchErrorDialogProps {
  open: boolean;
  onClose: () => void;
  projectId: string;
  project: Project;
  parts: Part[];
  initialPartIndex?: number | null;
}

function partSummary(part: Part): string {
  const bits = [part.original_name];
  if (part.specification) bits.push(part.specification);
  return bits.join(" · ");
}

function matchSummary(part: Part): string {
  const tier = part.match_tier ? matchTierLabel(part.match_tier) : "—";
  const sku = part.mcmaster_part_number || "no SKU";
  return `${tier} · ${sku} · ${formatConfidence(part)}`;
}

export function ReportMatchErrorDialog({
  open,
  onClose,
  projectId,
  project,
  parts,
  initialPartIndex = null,
}: ReportMatchErrorDialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [partIndex, setPartIndex] = useState<string>(
    initialPartIndex != null ? String(initialPartIndex) : "",
  );
  const [issueType, setIssueType] = useState<MatchIssueType>("wrong_part_number");
  const [message, setMessage] = useState("");
  const [expectedPartNumber, setExpectedPartNumber] = useState("");
  const [expectedUrl, setExpectedUrl] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (open) {
      setPartIndex(initialPartIndex != null ? String(initialPartIndex) : "");
      setIssueType("wrong_part_number");
      setMessage("");
      setExpectedPartNumber("");
      setExpectedUrl("");
      setError(null);
      setSuccess(false);
      dialog.showModal();
    } else {
      dialog.close();
    }
  }, [open, initialPartIndex]);

  const selectedPart =
    partIndex !== "" && !Number.isNaN(Number(partIndex))
      ? parts[Number(partIndex)]
      : undefined;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!message.trim()) {
      setError("Please describe what the matcher got wrong.");
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      await submitMatchErrorReport({
        project_id: projectId,
        project_title: project.title,
        makerworld_url: project.makerworld_url,
        part_index: partIndex !== "" ? Number(partIndex) : null,
        part: selectedPart ?? null,
        issue_type: issueType,
        message: message.trim(),
        expected_part_number: expectedPartNumber.trim(),
        expected_url: expectedUrl.trim(),
      });
      setSuccess(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not submit report");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <dialog
      ref={dialogRef}
      className="w-[min(100%,32rem)] max-h-[90vh] overflow-y-auto rounded-[var(--radius-md)] border border-border bg-card p-0 text-foreground shadow-lg backdrop:bg-black/40 open:animate-in"
      onClose={onClose}
      onCancel={onClose}
    >
      <form onSubmit={handleSubmit} className="space-y-4 p-6">
        <div>
          <h2 className="text-lg font-semibold">Report matching error</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Help us improve hardware matching. We save the BOM line and current
            McMaster guess with your notes.
          </p>
        </div>

        {success ? (
          <div className="space-y-4">
            <p className="rounded-lg border border-success/30 bg-success/10 px-4 py-3 text-sm text-success">
              Thank you — your report was saved and will help tune the matcher.
            </p>
            <Button type="button" onClick={onClose}>
              Close
            </Button>
          </div>
        ) : (
          <>
            {parts.length > 0 && (
              <div className="space-y-2">
                <Label htmlFor="report-part">BOM line (optional)</Label>
                <Select
                  id="report-part"
                  value={partIndex}
                  onChange={(e) => setPartIndex(e.target.value)}
                  disabled={submitting}
                >
                  <option value="">General — whole project / multiple lines</option>
                  {parts.map((part, index) => (
                    <option key={index} value={String(index)}>
                      {partSummary(part)}
                    </option>
                  ))}
                </Select>
              </div>
            )}

            {selectedPart && (
              <div className="rounded-lg border border-border bg-muted/30 px-3 py-2 text-xs text-muted-foreground">
                <p className="font-medium text-foreground">Current match</p>
                <p className="mt-1">{matchSummary(selectedPart)}</p>
                {selectedPart.mcmaster_url && (
                  <p className="mt-1 truncate font-mono">{selectedPart.mcmaster_url}</p>
                )}
              </div>
            )}

            <div className="space-y-2">
              <Label htmlFor="report-issue">What went wrong?</Label>
              <Select
                id="report-issue"
                value={issueType}
                onChange={(e) => setIssueType(e.target.value as MatchIssueType)}
                disabled={submitting}
                required
              >
                {ISSUE_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="report-message">Details</Label>
              <Textarea
                id="report-message"
                placeholder="What should we have picked instead? Any context from the MakerWorld BOM?"
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                disabled={submitting}
                required
                rows={4}
              />
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="report-expected-sku">Correct part # (optional)</Label>
                <Input
                  id="report-expected-sku"
                  placeholder="e.g. 91290A120"
                  value={expectedPartNumber}
                  onChange={(e) => setExpectedPartNumber(e.target.value)}
                  disabled={submitting}
                  className="font-mono text-sm"
                />
              </div>
              <div className="space-y-2 sm:col-span-2">
                <Label htmlFor="report-expected-url">Correct McMaster URL (optional)</Label>
                <Input
                  id="report-expected-url"
                  type="url"
                  placeholder="https://www.mcmaster.com/…"
                  value={expectedUrl}
                  onChange={(e) => setExpectedUrl(e.target.value)}
                  disabled={submitting}
                  className="font-mono text-xs"
                />
              </div>
            </div>

            {error && (
              <p className="text-sm text-destructive" role="alert">
                {error}
              </p>
            )}

            <div className="flex flex-wrap justify-end gap-2 pt-2">
              <Button
                type="button"
                variant="outline"
                onClick={onClose}
                disabled={submitting}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={submitting}>
                {submitting ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Sending…
                  </>
                ) : (
                  "Submit report"
                )}
              </Button>
            </div>
          </>
        )}
      </form>
    </dialog>
  );
}
