import type {
  HardwareMatchStatus,
  MatchAlternative,
  MatchTier,
  McMasterStatus,
  Part,
} from "@/lib/api";

const STATUS_LABELS: Record<McMasterStatus, string> = {
  likely: "Likely",
  possible: "Verify",
  unlikely: "Unlikely",
  not_applicable: "N/A",
};

const STATUS_STYLES: Record<McMasterStatus, string> = {
  likely: "bg-success-muted text-success",
  possible: "bg-muted text-warning",
  unlikely: "bg-muted text-warning",
  not_applicable: "bg-muted text-muted-foreground",
};

const MATCH_TIER_LABELS: Record<string, string> = {
  catalog: "Catalog SKU",
  rule: "Length rule",
  part_number: "BOM part #",
  filtered_browse: "Filtered browse",
  category_search: "Category search",
  site_search: "Site search",
  api_verified: "API verified",
};

const HARDWARE_MATCH_LABELS: Record<HardwareMatchStatus, string> = {
  verified: "Size/length OK",
  corrected: "Catalog corrected",
  size_mismatch: "Size mismatch",
  length_mismatch: "Length mismatch",
  spec_conflict: "Spec conflict",
  length_unknown: "Length unknown",
  unchecked: "",
  not_applicable: "",
};

const HARDWARE_MATCH_STYLES: Record<string, string> = {
  verified: "text-success",
  corrected: "text-success",
  size_mismatch: "text-danger",
  length_mismatch: "text-danger",
  spec_conflict: "text-danger",
  length_unknown: "text-warning",
};

export function mcmasterStatusLabel(status: McMasterStatus): string {
  return STATUS_LABELS[status] ?? status;
}

export function mcmasterStatusClass(status: McMasterStatus): string {
  return STATUS_STYLES[status] ?? STATUS_STYLES.possible;
}

export function matchTierLabel(tier: MatchTier | undefined): string {
  if (!tier) return "";
  return MATCH_TIER_LABELS[tier] ?? tier.replaceAll("_", " ");
}

export function hardwareMatchLabel(status: HardwareMatchStatus | undefined): string {
  if (!status || status === "unchecked" || status === "not_applicable") return "";
  return HARDWARE_MATCH_LABELS[status] ?? status;
}

export function hardwareMatchClass(status: HardwareMatchStatus | undefined): string {
  if (!status) return "";
  return HARDWARE_MATCH_STYLES[status] ?? "text-muted-foreground";
}

export function needsMcMasterVerification(part: Pick<Part, "mcmaster_status" | "confidence">): boolean {
  if (part.mcmaster_status === "not_applicable") return false;
  if (part.mcmaster_status === "unlikely") return true;
  if (part.mcmaster_status === "possible") return true;
  return part.confidence > 0 && part.confidence < 0.7;
}

export function summarizeMcMasterParts(
  parts: { mcmaster_status?: McMasterStatus }[],
) {
  return parts.reduce(
    (acc, part) => {
      const status = part.mcmaster_status ?? "possible";
      acc[status] = (acc[status] ?? 0) + 1;
      return acc;
    },
    {} as Record<McMasterStatus, number>,
  );
}

export function countNeedsVerification(parts: Part[]): number {
  return parts.filter((part) => needsMcMasterVerification(part)).length;
}

export function guessScopeLabel(scope: MatchAlternative["guess_scope"]): string {
  if (scope === "same_size") return "Same size";
  if (scope === "wider_scope") return "Wider search";
  return "Other";
}

export function alternativeOptionLabel(alt: MatchAlternative): string {
  const scope = guessScopeLabel(alt.guess_scope);
  const detail =
    alt.guess_label?.trim() ||
    (alt.mcmaster_part_number ? alt.mcmaster_part_number : matchTierLabel(alt.match_tier));
  return `${scope} · ${detail}`;
}

export function formatConfidence(
  part: Pick<Part, "confidence" | "confidence_low" | "confidence_high">,
): string {
  if (part.confidence <= 0) return "—";
  const low = part.confidence_low;
  const high = part.confidence_high;
  if (
    low != null &&
    high != null &&
    Math.abs(low - high) > 0.02 &&
    Math.abs(part.confidence - low) > 0.02
  ) {
    return `${Math.round(low * 100)}–${Math.round(high * 100)}%`;
  }
  return `${Math.round(part.confidence * 100)}%`;
}
