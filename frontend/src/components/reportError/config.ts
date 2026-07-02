import type { MakerWorldIssueType, MatchIssueType, ReportSide } from "@/lib/api";

export interface IssueOption<T extends string = string> {
  value: T;
  label: string;
  description: string;
}

export const REPORT_SIDES: { value: ReportSide; label: string }[] = [
  { value: "mcmaster", label: "McMaster matching" },
  { value: "makerworld", label: "MakerWorld BOM" },
];

export const MCMASTER_ISSUE_OPTIONS: IssueOption<MatchIssueType>[] = [
  {
    value: "wrong_part_number",
    label: "Wrong part number / SKU",
    description: "We matched a McMaster SKU, but it is the wrong product.",
  },
  {
    value: "wrong_category_or_search",
    label: "Wrong category or search link",
    description: "The link goes to the wrong product family or a generic search.",
  },
  {
    value: "missed_hardware",
    label: "Missed hardware",
    description: "Hardware should match McMaster but we left it blank or N/A.",
  },
  {
    value: "wrong_finish_or_material",
    label: "Wrong finish or material",
    description: "Correct family, wrong finish (e.g. stainless vs black oxide).",
  },
  {
    value: "should_be_not_applicable",
    label: "Should not match McMaster",
    description: "3D-printed parts, electronics, filament, etc.",
  },
  {
    value: "other",
    label: "Other matching problem",
    description: "Something else about McMaster matching.",
  },
];

export const MAKERWORLD_ISSUE_OPTIONS: IssueOption<MakerWorldIssueType>[] = [
  {
    value: "makerworld_wrong_line",
    label: "Wrong BOM line",
    description: "Name, spec, or description on MakerWorld does not match the part.",
  },
  {
    value: "makerworld_missing_hardware",
    label: "Missing from MakerWorld BOM",
    description: "Hardware is in the design but absent from the MakerWorld list.",
  },
  {
    value: "makerworld_wrong_quantity",
    label: "Wrong quantity on MakerWorld",
    description: "The listed quantity on MakerWorld is incorrect.",
  },
  {
    value: "makerworld_parse_error",
    label: "Import / parse problem",
    description: "Scrape, CSV download, or description parsing failed or mangled data.",
  },
  {
    value: "makerworld_other",
    label: "Other MakerWorld issue",
    description: "Something else about the MakerWorld side.",
  },
];

export function defaultIssueForSide(side: ReportSide): MatchIssueType | MakerWorldIssueType {
  return side === "mcmaster" ? "wrong_part_number" : "makerworld_wrong_line";
}
