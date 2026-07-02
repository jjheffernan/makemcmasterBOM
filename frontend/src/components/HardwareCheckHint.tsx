import { CircleHelp } from "lucide-react";
import type { Part } from "@/lib/api";
import {
  hardwareCheckShortLabel,
  hardwareCheckTooltip,
  inferHardwareCategory,
} from "@/lib/hardwareCheckTips";
import { cn } from "@/lib/utils";

type HardwareCheckHintProps = {
  part: Part;
  className?: string;
  /** compact = icon only; inline = icon + short category label */
  variant?: "compact" | "inline";
};

export function HardwareCheckHint({
  part,
  className,
  variant = "compact",
}: HardwareCheckHintProps) {
  const category = inferHardwareCategory(part);
  if (category === "unknown" && part.mcmaster_status === "not_applicable") {
    return null;
  }

  const tooltip = hardwareCheckTooltip(part);
  const shortLabel = hardwareCheckShortLabel(part);

  return (
    <button
      type="button"
      className={cn(
        "inline-flex shrink-0 items-center gap-0.5 rounded-sm text-muted-foreground",
        "hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50",
        className,
      )}
      title={tooltip}
      aria-label={shortLabel}
    >
      <CircleHelp className="h-3.5 w-3.5" aria-hidden />
      {variant === "inline" && (
        <span className="max-w-[5.5rem] truncate text-[10px] leading-none">
          {shortLabel}
        </span>
      )}
    </button>
  );
}
