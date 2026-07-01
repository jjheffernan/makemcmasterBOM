import type { Part, SpecificationIssue } from "@/lib/api";

const FASTENER_RE =
  /\b(screw|bolt|nut|washer|stud|standoff|cap screw|machine screw)\b/i;
const BEARING_RE = /\b(bearing|608|693|625)\b/i;
const NUT_RE = /\bnut\b/i;
const WASHER_RE = /\bwasher\b/i;
const MAGNET_RE = /\bmagnet\b/i;
const INSERT_RE = /\binsert\b/i;
const TUBING_RE = /\b(tubing|tube|ptfe|hose)\b/i;

export const SPEC_PLACEHOLDER_DEFAULT =
  "Head style, finish, shielding — metadata not already in the part name";

export function specPlaceholderForPart(part: Pick<Part, "original_name" | "specification">): string {
  const text = `${part.original_name} ${part.specification}`;
  if (BEARING_RE.test(text)) {
    return "Shielding / seal (e.g. double-shielded, 2RS, open)";
  }
  if (FASTENER_RE.test(text)) {
    return "Head style, drive, finish (e.g. socket head, hex, 18-8, fully threaded)";
  }
  if (NUT_RE.test(text)) {
    return "Style or locking (e.g. nyloc, flange, jam)";
  }
  if (WASHER_RE.test(text)) {
    return "Type or finish (e.g. lock washer, stainless)";
  }
  if (MAGNET_RE.test(text)) {
    return "Grade, coating, or pull force if known";
  }
  if (INSERT_RE.test(text)) {
    return "Install method or material (e.g. heat-set, brass)";
  }
  if (TUBING_RE.test(text)) {
    return "ID/OD, wall, material (e.g. PTFE, 4 mm ID)";
  }
  return SPEC_PLACEHOLDER_DEFAULT;
}

export function worstSpecIssue(
  issues: SpecificationIssue[] | undefined,
): SpecificationIssue | undefined {
  if (!issues?.length) return undefined;
  return issues.find((i) => i.severity === "error") ?? issues[0];
}

export function specInputClassName(issue: SpecificationIssue | undefined): string {
  if (!issue) return "";
  if (issue.severity === "error") return "border-danger focus-visible:ring-danger/40";
  return "border-warning focus-visible:ring-warning/40";
}
