// Human: Filter bar UI — date, magnitude, depth, region preset, location search.
// Agent: READS filters prop; WRITES via onChange/onApply/onReset callbacks; no HTTP.
import { useTranslation } from "react-i18next";
import type { FilterState } from "../types";

// Human: Backend region_preset keys offered in the preset dropdown.
// Agent: READS preset strings; empty string means no preset.
const PRESETS = [
  "",
  "global",
  "europe",
  "north_america",
  "south_america",
  "asia",
  "pacific_ring",
  "middle_east",
  "africa",
  "oceania",
];

interface Props {
  filters: FilterState;
  onChange: (next: FilterState) => void;
  onApply: () => void;
  onReset: () => void;
}

// Human: Dashboard filter controls — local draft until parent calls onApply.
// Agent: CALLS onChange per field; CALLS onApply/onReset from action buttons.
export function FilterBar({ filters, onChange, onApply, onReset }: Props) {
  const { t } = useTranslation();

  // Human: Update one filter field immutably in parent draft state.
  // Agent: CALLS onChange with spread filters and updated key.
  const update = (key: keyof FilterState, value: string) => {
    onChange({ ...filters, [key]: value });
  };

  return (
    <section className="filter-bar">
      <h2>{t("filters")}</h2>
      {/* Human: Grid of filter inputs — dates, numeric ranges, preset, text search. */}
      {/* Agent: WRITES filter fields via update(); READS filters prop. */}
      <div className="filter-grid">
        <label>
          {t("startDate")}
          <input type="date" value={filters.startDate} onChange={(e) => update("startDate", e.target.value)} />
        </label>
        <label>
          {t("endDate")}
          <input type="date" value={filters.endDate} onChange={(e) => update("endDate", e.target.value)} />
        </label>
        <label>
          {t("minMagnitude")}
          <input type="number" step="0.1" value={filters.minMagnitude} onChange={(e) => update("minMagnitude", e.target.value)} />
        </label>
        <label>
          {t("maxMagnitude")}
          <input type="number" step="0.1" value={filters.maxMagnitude} onChange={(e) => update("maxMagnitude", e.target.value)} />
        </label>
        <label>
          {t("minDepth")}
          <input type="number" value={filters.minDepth} onChange={(e) => update("minDepth", e.target.value)} />
        </label>
        <label>
          {t("maxDepth")}
          <input type="number" value={filters.maxDepth} onChange={(e) => update("maxDepth", e.target.value)} />
        </label>
        <label>
          {t("regionPreset")}
          <select value={filters.regionPreset} onChange={(e) => update("regionPreset", e.target.value)}>
            <option value="">—</option>
            {PRESETS.filter(Boolean).map((key) => (
              <option key={key} value={key}>
                {t(`preset_${key}`)}
              </option>
            ))}
          </select>
        </label>
        <label>
          {t("locationQuery")}
          <input type="text" value={filters.locationQuery} onChange={(e) => update("locationQuery", e.target.value)} />
        </label>
      </div>
      {/* Human: Apply commits draft to URL; Reset clears all filters. */}
      {/* Agent: CALLS onApply and onReset parent handlers. */}
      <div className="filter-actions">
        <button type="button" onClick={onApply}>{t("applyFilters")}</button>
        <button type="button" className="secondary" onClick={onReset}>{t("resetFilters")}</button>
      </div>
    </section>
  );
}
