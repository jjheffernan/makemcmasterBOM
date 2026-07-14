import { useCallback, useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Label, Select } from "@/components/ui/select";
import {
  DEFAULT_MATCH_PREFERENCES,
  getMatchPreferences,
  setMatchPreferences,
  type GuessMode,
  type MatchPreferences,
} from "@/lib/matchPreferences";

export function SettingsPage() {
  const [prefs, setPrefs] = useState<MatchPreferences>(() =>
    getMatchPreferences(),
  );
  const [savedAt, setSavedAt] = useState<string | null>(null);

  const persist = useCallback((next: MatchPreferences) => {
    setMatchPreferences(next);
    setPrefs(next);
    setSavedAt(new Date().toLocaleTimeString());
  }, []);

  const setGuessMode = (guess_mode: GuessMode) => {
    persist({ ...prefs, guess_mode });
  };

  const toggle = (key: keyof Pick<
    MatchPreferences,
    "prefer_length_filter" | "show_wider_scope_alternatives"
  >) => {
    persist({ ...prefs, [key]: !prefs[key] });
  };

  const resetDefaults = () => {
    persist({ ...DEFAULT_MATCH_PREFERENCES });
  };

  return (
    <div className="mx-auto max-w-xl space-y-4">
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Matching</CardTitle>
          <CardDescription>
            Stored in this browser only. Defaults match today’s import behavior
            (lazy / length filter on / wider alts shown).
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4 pt-4">
          <div className="grid gap-1.5">
            <Label htmlFor="guess-mode">Guess mode</Label>
            <Select
              id="guess-mode"
              value={prefs.guess_mode}
              onChange={(e) => setGuessMode(e.target.value as GuessMode)}
              className="h-9 max-w-xs text-sm"
            >
              <option value="lazy">
                Lazy — allow wider-scope guesses (current)
              </option>
              <option value="exact">
                Exact — same-size / length-specific first
              </option>
            </Select>
            <p className="text-xs text-muted-foreground">
              Applied when rematch/import options land on the API (slice F). UI
              filtering of wider-scope alternatives uses the toggle below now.
            </p>
          </div>

          <label className="flex cursor-pointer items-start gap-2 text-sm">
            <input
              type="checkbox"
              className="mt-0.5 h-4 w-4 rounded border-border"
              checked={prefs.prefer_length_filter}
              onChange={() => toggle("prefer_length_filter")}
            />
            <span>
              <span className="font-medium">Prefer length-filtered browse</span>
              <span className="mt-0.5 block text-xs text-muted-foreground">
                When length is known, prefer length-specific McMaster browse
                URLs. Backend will honor this with guess_mode wiring.
              </span>
            </span>
          </label>

          <label className="flex cursor-pointer items-start gap-2 text-sm">
            <input
              type="checkbox"
              className="mt-0.5 h-4 w-4 rounded border-border"
              checked={prefs.show_wider_scope_alternatives}
              onChange={() => toggle("show_wider_scope_alternatives")}
            />
            <span>
              <span className="font-medium">Show wider-scope alternatives</span>
              <span className="mt-0.5 block text-xs text-muted-foreground">
                Hide “Wider search” options in the BOM Link column when off.
              </span>
            </span>
          </label>

          <div className="flex flex-wrap items-center gap-3 border-t border-border pt-3">
            <Button type="button" variant="outline" size="sm" onClick={resetDefaults}>
              Reset defaults
            </Button>
            {savedAt && (
              <span className="text-xs text-muted-foreground">
                Saved {savedAt}
              </span>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
