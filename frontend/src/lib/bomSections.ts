import type { Part } from "@/lib/api";

export type BomSectionKey = "bom" | "not_applicable";

export const DEFAULT_BOM_HEADINGS: Record<BomSectionKey, string> = {
  bom: "BOM",
  not_applicable: "Not sold on McMaster-Carr",
};

export type BomDisplayRow =
  | { kind: "heading"; id: BomSectionKey; text: string }
  | { kind: "part"; partIndex: number };

export function resolveBomHeadings(
  stored?: Partial<Record<BomSectionKey, string>>,
): Record<BomSectionKey, string> {
  return {
    bom: stored?.bom?.trim() || DEFAULT_BOM_HEADINGS.bom,
    not_applicable:
      stored?.not_applicable?.trim() || DEFAULT_BOM_HEADINGS.not_applicable,
  };
}

export function isMcMasterBomPart(part: Pick<Part, "mcmaster_status">): boolean {
  return part.mcmaster_status !== "not_applicable";
}

export function sectionKeyForPart(
  part: Pick<Part, "mcmaster_status">,
): BomSectionKey {
  return isMcMasterBomPart(part) ? "bom" : "not_applicable";
}

export function splitPartsBySection(parts: Part[]): Record<BomSectionKey, Part[]> {
  const sections: Record<BomSectionKey, Part[]> = {
    bom: [],
    not_applicable: [],
  };
  for (const part of parts) {
    sections[sectionKeyForPart(part)].push(part);
  }
  return sections;
}

export function mergeSectionParts(
  sections: Record<BomSectionKey, Part[]>,
): Part[] {
  return [...sections.bom, ...sections.not_applicable];
}

/** BOM hardware first, then not-applicable — matches the parts table layout. */
export function normalizePartsOrder(parts: Part[]): Part[] {
  return mergeSectionParts(splitPartsBySection(parts));
}

export function sectionPartIndices(
  parts: Part[],
  section: BomSectionKey,
): number[] {
  return parts.flatMap((part, index) =>
    sectionKeyForPart(part) === section ? [index] : [],
  );
}

export function reorderPartWithinSection(
  parts: Part[],
  fromPartIndex: number,
  toPartIndex: number,
): Part[] | null {
  if (fromPartIndex === toPartIndex) return null;

  const fromPart = parts[fromPartIndex];
  const toPart = parts[toPartIndex];
  if (!fromPart || !toPart) return null;
  if (sectionKeyForPart(fromPart) !== sectionKeyForPart(toPart)) return null;

  const section = sectionKeyForPart(fromPart);
  const sectionIndices = sectionPartIndices(parts, section);
  const fromPos = sectionIndices.indexOf(fromPartIndex);
  const toPos = sectionIndices.indexOf(toPartIndex);
  if (fromPos < 0 || toPos < 0) return null;

  const reorderedIndices = [...sectionIndices];
  const [moved] = reorderedIndices.splice(fromPos, 1);
  let insertAt = toPos;
  if (fromPos < toPos) insertAt -= 1;
  reorderedIndices.splice(insertAt, 0, moved);

  const sections = splitPartsBySection(parts);
  sections[section] = reorderedIndices.map((index) => parts[index]);
  return mergeSectionParts(sections);
}

export function buildPartIndexMap(
  oldParts: Part[],
  newParts: Part[],
): Map<number, number> {
  const map = new Map<number, number>();
  for (let newIndex = 0; newIndex < newParts.length; newIndex += 1) {
    const oldIndex = oldParts.indexOf(newParts[newIndex]);
    if (oldIndex >= 0) map.set(oldIndex, newIndex);
  }
  return map;
}

export function remapRowSelection(
  selection: Record<string, boolean>,
  indexMap: Map<number, number>,
): Record<string, boolean> {
  const next: Record<string, boolean> = {};
  for (const [id, selected] of Object.entries(selection)) {
    if (!selected) continue;
    const mapped = indexMap.get(Number(id));
    if (mapped != null) next[String(mapped)] = true;
  }
  return next;
}

export function remapSpecIssuesByIndex<T extends { part_index: number }>(
  issues: Record<number, T[]>,
  indexMap: Map<number, number>,
): Record<number, T[]> {
  const next: Record<number, T[]> = {};
  for (const [oldIdx, list] of Object.entries(issues)) {
    const newIdx = indexMap.get(Number(oldIdx));
    if (newIdx == null) continue;
    next[newIdx] = list.map((issue) => ({ ...issue, part_index: newIdx }));
  }
  return next;
}

export function buildBomDisplayRows(
  parts: Part[],
  headings: Record<BomSectionKey, string>,
): BomDisplayRow[] {
  const bomIndices = sectionPartIndices(parts, "bom");
  const notApplicableIndices = sectionPartIndices(parts, "not_applicable");

  const rows: BomDisplayRow[] = [];

  if (bomIndices.length > 0) {
    rows.push({ kind: "heading", id: "bom", text: headings.bom });
    for (const partIndex of bomIndices) {
      rows.push({ kind: "part", partIndex });
    }
  }

  if (notApplicableIndices.length > 0) {
    rows.push({
      kind: "heading",
      id: "not_applicable",
      text: headings.not_applicable,
    });
    for (const partIndex of notApplicableIndices) {
      rows.push({ kind: "part", partIndex });
    }
  }

  return rows;
}
