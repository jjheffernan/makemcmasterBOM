import { GripVertical } from "lucide-react";
import { cn } from "@/lib/utils";

const DRAG_MIME = "application/x-makemcmaster-bom-part-index";

export function setBomPartDragData(dataTransfer: DataTransfer, partIndex: number) {
  dataTransfer.setData(DRAG_MIME, String(partIndex));
  dataTransfer.effectAllowed = "move";
}

export function readBomPartDragIndex(dataTransfer: DataTransfer): number | null {
  const raw = dataTransfer.getData(DRAG_MIME);
  if (!raw) return null;
  const index = Number(raw);
  return Number.isInteger(index) && index >= 0 ? index : null;
}

interface BomDragHandleProps {
  partIndex: number;
  label: string;
  disabled?: boolean;
  onDragStart?: (partIndex: number) => void;
  onDragEnd?: () => void;
  className?: string;
}

export function BomDragHandle({
  partIndex,
  label,
  disabled = false,
  onDragStart,
  onDragEnd,
  className,
}: BomDragHandleProps) {
  return (
    <button
      type="button"
      draggable={!disabled}
      disabled={disabled}
      aria-label={label}
      title="Drag to reorder"
      className={cn(
        "inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-md text-muted-foreground",
        disabled
          ? "cursor-not-allowed opacity-40"
          : "cursor-grab active:cursor-grabbing hover:bg-muted/80 hover:text-foreground",
        className,
      )}
      onDragStart={(event) => {
        if (disabled) {
          event.preventDefault();
          return;
        }
        setBomPartDragData(event.dataTransfer, partIndex);
        onDragStart?.(partIndex);
      }}
      onDragEnd={() => onDragEnd?.()}
    >
      <GripVertical className="h-4 w-4" />
    </button>
  );
}
