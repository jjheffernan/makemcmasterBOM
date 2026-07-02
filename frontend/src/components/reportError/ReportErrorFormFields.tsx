import { Input } from "@/components/ui/input";
import { Label, Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import type {
  MakerWorldIssueType,
  MatchIssueType,
  Part,
  ReportSide,
} from "@/lib/api";
import { formatConfidence, matchTierLabel } from "@/lib/mcmaster";
import { needsMcMasterVerification } from "@/lib/mcmaster";
import {
  defaultIssueForSide,
  MAKERWORLD_ISSUE_OPTIONS,
  MCMASTER_ISSUE_OPTIONS,
  type IssueOption,
} from "./config";

export interface ReportFormState {
  partIndex: string;
  issueType: MatchIssueType | MakerWorldIssueType;
  message: string;
  expectedPartNumber: string;
  expectedUrl: string;
  expectedFinish: string;
  makerworldLineText: string;
  expectedLineText: string;
  expectedQuantity: string;
  makerworldUrl: string;
  parseContext: string;
}

interface ReportErrorFormFieldsProps {
  reportSide: ReportSide;
  parts: Part[];
  projectMakerworldUrl: string;
  form: ReportFormState;
  submitting: boolean;
  onChange: (patch: Partial<ReportFormState>) => void;
}

export function partLineSummary(part: Part): string {
  const bits = [part.original_name];
  if (part.specification) bits.push(part.specification);
  return bits.join(" · ");
}

function partSummary(part: Part): string {
  return partLineSummary(part);
}

function matchSummary(part: Part): string {
  const tier = part.match_tier ? matchTierLabel(part.match_tier) : "—";
  const sku = part.mcmaster_part_number || "no SKU";
  return `${tier} · ${sku} · ${formatConfidence(part)}`;
}

function IssueSelect<T extends string>({
  id,
  label,
  value,
  options,
  submitting,
  onChange,
}: {
  id: string;
  label: string;
  value: T;
  options: IssueOption<T>[];
  submitting: boolean;
  onChange: (value: T) => void;
}) {
  const selected = options.find((option) => option.value === value);
  return (
    <div className="space-y-2">
      <Label htmlFor={id}>{label}</Label>
      <Select
        id={id}
        value={value}
        onChange={(e) => onChange(e.target.value as T)}
        disabled={submitting}
        required
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </Select>
      {selected?.description && (
        <p className="text-xs text-muted-foreground">{selected.description}</p>
      )}
    </div>
  );
}

function PartPicker({
  parts,
  partIndex,
  submitting,
  onChange,
  optional = true,
}: {
  parts: Part[];
  partIndex: string;
  submitting: boolean;
  onChange: (value: string) => void;
  optional?: boolean;
}) {
  if (parts.length === 0) return null;
  return (
    <div className="space-y-2">
      <Label htmlFor="report-part">
        BOM line{optional ? " (optional)" : ""}
      </Label>
      <Select
        id="report-part"
        value={partIndex}
        onChange={(e) => onChange(e.target.value)}
        disabled={submitting}
        required={!optional}
      >
        {optional && (
          <option value="">General — whole project / multiple lines</option>
        )}
        {!optional && partIndex === "" && (
          <option value="" disabled>
            Select a line…
          </option>
        )}
        {parts.map((part, index) => (
          <option key={index} value={String(index)}>
            {partSummary(part)}
          </option>
        ))}
      </Select>
    </div>
  );
}

function CurrentMatchCard({ part }: { part: Part }) {
  return (
    <div className="rounded-lg border border-border bg-muted/30 px-3 py-2 text-xs text-muted-foreground">
      <p className="font-medium text-foreground">Current match</p>
      <p className="mt-1">{matchSummary(part)}</p>
      {part.mcmaster_url && (
        <p className="mt-1 truncate font-mono">{part.mcmaster_url}</p>
      )}
    </div>
  );
}

function MakerworldUrlField({
  value,
  fallback,
  submitting,
  onChange,
}: {
  value: string;
  fallback: string;
  submitting: boolean;
  onChange: (value: string) => void;
}) {
  return (
    <div className="space-y-2">
      <Label htmlFor="report-makerworld-url">MakerWorld project URL</Label>
      <Input
        id="report-makerworld-url"
        type="url"
        placeholder="https://makerworld.com/en/models/…"
        value={value || fallback}
        onChange={(e) => onChange(e.target.value)}
        disabled={submitting}
        className="font-mono text-xs"
      />
    </div>
  );
}

function DetailsField({
  id,
  label,
  placeholder,
  value,
  submitting,
  onChange,
  rows = 4,
}: {
  id: string;
  label: string;
  placeholder: string;
  value: string;
  submitting: boolean;
  onChange: (value: string) => void;
  rows?: number;
}) {
  return (
    <div className="space-y-2">
      <Label htmlFor={id}>{label}</Label>
      <Textarea
        id={id}
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={submitting}
        required
        rows={rows}
      />
    </div>
  );
}

function McMasterFields({
  parts,
  form,
  submitting,
  onChange,
}: Omit<ReportErrorFormFieldsProps, "reportSide" | "projectMakerworldUrl">) {
  const issueType = form.issueType;
  const selectedPart =
    form.partIndex !== "" && !Number.isNaN(Number(form.partIndex))
      ? parts[Number(form.partIndex)]
      : undefined;

  return (
    <>
      <IssueSelect
        id="report-issue"
        label="What went wrong?"
        value={form.issueType as MatchIssueType}
        options={MCMASTER_ISSUE_OPTIONS}
        submitting={submitting}
        onChange={(value) => onChange({ issueType: value })}
      />

      {(issueType === "wrong_part_number" ||
        issueType === "wrong_category_or_search" ||
        issueType === "wrong_finish_or_material" ||
        issueType === "should_be_not_applicable" ||
        issueType === "other") && (
        <PartPicker
          parts={parts}
          partIndex={form.partIndex}
          submitting={submitting}
          onChange={(value) => onChange({ partIndex: value })}
        />
      )}

      {issueType === "missed_hardware" && (
        <PartPicker
          parts={parts}
          partIndex={form.partIndex}
          submitting={submitting}
          onChange={(value) => onChange({ partIndex: value })}
          optional={false}
        />
      )}

      {selectedPart && issueType !== "missed_hardware" && (
        <CurrentMatchCard part={selectedPart} />
      )}

      {issueType === "wrong_part_number" && (
        <div className="grid gap-3 sm:grid-cols-2">
          <div className="space-y-2">
            <Label htmlFor="report-expected-sku">Correct part #</Label>
            <Input
              id="report-expected-sku"
              placeholder="e.g. 91290A120"
              value={form.expectedPartNumber}
              onChange={(e) => onChange({ expectedPartNumber: e.target.value })}
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
              value={form.expectedUrl}
              onChange={(e) => onChange({ expectedUrl: e.target.value })}
              disabled={submitting}
              className="font-mono text-xs"
            />
          </div>
        </div>
      )}

      {issueType === "wrong_category_or_search" && (
        <div className="space-y-3">
          <div className="space-y-2">
            <Label htmlFor="report-expected-url">Correct McMaster URL or search</Label>
            <Input
              id="report-expected-url"
              type="url"
              placeholder="https://www.mcmaster.com/… or search terms"
              value={form.expectedUrl}
              onChange={(e) => onChange({ expectedUrl: e.target.value })}
              disabled={submitting}
              className="font-mono text-xs"
            />
          </div>
        </div>
      )}

      {issueType === "missed_hardware" && (
        <div className="space-y-3">
          {!selectedPart && (
            <div className="space-y-2">
              <Label htmlFor="report-missed-name">Hardware name / spec</Label>
              <Input
                id="report-missed-name"
                placeholder="e.g. M3×8 socket head cap screw, stainless"
                value={form.expectedLineText}
                onChange={(e) => onChange({ expectedLineText: e.target.value })}
                disabled={submitting}
                required
              />
            </div>
          )}
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="report-expected-sku">Expected part # (optional)</Label>
              <Input
                id="report-expected-sku"
                placeholder="e.g. 91290A120"
                value={form.expectedPartNumber}
                onChange={(e) => onChange({ expectedPartNumber: e.target.value })}
                disabled={submitting}
                className="font-mono text-sm"
              />
            </div>
            <div className="space-y-2 sm:col-span-2">
              <Label htmlFor="report-expected-url">Expected McMaster URL (optional)</Label>
              <Input
                id="report-expected-url"
                type="url"
                placeholder="https://www.mcmaster.com/…"
                value={form.expectedUrl}
                onChange={(e) => onChange({ expectedUrl: e.target.value })}
                disabled={submitting}
                className="font-mono text-xs"
              />
            </div>
          </div>
        </div>
      )}

      {issueType === "wrong_finish_or_material" && (
        <div className="space-y-3">
          <div className="space-y-2">
            <Label htmlFor="report-expected-finish">Correct finish / material</Label>
            <Input
              id="report-expected-finish"
              placeholder="e.g. black oxide, 316 stainless"
              value={form.expectedFinish}
              onChange={(e) => onChange({ expectedFinish: e.target.value })}
              disabled={submitting}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="report-expected-sku">Correct part # (optional)</Label>
            <Input
              id="report-expected-sku"
              placeholder="e.g. 91290A120"
              value={form.expectedPartNumber}
              onChange={(e) => onChange({ expectedPartNumber: e.target.value })}
              disabled={submitting}
              className="font-mono text-sm"
            />
          </div>
        </div>
      )}

      {issueType === "should_be_not_applicable" && (
        <div className="space-y-2">
          <Label htmlFor="report-item-type">Item type</Label>
          <Input
            id="report-item-type"
            placeholder="e.g. 3D-printed bracket, stepper motor, PETG filament"
            value={form.expectedLineText}
            onChange={(e) => onChange({ expectedLineText: e.target.value })}
            disabled={submitting}
          />
        </div>
      )}

      <DetailsField
        id="report-message"
        label="Details"
        placeholder={
          issueType === "missed_hardware"
            ? "Where does this hardware appear (MakerWorld description, assembly step, etc.)?"
            : "What should we have picked instead? Any context from the MakerWorld BOM?"
        }
        value={form.message}
        submitting={submitting}
        onChange={(value) => onChange({ message: value })}
      />
    </>
  );
}

function MakerWorldFields({
  parts,
  projectMakerworldUrl,
  form,
  submitting,
  onChange,
}: ReportErrorFormFieldsProps) {
  const issueType = form.issueType;
  const selectedPart =
    form.partIndex !== "" && !Number.isNaN(Number(form.partIndex))
      ? parts[Number(form.partIndex)]
      : undefined;

  return (
    <>
      <MakerworldUrlField
        value={form.makerworldUrl}
        fallback={projectMakerworldUrl}
        submitting={submitting}
        onChange={(value) => onChange({ makerworldUrl: value })}
      />

      <IssueSelect
        id="report-makerworld-issue"
        label="What went wrong on MakerWorld?"
        value={form.issueType as MakerWorldIssueType}
        options={MAKERWORLD_ISSUE_OPTIONS}
        submitting={submitting}
        onChange={(value) => onChange({ issueType: value })}
      />

      {(issueType === "makerworld_wrong_line" ||
        issueType === "makerworld_wrong_quantity") && (
        <PartPicker
          parts={parts}
          partIndex={form.partIndex}
          submitting={submitting}
          onChange={(value) => onChange({ partIndex: value })}
          optional={false}
        />
      )}

      {issueType === "makerworld_wrong_line" && (
        <div className="space-y-3">
          <div className="space-y-2">
            <Label htmlFor="report-mw-line">Text on MakerWorld (if different from BOM line)</Label>
            <Input
              id="report-mw-line"
              placeholder="What MakerWorld shows for this line"
              value={form.makerworldLineText}
              onChange={(e) => onChange({ makerworldLineText: e.target.value })}
              disabled={submitting}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="report-expected-line">What it should say</Label>
            <Input
              id="report-expected-line"
              placeholder="Correct name, spec, or description"
              value={form.expectedLineText}
              onChange={(e) => onChange({ expectedLineText: e.target.value })}
              disabled={submitting}
            />
          </div>
        </div>
      )}

      {issueType === "makerworld_missing_hardware" && (
        <div className="space-y-3">
          <div className="space-y-2">
            <Label htmlFor="report-missing-name">Missing hardware</Label>
            <Input
              id="report-missing-name"
              placeholder="Part name and spec that should be on the BOM"
              value={form.expectedLineText}
              onChange={(e) => onChange({ expectedLineText: e.target.value })}
              disabled={submitting}
              required
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="report-missing-qty">Expected quantity (optional)</Label>
            <Input
              id="report-missing-qty"
              type="number"
              min={0}
              step={1}
              placeholder="e.g. 4"
              value={form.expectedQuantity}
              onChange={(e) => onChange({ expectedQuantity: e.target.value })}
              disabled={submitting}
              className="w-28 font-mono tabular-nums"
            />
          </div>
        </div>
      )}

      {issueType === "makerworld_wrong_quantity" && selectedPart && (
        <div className="rounded-lg border border-border bg-muted/30 px-3 py-2 text-xs text-muted-foreground">
          <p className="font-medium text-foreground">Imported quantity</p>
          <p className="mt-1 tabular-nums">{selectedPart.quantity}</p>
        </div>
      )}

      {issueType === "makerworld_wrong_quantity" && (
        <div className="space-y-2">
          <Label htmlFor="report-expected-qty">Correct quantity</Label>
          <Input
            id="report-expected-qty"
            type="number"
            min={0}
            step={1}
            placeholder="e.g. 8"
            value={form.expectedQuantity}
            onChange={(e) => onChange({ expectedQuantity: e.target.value })}
            disabled={submitting}
            required
            className="w-28 font-mono tabular-nums"
          />
        </div>
      )}

      {issueType === "makerworld_parse_error" && (
        <div className="space-y-2">
          <Label htmlFor="report-parse-context">What failed?</Label>
          <Input
            id="report-parse-context"
            placeholder="e.g. CSV download missing, description BOM garbled"
            value={form.parseContext}
            onChange={(e) => onChange({ parseContext: e.target.value })}
            disabled={submitting}
          />
        </div>
      )}

      <DetailsField
        id="report-message"
        label="Details"
        placeholder="Describe the MakerWorld-side problem and what you expected instead."
        value={form.message}
        submitting={submitting}
        onChange={(value) => onChange({ message: value })}
      />
    </>
  );
}

export function ReportErrorFormFields(props: ReportErrorFormFieldsProps) {
  if (props.reportSide === "makerworld") {
    return <MakerWorldFields {...props} />;
  }
  return <McMasterFields {...props} />;
}

function defaultIssueTypeForPart(
  part: Part,
  reportSide: ReportSide,
): MatchIssueType | MakerWorldIssueType {
  if (reportSide === "makerworld") {
    return "makerworld_wrong_line";
  }

  if (part.mcmaster_status === "not_applicable") {
    return "should_be_not_applicable";
  }
  if (!part.mcmaster_url.trim()) {
    return "missed_hardware";
  }
  if (
    (part.browse_finish_options?.length ?? 0) > 1 &&
    (part.hardware_match_status === "spec_conflict" ||
      Boolean(part.selected_finish_id))
  ) {
    return "wrong_finish_or_material";
  }
  const tier = part.match_tier;
  if (
    tier === "category_search" ||
    tier === "site_search" ||
    (tier === "filtered_browse" && needsMcMasterVerification(part))
  ) {
    return "wrong_category_or_search";
  }
  if (needsMcMasterVerification(part)) {
    return "wrong_category_or_search";
  }
  if (part.mcmaster_part_number) {
    return "wrong_part_number";
  }
  return defaultIssueForSide("mcmaster");
}

function buildLineContextMessage(part: Part): string {
  const lines: string[] = [
    `BOM line: ${partLineSummary(part)} (qty ${part.quantity})`,
  ];

  if (part.mcmaster_status === "not_applicable") {
    lines.push(
      `Marked not applicable${part.mcmaster_reason ? `: ${part.mcmaster_reason}` : ""}`,
    );
  } else {
    lines.push(`Imported match: ${matchSummary(part)}`);
    if (part.mcmaster_url.trim()) {
      lines.push(`McMaster link: ${part.mcmaster_url.trim()}`);
    }
    if (part.mcmaster_reason.trim()) {
      lines.push(`Match note: ${part.mcmaster_reason.trim()}`);
    }
  }

  if (part.notes.trim()) {
    lines.push(`Editor notes: ${part.notes.trim()}`);
  }

  lines.push("", "What went wrong:");
  return lines.join("\n");
}

export function reportFormFromPart(
  part: Part,
  partIndex: string,
  reportSide: ReportSide,
  projectMakerworldUrl = "",
): ReportFormState {
  const issueType = defaultIssueTypeForPart(part, reportSide);
  const form: ReportFormState = {
    ...emptyReportForm(partIndex, reportSide),
    issueType,
    message: buildLineContextMessage(part),
    makerworldLineText: partLineSummary(part),
    makerworldUrl: projectMakerworldUrl.trim(),
  };

  if (issueType === "should_be_not_applicable") {
    form.expectedLineText = partLineSummary(part);
  }

  return form;
}

export function emptyReportForm(
  partIndex: string,
  reportSide: ReportSide,
): ReportFormState {
  return {
    partIndex,
    issueType: defaultIssueForSide(reportSide),
    message: "",
    expectedPartNumber: "",
    expectedUrl: "",
    expectedFinish: "",
    makerworldLineText: "",
    expectedLineText: "",
    expectedQuantity: "",
    makerworldUrl: "",
    parseContext: "",
  };
}
