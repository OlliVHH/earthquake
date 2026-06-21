// Human: Filter state hook — mirrors dashboard filters in URL search params and API query map.
// Agent: READS/WRITES URL via react-router useSearchParams; RETURNS filters, setters, queryParams.
/** Default filter values and URL query synchronization. */

import { useCallback, useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import type { FilterState } from "../types";

// Human: Format a local Date as YYYY-MM-DD for HTML date inputs.
// Agent: READS Date; RETURNS date-only string in local calendar.
function formatLocalDate(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

// Human: Monday–Sunday bounds of the current ISO calendar week (local timezone).
// Agent: READS system clock; RETURNS startDate/endDate strings for default filters.
function getCurrentWeekRange(): { startDate: string; endDate: string } {
  const today = new Date();
  const weekday = today.getDay();
  const daysFromMonday = weekday === 0 ? 6 : weekday - 1;

  const monday = new Date(today);
  monday.setDate(today.getDate() - daysFromMonday);

  const sunday = new Date(monday);
  sunday.setDate(monday.getDate() + 6);

  return {
    startDate: formatLocalDate(monday),
    endDate: formatLocalDate(sunday),
  };
}

// Human: Fresh default filters — current calendar week for dates, newest-first sort.
// Agent: CALLS getCurrentWeekRange; RETURNS FilterState; invoked on each reset/read fallback.
export function getDefaultFilters(): FilterState {
  const { startDate, endDate } = getCurrentWeekRange();
  return {
    startDate,
    endDate,
    minMagnitude: "",
    maxMagnitude: "",
    minDepth: "",
    maxDepth: "",
    minLat: "",
    maxLat: "",
    minLon: "",
    maxLon: "",
    locationQuery: "",
    regionPreset: "",
    sort: "time_desc",
  };
}

// Human: Parse URLSearchParams into FilterState, falling back to defaults per key.
// Agent: READS URLSearchParams; CALLS getDefaultFilters; RETURNS FilterState; WRITES none.
function readFilters(params: URLSearchParams): FilterState {
  const next = getDefaultFilters();
  for (const key of Object.keys(next) as (keyof FilterState)[]) {
    const value = params.get(key);
    if (value) {
      next[key] = value;
    }
  }
  return next;
}

// Human: Convert date-only input to API datetime; end-of-day uses T23:59:59.
// Agent: RETURNS ISO-like string or empty; READS value string and endOfDay flag.
function toApiDate(value: string, endOfDay: boolean): string {
  if (!value) {
    return "";
  }
  if (value.includes("T")) {
    return value;
  }
  return endOfDay ? `${value}T23:59:59` : `${value}T00:00:00`;
}

// Human: Hook exposing URL-backed filters, apply/reset, and snake_case API query map.
// Agent: CALLS useSearchParams; RETURNS filters, setFilters, resetFilters, queryParams.
export function useFilters() {
  const [searchParams, setSearchParams] = useSearchParams();
  const filters = useMemo(() => readFilters(searchParams), [searchParams]);

  // Human: Replace URL query with non-empty filter values (replace navigation).
  // Agent: WRITES URLSearchParams via setSearchParams replace:true.
  const setFilters = useCallback(
    (next: FilterState) => {
      const params = new URLSearchParams();
      for (const [key, value] of Object.entries(next)) {
        if (value) {
          params.set(key, value);
        }
      }
      setSearchParams(params, { replace: true });
    },
    [setSearchParams],
  );

  const resetFilters = useCallback(() => setFilters(getDefaultFilters()), [setFilters]);

  // Human: Map UI filter keys to backend query param names and date normalization.
  // Agent: RETURNS Record for buildQuery; READS filters state.
  const queryParams = useMemo(() => {
    const map: Record<string, string> = { sort: filters.sort };
    if (filters.startDate) {
      map.start_date = toApiDate(filters.startDate, false);
    }
    if (filters.endDate) {
      map.end_date = toApiDate(filters.endDate, true);
    }
    if (filters.minMagnitude) map.min_magnitude = filters.minMagnitude;
    if (filters.maxMagnitude) map.max_magnitude = filters.maxMagnitude;
    if (filters.minDepth) map.min_depth = filters.minDepth;
    if (filters.maxDepth) map.max_depth = filters.maxDepth;
    if (filters.minLat) map.min_lat = filters.minLat;
    if (filters.maxLat) map.max_lat = filters.maxLat;
    if (filters.minLon) map.min_lon = filters.minLon;
    if (filters.maxLon) map.max_lon = filters.maxLon;
    if (filters.locationQuery) map.location_query = filters.locationQuery;
    if (filters.regionPreset) map.region_preset = filters.regionPreset;
    return map;
  }, [filters]);

  return { filters, setFilters, resetFilters, queryParams };
}
