import { useLayoutEffect, useRef, useState } from "react";
import { cn } from "@/lib/utils";

/** Omit embedded Parts: prose — same rule as backend description_summary. */
export function sanitizeDescriptionText(
  description: string,
  fallback: string,
): string {
  if (!description.trim()) return fallback;
  const beforeParts =
    description.split(/\bParts\s*:/i)[0]?.trim() ?? description;
  return beforeParts || description;
}

type DescriptionPreviewProps = {
  description: string;
  fallback?: string;
  className?: string;
};

export function DescriptionPreview({
  description,
  fallback = "",
  className,
}: DescriptionPreviewProps) {
  const [expanded, setExpanded] = useState(false);
  const [clamped, setClamped] = useState(false);
  const ref = useRef<HTMLParagraphElement>(null);
  const text = sanitizeDescriptionText(description, fallback);

  useLayoutEffect(() => {
    const el = ref.current;
    if (!el || expanded) return;
    setClamped(el.scrollHeight > el.clientHeight + 1);
  }, [text, expanded]);

  const showToggle = clamped || expanded;

  return (
    <div className={className}>
      <p
        ref={ref}
        className={cn("whitespace-pre-wrap", !expanded && "line-clamp-3")}
      >
        {text}
      </p>
      {showToggle && (
        <button
          type="button"
          className="mt-0.5 text-sm font-medium text-link hover:text-[var(--link-hover)]"
          onClick={() => setExpanded((value) => !value)}
        >
          {expanded ? "Read less" : "Read more"}
        </button>
      )}
    </div>
  );
}
