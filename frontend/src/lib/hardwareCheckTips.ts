import type { Part } from "@/lib/api";

/** BOM / McMaster hardware family used for ordering checklists. */
export type HardwareCategory =
  | "socket_screw"
  | "flat_screw"
  | "bolt"
  | "hex_nut"
  | "lock_nut"
  | "flange_nut"
  | "jam_nut"
  | "coupling_nut"
  | "flat_washer"
  | "lock_washer"
  | "fender_washer"
  | "bearing"
  | "insert"
  | "standoff"
  | "tubing"
  | "magnet"
  | "spring"
  | "oring"
  | "pin"
  | "rivet"
  | "generic_fastener"
  | "unknown";

type CategoryGuide = {
  label: string;
  checks: readonly string[];
};

const MCMASTER_CATEGORY_MAP: Record<string, HardwareCategory> = {
  socket_head_screw: "socket_screw",
  flat_head_screw: "flat_screw",
  screw: "socket_screw",
  hex_nut: "hex_nut",
  lock_nut: "lock_nut",
  flange_nut: "flange_nut",
  jam_nut: "jam_nut",
  coupling_nut: "coupling_nut",
  nut: "hex_nut",
  flat_washer: "flat_washer",
  lock_washer: "lock_washer",
  fender_washer: "fender_washer",
  washer: "flat_washer",
  bearing: "bearing",
  insert: "insert",
  standoff: "standoff",
  tubing: "tubing",
  magnet: "magnet",
  spring: "spring",
  oring: "oring",
  pin: "pin",
  rivet: "rivet",
};

const CATEGORY_GUIDES: Record<HardwareCategory, CategoryGuide> = {
  socket_screw: {
    label: "Socket head cap screw",
    checks: [
      "Thread size matches the tapped hole or nut",
      "Overall length fits the stack-up (not too long for blind holes)",
      "Head style is socket/cap (not button, flat, or set screw)",
      "Material/finish matches the assembly (e.g. stainless vs black oxide)",
      "Fully threaded vs partial thread if length is critical",
    ],
  },
  flat_screw: {
    label: "Flat / countersunk screw",
    checks: [
      "Thread size and length match the design",
      "Countersink angle and head diameter fit the pocket",
      "Socket flat head vs slotted/phillips if specified on the drawing",
      "Material/finish matches mating parts",
    ],
  },
  bolt: {
    label: "Hex bolt / machine bolt",
    checks: [
      "Thread size and length match the grip length needed",
      "Hex head (not socket or carriage) if the BOM says bolt",
      "Grade/strength and finish match the application",
      "Fully threaded vs shank section if a precise grip is required",
    ],
  },
  hex_nut: {
    label: "Hex nut",
    checks: [
      "Thread matches the bolt/screw (same pitch and diameter)",
      "Standard hex nut — not nyloc, flange, or jam unless specified",
      "Material matches bolt (stainless with stainless, etc.)",
      "Height/class if a thin or thick nut matters for clearance",
    ],
  },
  lock_nut: {
    label: "Lock / nyloc nut",
    checks: [
      "Thread matches the mating fastener",
      "Nylon-insert or prevailing-torque type matches the BOM",
      "Not a plain hex nut if locking was required",
      "Temperature limits for nylon insert if used near heat",
    ],
  },
  flange_nut: {
    label: "Flange nut",
    checks: [
      "Thread matches the mating fastener",
      "Integrated washer/flange — skip separate washer unless drawing shows one",
      "Serrated vs smooth flange if vibration resistance matters",
    ],
  },
  jam_nut: {
    label: "Jam nut",
    checks: [
      "Thread matches the stud or screw being locked",
      "Thin height — used as a lock against a full nut, not as primary nut",
      "Pair with a standard nut on the same thread if that is the design",
    ],
  },
  coupling_nut: {
    label: "Coupling nut",
    checks: [
      "Thread matches both rods/studs being joined",
      "Length spans the needed engagement on each side",
      "Not a standard hex nut if you need to join two threaded ends",
    ],
  },
  flat_washer: {
    label: "Flat washer",
    checks: [
      "Inner diameter matches screw/bolt size (for screw size)",
      "OD and thickness suit the bearing surface",
      "Not a lock or fender washer if a plain washer was intended",
      "Material/finish matches the fastener",
    ],
  },
  lock_washer: {
    label: "Lock washer",
    checks: [
      "For screw size matches the fastener thread",
      "Split lock vs toothed/star type matches the BOM",
      "Not a flat washer if vibration resistance was required",
      "Correct orientation (belleville/conical if applicable)",
    ],
  },
  fender_washer: {
    label: "Fender washer",
    checks: [
      "Large OD for oversized holes or soft materials",
      "Inner diameter matches screw size",
      "Not a standard flat washer if a wide bearing surface was needed",
    ],
  },
  bearing: {
    label: "Bearing",
    checks: [
      "Bore × OD × width match the shaft and housing",
      "Shielding/seal code (ZZ, 2RS, open) matches speed and environment",
      "Load rating and speed suitable for the application",
    ],
  },
  insert: {
    label: "Threaded insert",
    checks: [
      "Thread size matches the screw used after install",
      "Outer diameter/length suits the plastic or metal boss",
      "Install method (heat-set, press, ultrasonic) matches material",
    ],
  },
  standoff: {
    label: "Standoff / spacer",
    checks: [
      "Thread size and length match board stack height",
      "Hex vs round vs swage style matches assembly access",
      "Male/female ends match how boards are stacked",
    ],
  },
  tubing: {
    label: "Tubing / hose",
    checks: [
      "Inner/outer diameter and wall match fittings",
      "Material (PTFE, polyurethane, etc.) matches fluid/temperature",
      "Length per BOM or cut tolerance",
    ],
  },
  magnet: {
    label: "Magnet",
    checks: [
      "Size and grade (e.g. N52) match holding force needed",
      "Coating if used in wet or abrasive environments",
      "Polarity/count if the design uses paired magnets",
    ],
  },
  spring: {
    label: "Spring",
    checks: [
      "Wire diameter, OD, and free length match the design",
      "Compression vs extension vs torsion type",
      "Material and load rate if deflection is critical",
    ],
  },
  oring: {
    label: "O-ring",
    checks: [
      "Inner diameter and cross-section fit the groove",
      "Material (Buna, Viton, etc.) matches fluid and temperature",
      "Dash size or metric ID × CS if specified on drawing",
    ],
  },
  pin: {
    label: "Pin",
    checks: [
      "Diameter and length match reamed holes or slots",
      "Dowel vs roll pin vs clevis — type matches function",
      "Material/hardening if shear load is significant",
    ],
  },
  rivet: {
    label: "Rivet",
    checks: [
      "Diameter and grip range match material stack thickness",
      "Head style (button, countersunk) matches surface finish",
      "Material compatible with joined sheets",
    ],
  },
  generic_fastener: {
    label: "Fastener",
    checks: [
      "Thread/screw size matches mating parts",
      "Length suits the stack-up",
      "Head style and drive match the design intent",
      "Material/finish appropriate for the environment",
    ],
  },
  unknown: {
    label: "Part",
    checks: [
      "Description and quantity match the MakerWorld BOM",
      "McMaster listing matches size, material, and function",
      "Open the link and confirm the photo/spec table before ordering",
    ],
  },
};

const TEXT_PATTERNS: ReadonlyArray<{ pattern: RegExp; category: HardwareCategory }> = [
  { pattern: /\b(socket\s+head|shcs|din\s*912)\b/i, category: "socket_screw" },
  { pattern: /\b(flat\s+head|fhcs|countersunk?)\b/i, category: "flat_screw" },
  { pattern: /\b(button\s+head|bhcs)\b/i, category: "socket_screw" },
  { pattern: /\b(hex\s+)?bolt\b/i, category: "bolt" },
  { pattern: /\b(nyloc|nylock|lock\s*nut)\b/i, category: "lock_nut" },
  { pattern: /\bflange\s+nut\b/i, category: "flange_nut" },
  { pattern: /\bjam\s+nut\b/i, category: "jam_nut" },
  { pattern: /\bcoupling\s+nut\b/i, category: "coupling_nut" },
  { pattern: /\b(hex\s+)?nut\b/i, category: "hex_nut" },
  { pattern: /\bfender\s+washer\b/i, category: "fender_washer" },
  { pattern: /\b(lock|spring|split)\s+washer\b/i, category: "lock_washer" },
  { pattern: /\bwasher\b/i, category: "flat_washer" },
  { pattern: /\b(bearing|608|693|625)\b/i, category: "bearing" },
  { pattern: /\b(insert|heat[\s-]?set)\b/i, category: "insert" },
  { pattern: /\bstandoff\b/i, category: "standoff" },
  { pattern: /\b(tubing|tube|ptfe|hose)\b/i, category: "tubing" },
  { pattern: /\bmagnet\b/i, category: "magnet" },
  { pattern: /\bspring\b/i, category: "spring" },
  { pattern: /\bo[\s-]?ring\b/i, category: "oring" },
  { pattern: /\b(dowel|roll)\s+pin\b/i, category: "pin" },
  { pattern: /\brivet\b/i, category: "rivet" },
  { pattern: /\b(screw|stud)\b/i, category: "socket_screw" },
];

function combinedPartText(part: Pick<Part, "original_name" | "specification" | "normalized_name">): string {
  return `${part.original_name} ${part.specification} ${part.normalized_name}`.trim();
}

export function inferHardwareCategory(
  part: Pick<Part, "original_name" | "specification" | "normalized_name" | "mcmaster_category">,
): HardwareCategory {
  const fromMcMaster = part.mcmaster_category?.trim();
  if (fromMcMaster) {
    const mapped = MCMASTER_CATEGORY_MAP[fromMcMaster];
    if (mapped) return mapped;
  }

  const text = combinedPartText(part);
  for (const { pattern, category } of TEXT_PATTERNS) {
    if (pattern.test(text)) return category;
  }

  if (/\b(fastener|hardware)\b/i.test(text)) return "generic_fastener";
  return "unknown";
}

export function hardwareCategoryLabel(category: HardwareCategory): string {
  return CATEGORY_GUIDES[category].label;
}

function formatMatchedSize(
  part: Pick<Part, "hardware_diameter_mm" | "hardware_length_mm">,
): string {
  const d = part.hardware_diameter_mm;
  const l = part.hardware_length_mm;
  if (d != null && l != null) {
    return `Matched M${trimMetric(d)}×${trimMetric(l)} mm. `;
  }
  if (d != null) {
    return `Matched M${trimMetric(d)} thread/screw size. `;
  }
  return "";
}

function trimMetric(value: number): string {
  return Number.isInteger(value) ? String(value) : String(value);
}

/** Full checklist for native tooltip / aria description. */
export function hardwareCheckTooltip(
  part: Pick<
    Part,
    | "original_name"
    | "specification"
    | "normalized_name"
    | "mcmaster_category"
    | "hardware_diameter_mm"
    | "hardware_length_mm"
    | "mcmaster_metacategory_label"
    | "mcmaster_status"
    | "mcmaster_part_number"
  >,
): string {
  const category = inferHardwareCategory(part);
  const guide = CATEGORY_GUIDES[category];
  const size = formatMatchedSize(part);
  const sku =
    part.mcmaster_part_number?.trim() ?
      `SKU ${part.mcmaster_part_number}. `
    : "";

  const lines = [
    `${guide.label} — confirm before ordering:`,
    size + sku,
    ...guide.checks.map((check, index) => `${index + 1}. ${check}`),
  ].filter(Boolean);

  if (part.mcmaster_metacategory_label?.trim()) {
    lines.splice(
      1,
      0,
      `McMaster department: ${part.mcmaster_metacategory_label.trim()}`,
    );
  }

  if (part.mcmaster_status === "not_applicable") {
    lines.push("No McMaster link — verify this line is not orderable catalog hardware.");
  }

  return lines.join("\n");
}

/** Short label shown beside the part name. */
export function hardwareCheckShortLabel(
  part: Pick<Part, "original_name" | "specification" | "normalized_name" | "mcmaster_category">,
): string {
  return `Check ${hardwareCategoryLabel(inferHardwareCategory(part)).toLowerCase()}`;
}
