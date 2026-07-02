import { BookOpen, Flag, Import, Table2 } from "lucide-react";
import { Link, useLocation } from "react-router-dom";
import { DebugToggle } from "@/components/DebugPanel";
import { ThemeToggle } from "@/components/ThemeToggle";
import { useReportMatchError } from "@/lib/reportContext";
import { cn } from "@/lib/utils";

const nav = [
  { to: "/", label: "Import", icon: Import },
  { to: "/notebooks", label: "Notebooks", icon: BookOpen },
];

export function Layout({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  const { openReport } = useReportMatchError();

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-accent-border bg-accent text-accent-foreground shadow-sm">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-md bg-foreground/10">
              <Table2 className="h-5 w-5 text-primary" />
            </div>
            <div>
              <p className="text-sm font-bold tracking-tight">
                make master BOM
              </p>
              <p className="text-xs opacity-70">
                McMaster-Carr link generator
              </p>
            </div>
          </div>
          <div className="flex items-center gap-1">
            <nav className="flex items-center gap-1">
              {nav.map(({ to, label, icon: Icon }) => {
                const active = location.pathname === to;
                return (
                  <Link
                    key={to}
                    to={to}
                    className={cn(
                      "inline-flex items-center gap-2 border-b-2 px-3 py-2 text-sm font-medium transition-colors",
                      active
                        ? "border-primary text-foreground"
                        : "border-transparent opacity-75 hover:border-foreground/20 hover:opacity-100",
                    )}
                  >
                    <Icon className="h-4 w-4" />
                    {label}
                  </Link>
                );
              })}
              <button
                type="button"
                onClick={() => openReport()}
                title="Report matching error"
                className={cn(
                  "inline-flex items-center gap-2 border-b-2 border-transparent px-3 py-2 text-sm font-medium transition-colors",
                  "opacity-75 hover:border-foreground/20 hover:opacity-100",
                )}
              >
                <Flag className="h-4 w-4" />
                Report error
              </button>
            </nav>
            <DebugToggle />
            <ThemeToggle />
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-8">{children}</main>
    </div>
  );
}
