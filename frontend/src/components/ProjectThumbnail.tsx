import { ImageOff } from "lucide-react";
import { cn } from "@/lib/utils";

interface ProjectThumbnailProps {
  url?: string;
  title?: string;
  size?: "sm" | "md" | "lg";
  className?: string;
}

const SIZES = {
  sm: "h-12 w-12",
  md: "h-20 w-20",
  lg: "h-28 w-28",
};

export function ProjectThumbnail({
  url,
  title = "Project",
  size = "md",
  className,
}: ProjectThumbnailProps) {
  if (!url) {
    return (
      <div
        className={cn(
          "flex shrink-0 items-center justify-center rounded-[var(--radius-md)] border border-border bg-muted text-muted-foreground",
          SIZES[size],
          className,
        )}
        aria-hidden
      >
        <ImageOff className="h-5 w-5" />
      </div>
    );
  }

  return (
    <img
      src={url}
      alt={`${title} thumbnail`}
      className={cn(
        "shrink-0 rounded-[var(--radius-md)] border border-border bg-card object-cover shadow-sm",
        SIZES[size],
        className,
      )}
      loading="lazy"
      referrerPolicy="no-referrer"
    />
  );
}
