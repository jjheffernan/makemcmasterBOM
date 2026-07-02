import { useCallback, useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { useLocation } from "react-router-dom";
import { Loader2, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  submitMatchErrorReport,
  type Part,
  type Project,
  type ReportSide,
} from "@/lib/api";
import { cn } from "@/lib/utils";
import { REPORT_SIDES } from "@/components/reportError/config";
import {
  emptyReportForm,
  ReportErrorFormFields,
  reportFormFromPart,
  type ReportFormState,
} from "@/components/reportError/ReportErrorFormFields";

export interface ReportMatchErrorDialogProps {
  open: boolean;
  onClose: () => void;
  projectId?: string;
  project?: Project;
  parts?: Part[];
  initialPartIndex?: number | null;
}

function parseOptionalQuantity(value: string): number | null {
  const trimmed = value.trim();
  if (!trimmed) return null;
  const qty = Number(trimmed);
  return Number.isFinite(qty) && qty >= 0 ? qty : null;
}

function validateForm(reportSide: ReportSide, form: ReportFormState): string | null {
  if (!form.message.trim()) {
    return "Please describe what went wrong.";
  }

  if (reportSide === "mcmaster") {
    if (form.issueType === "missed_hardware" && !form.partIndex && !form.expectedLineText.trim()) {
      return "Select a BOM line or name the hardware we missed.";
    }
    return null;
  }

  if (form.issueType === "makerworld_missing_hardware" && !form.expectedLineText.trim()) {
    return "Describe the hardware missing from the MakerWorld BOM.";
  }
  if (
    (form.issueType === "makerworld_wrong_line" ||
      form.issueType === "makerworld_wrong_quantity") &&
    !form.partIndex
  ) {
    return "Select the BOM line this report is about.";
  }
  if (
    form.issueType === "makerworld_wrong_quantity" &&
    parseOptionalQuantity(form.expectedQuantity) == null
  ) {
    return "Enter the correct quantity.";
  }

  return null;
}

export function ReportMatchErrorDialog({
  open,
  onClose,
  projectId = "",
  project = { title: "", makerworld_url: "", description: "", parts: [] },
  parts = [],
  initialPartIndex = null,
}: ReportMatchErrorDialogProps) {
  const location = useLocation();
  const initialPart =
    initialPartIndex != null ? String(initialPartIndex) : "";

  const buildForm = useCallback(
    (side: ReportSide, partIndexValue: string) => {
      const index =
        partIndexValue !== "" && !Number.isNaN(Number(partIndexValue))
          ? Number(partIndexValue)
          : null;
      const part = index != null ? parts[index] : undefined;
      if (part) {
        return reportFormFromPart(
          part,
          partIndexValue,
          side,
          project.makerworld_url,
        );
      }
      return emptyReportForm(partIndexValue, side);
    },
    [parts, project.makerworld_url],
  );

  const [reportSide, setReportSide] = useState<ReportSide>("mcmaster");
  const [form, setForm] = useState<ReportFormState>(() =>
    buildForm("mcmaster", initialPart),
  );
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const pageUrl = `${window.location.origin}${location.pathname}${location.search}${location.hash}`;

  const resetForm = useCallback(
    (side: ReportSide, partIndexValue = initialPart) => {
      setForm(buildForm(side, partIndexValue));
      setError(null);
      setSuccess(false);
    },
    [buildForm, initialPart],
  );

  useEffect(() => {
    if (!open) return;
    setReportSide("mcmaster");
    resetForm("mcmaster", initialPart);
  }, [open, initialPart, resetForm]);

  useEffect(() => {
    if (!open) return;

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !submitting) {
        onClose();
      }
    };

    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open, onClose, submitting]);

  const selectedPart =
    form.partIndex !== "" && !Number.isNaN(Number(form.partIndex))
      ? parts[Number(form.partIndex)]
      : undefined;

  function handleSideChange(side: ReportSide) {
    setReportSide(side);
    resetForm(side, form.partIndex);
  }

  function patchForm(patch: Partial<ReportFormState>) {
    setForm((prev) => ({ ...prev, ...patch }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();

    const validationError = validateForm(reportSide, form);
    if (validationError) {
      setError(validationError);
      return;
    }

    setSubmitting(true);
    setError(null);

    const makerworldUrl =
      form.makerworldUrl.trim() || project.makerworld_url.trim();

    try {
      await submitMatchErrorReport({
        project_id: projectId,
        project_title: project.title,
        makerworld_url: makerworldUrl,
        report_side: reportSide,
        part_index: form.partIndex !== "" ? Number(form.partIndex) : null,
        part: selectedPart ?? null,
        issue_type: form.issueType,
        message: form.message.trim(),
        expected_part_number: form.expectedPartNumber.trim(),
        expected_url: form.expectedUrl.trim(),
        expected_finish: form.expectedFinish.trim(),
        makerworld_line_text: form.makerworldLineText.trim(),
        expected_line_text: form.expectedLineText.trim(),
        expected_quantity: parseOptionalQuantity(form.expectedQuantity),
        parse_context: form.parseContext.trim(),
        page_url: pageUrl,
      });
      setSuccess(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not submit report");
    } finally {
      setSubmitting(false);
    }
  }

  if (!open) return null;

  return createPortal(
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      role="presentation"
    >
      <div
        className="absolute inset-0 bg-black/50"
        aria-hidden
        onMouseDown={(e) => e.preventDefault()}
      />

      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="report-error-title"
        className="relative z-10 flex max-h-[min(90vh,720px)] w-full max-w-lg flex-col overflow-hidden rounded-[var(--radius-md)] border border-border bg-card text-foreground shadow-xl"
      >
        <form onSubmit={handleSubmit} className="flex min-h-0 flex-1 flex-col">
          <input type="hidden" name="page_url" value={pageUrl} readOnly />

          <div className="flex items-start justify-between gap-3 border-b border-border px-6 py-4">
            <div>
              <h2 id="report-error-title" className="text-lg font-semibold">
                Report an error
              </h2>
              <p className="mt-1 text-sm text-muted-foreground">
                Tell us what went wrong — McMaster matching or the MakerWorld BOM.
              </p>
            </div>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="shrink-0"
              onClick={onClose}
              disabled={submitting}
              aria-label="Close"
            >
              <X className="h-4 w-4" />
            </Button>
          </div>

          <div className="min-h-0 flex-1 overflow-y-auto px-6 py-4">
            {success ? (
              <div className="space-y-4">
                <p className="rounded-lg border border-success/30 bg-success/10 px-4 py-3 text-sm text-success">
                  Thank you — your report was saved and will help improve imports
                  and matching.
                </p>
                <Button type="button" onClick={onClose}>
                  Close
                </Button>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="flex gap-1 rounded-lg border border-border bg-muted/40 p-1">
                  {REPORT_SIDES.map(({ value, label }) => (
                    <button
                      key={value}
                      type="button"
                      className={cn(
                        "flex-1 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                        reportSide === value
                          ? "bg-card text-foreground shadow-sm"
                          : "text-muted-foreground hover:text-foreground",
                      )}
                      onClick={() => handleSideChange(value)}
                      disabled={submitting}
                    >
                      {label}
                    </button>
                  ))}
                </div>

                <ReportErrorFormFields
                  reportSide={reportSide}
                  parts={parts}
                  projectMakerworldUrl={project.makerworld_url}
                  form={form}
                  submitting={submitting}
                  onChange={patchForm}
                />

                {error && (
                  <p className="text-sm text-destructive" role="alert">
                    {error}
                  </p>
                )}
              </div>
            )}
          </div>

          {!success && (
            <div className="flex flex-wrap justify-end gap-2 border-t border-border px-6 py-4">
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
          )}
        </form>
      </div>
    </div>,
    document.body,
  );
}
