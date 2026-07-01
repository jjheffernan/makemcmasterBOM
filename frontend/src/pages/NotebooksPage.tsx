import { useQuery } from "@tanstack/react-query";
import { ExternalLink, Loader2, Notebook } from "lucide-react";
import { buttonVariants } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { listNotebooks } from "@/lib/api";

export function NotebooksPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["notebooks"],
    queryFn: listNotebooks,
  });

  const jupyterBase = data?.jupyter_url ?? "/jupyter/lab/tree/notebooks";

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Pipeline Notebooks</CardTitle>
          <CardDescription>
            Prototype scrape, parse, and matching logic here before promoting
            code into <code className="text-xs">backend/services/</code>.
            JupyterLab opens at{" "}
            <a href={jupyterBase} target="_blank" rel="noreferrer" className="text-link underline hover:text-[var(--link-hover)]">
              {jupyterBase}
            </a>{" "}
            (use the button below — embedded view can be blocked by the browser).
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-3">
          <a
            href={jupyterBase}
            target="_blank"
            rel="noreferrer"
            className={buttonVariants()}
          >
            <Notebook className="h-4 w-4" />
            Open JupyterLab
          </a>
        </CardContent>
      </Card>

      {isLoading && (
        <div className="flex items-center gap-2 text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading notebooks…
        </div>
      )}

      {error && (
        <p className="text-sm text-destructive">
          Could not load notebook list. Is the API running?
        </p>
      )}

      <div className="grid gap-4 md:grid-cols-2">
        {data?.notebooks.map((nb) => (
          <Card key={nb.filename}>
            <CardHeader>
              <CardTitle className="text-base">{nb.title}</CardTitle>
              <CardDescription>{nb.description}</CardDescription>
            </CardHeader>
            <CardContent className="flex items-center justify-between">
              <span className="rounded-full bg-muted px-2 py-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                {nb.stage}
              </span>
              <a
                href={`/jupyter/lab/tree/${nb.jupyter_path}`}
                target="_blank"
                rel="noreferrer"
                className={buttonVariants({ variant: "outline", size: "sm" })}
              >
                Open
                <ExternalLink className="h-3.5 w-3.5" />
              </a>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Direct access</CardTitle>
          <CardDescription>
            If the proxied URL shows a blank page, open JupyterLab directly at{" "}
            <a
              href="http://127.0.0.1:8888/jupyter/lab/tree/notebooks"
              target="_blank"
              rel="noreferrer"
              className="text-link underline hover:text-[var(--link-hover)]"
            >
              http://127.0.0.1:8888/jupyter/lab/tree/notebooks
            </a>{" "}
            while <code className="text-xs">./scripts/dev.sh</code> is running.
          </CardDescription>
        </CardHeader>
      </Card>
    </div>
  );
}
