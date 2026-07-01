import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Clock, Loader2 } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { ProjectThumbnail } from "@/components/ProjectThumbnail";
import { fetchBomHistory, type ProjectHistoryItem } from "@/lib/api";

function formatWhen(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function bomStatusLabel(status: ProjectHistoryItem["bom_status"]): string {
  switch (status) {
    case "embedded":
      return "Embedded BOM";
    case "description":
      return "Description BOM";
    case "file":
      return "File BOM";
    case "upload":
      return "Uploaded";
    default:
      return "BOM";
  }
}

type BomHistoryProps = {
  refreshKey?: number;
};

export function BomHistory({ refreshKey = 0 }: BomHistoryProps) {
  const [items, setItems] = useState<ProjectHistoryItem[]>([]);
  const [limit, setLimit] = useState(5);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetchBomHistory()
      .then((data) => {
        if (!cancelled) {
          setItems(data.items);
          setLimit(data.limit);
        }
      })
      .catch(() => {
        if (!cancelled) setError("Could not load history");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [refreshKey]);

  return (
    <Card>
      <CardHeader>
        <CardTitle>History</CardTitle>
        <CardDescription>
          Recent BOMs from this session (last {limit}). History clears when the
          API restarts.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {loading && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Loading history…
          </div>
        )}
        {error && (
          <p className="text-sm text-destructive" role="alert">
            {error}
          </p>
        )}
        {!loading && !error && items.length === 0 && (
          <p className="text-sm text-muted-foreground">
            No imports yet. Import a MakerWorld project or upload a BOM file to
            see it here.
          </p>
        )}
        {!loading && items.length > 0 && (
          <ul className="divide-y divide-border rounded-lg border border-border">
            {items.map((item) => (
              <li key={item.project_id}>
                <Link
                  to={`/bom/${item.project_id}`}
                  className="flex items-center gap-3 px-3 py-3 transition-colors hover:bg-muted/50"
                >
                  <ProjectThumbnail
                    url={item.thumbnail_url}
                    title={item.title}
                    size="sm"
                  />
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-medium">{item.title}</p>
                    <p className="text-xs text-muted-foreground">
                      {item.parts_count} part{item.parts_count === 1 ? "" : "s"}
                      {" · "}
                      {bomStatusLabel(item.bom_status)}
                    </p>
                  </div>
                  <div className="hidden shrink-0 items-center gap-1 text-xs text-muted-foreground sm:flex">
                    <Clock className="h-3.5 w-3.5" />
                    {formatWhen(item.updated_at)}
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
