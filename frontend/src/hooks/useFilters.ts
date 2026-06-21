/** Default filter values and URL query synchronization. */

import { useCallback, useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import type { FilterState } from "../types";

const DEFAULTS: FilterState = {
  startDate: "",
  endDate: "",
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

function readFilters(params: URLSearchParams): FilterState {
  const next = { ...DEFAULTS };
  for (const key of Object.keys(DEFAULTS) as (keyof FilterState)[]) {
    const value = params.get(key);
    if (value) {
      next[key] = value;
    }
  }
  return next;
}

function toApiDate(value: string, endOfDay: boolean): string {
  if (!value) {
    return "";
  }
  if (value.includes("T")) {
    return value;
  }
  return endOfDay ? `${value}T23:59:59` : `${value}T00:00:00`;
}

export function useFilters() {
  const [searchParams, setSearchParams] = useSearchParams();
  const filters = useMemo(() => readFilters(searchParams), [searchParams]);

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

  const resetFilters = useCallback(() => setFilters(DEFAULTS), [setFilters]);

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
