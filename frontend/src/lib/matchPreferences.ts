/**
 * Client-side matching preferences (localStorage).
 *
 * Defaults match today's pipeline behavior: lazy guesses (wider scope allowed),
 * length-filtered browse when length is known, and wider-scope alts shown in UI.
 *
 * `guess_mode` / `prefer_length_filter` are persisted for Settings and future
 * rematch API wiring (slice F). Until a rematch endpoint accepts them, only
 * `show_wider_scope_alternatives` affects the BOM editor immediately.
 */

export type GuessMode = "exact" | "lazy";

export interface MatchPreferences {
  guess_mode: GuessMode;
  prefer_length_filter: boolean;
  show_wider_scope_alternatives: boolean;
}

export const MATCH_PREFERENCES_STORAGE_KEY = "makerworld-bom-match-prefs";

export const DEFAULT_MATCH_PREFERENCES: MatchPreferences = {
  guess_mode: "lazy",
  prefer_length_filter: true,
  show_wider_scope_alternatives: true,
};

function isGuessMode(value: unknown): value is GuessMode {
  return value === "exact" || value === "lazy";
}

function isBool(value: unknown): value is boolean {
  return typeof value === "boolean";
}

/** Read prefs from localStorage; missing/invalid keys fall back to defaults. */
export function getMatchPreferences(): MatchPreferences {
  try {
    const raw = localStorage.getItem(MATCH_PREFERENCES_STORAGE_KEY);
    if (!raw) return { ...DEFAULT_MATCH_PREFERENCES };
    const parsed = JSON.parse(raw) as Partial<MatchPreferences>;
    return {
      guess_mode: isGuessMode(parsed.guess_mode)
        ? parsed.guess_mode
        : DEFAULT_MATCH_PREFERENCES.guess_mode,
      prefer_length_filter: isBool(parsed.prefer_length_filter)
        ? parsed.prefer_length_filter
        : DEFAULT_MATCH_PREFERENCES.prefer_length_filter,
      show_wider_scope_alternatives: isBool(parsed.show_wider_scope_alternatives)
        ? parsed.show_wider_scope_alternatives
        : DEFAULT_MATCH_PREFERENCES.show_wider_scope_alternatives,
    };
  } catch {
    return { ...DEFAULT_MATCH_PREFERENCES };
  }
}

export function setMatchPreferences(prefs: MatchPreferences): void {
  localStorage.setItem(MATCH_PREFERENCES_STORAGE_KEY, JSON.stringify(prefs));
}

export function updateMatchPreferences(
  patch: Partial<MatchPreferences>,
): MatchPreferences {
  const next = { ...getMatchPreferences(), ...patch };
  setMatchPreferences(next);
  return next;
}

/**
 * Query/body fields for a future rematch / import options API.
 * Safe to omit when all values equal defaults (preserves today's server behavior).
 */
export function matchPreferencesForApi(
  prefs: MatchPreferences = getMatchPreferences(),
): Record<string, string | boolean> {
  return {
    guess_mode: prefs.guess_mode,
    prefer_length_filter: prefs.prefer_length_filter,
    show_wider_scope_alternatives: prefs.show_wider_scope_alternatives,
  };
}
