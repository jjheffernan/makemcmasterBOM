import { Monitor, Moon, Sun } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useTheme, type Theme } from "@/lib/theme";

const CYCLE: Theme[] = ["light", "dark", "system"];

const LABELS: Record<Theme, string> = {
  light: "Light mode",
  dark: "Dark mode",
  system: "System theme",
};

const ICONS = {
  light: Sun,
  dark: Moon,
  system: Monitor,
} as const;

export function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  const Icon = ICONS[theme];

  function cycle() {
    const index = CYCLE.indexOf(theme);
    setTheme(CYCLE[(index + 1) % CYCLE.length]);
  }

  return (
    <Button
      type="button"
      variant="ghost"
      size="sm"
      onClick={cycle}
      aria-label={LABELS[theme]}
      title={LABELS[theme]}
    >
      <Icon className="h-4 w-4" />
      <span className="sr-only">{LABELS[theme]}</span>
    </Button>
  );
}
