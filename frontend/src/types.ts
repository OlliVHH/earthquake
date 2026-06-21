// Human: Shared TypeScript contracts for API responses, filters, and view modes.
// Agent: READS none; WRITES none; types only — no runtime logic.
/** Shared API and domain types. */

// --- Earthquake list API ---

// Human: Single earthquake row from list/detail endpoints.
// Agent: HTTP shape from /earthquakes; DB fields mapped to camel-ish API names.
export interface Earthquake {
  event_id: string;
  time_utc: string;
  latitude: number;
  longitude: number;
  depth_km: number;
  magnitude: number | null;
  mag_type: string | null;
  location_name: string | null;
}

// Human: Paginated list wrapper with total count and slice metadata.
// Agent: HTTP response from GET /earthquakes.
export interface EarthquakeListResponse {
  items: Earthquake[];
  total: number;
  limit: number;
  offset: number;
}

// --- Map API ---

// Human: Lightweight point for map markers and heatmap layers.
// Agent: HTTP shape from /earthquakes/map points array.
export interface MapPoint {
  event_id: string;
  latitude: number;
  longitude: number;
  magnitude: number | null;
  time_utc: string;
  location_name: string | null;
}

// Human: Map endpoint response with point collection and total.
// Agent: HTTP response from GET /earthquakes/map.
export interface MapPointsResponse {
  points: MapPoint[];
  total: number;
}

// --- Stats and sync ---

// Human: Aggregate stats for the current filter set (count, magnitude range, time span).
// Agent: HTTP response from GET /earthquakes/stats.
export interface EarthquakeStats {
  count: number;
  max_magnitude: number | null;
  min_time: string | null;
  max_time: string | null;
}

// Human: One sync job row from /sync/status.
// Agent: HTTP shape; READS key, status, timestamps, message.
export interface SyncStatusItem {
  key: string;
  status: string;
  last_success_at: string | null;
  last_updatedafter: string | null;
  message: string | null;
  progress_percent: number;
}

// --- UI filter state ---

// Human: Dashboard filter fields — URL-synced strings before API param mapping.
// Agent: WRITES via useFilters; keys match URL query param names.
export interface FilterState {
  startDate: string;
  endDate: string;
  minMagnitude: string;
  maxMagnitude: string;
  minDepth: string;
  maxDepth: string;
  minLat: string;
  maxLat: string;
  minLon: string;
  maxLon: string;
  locationQuery: string;
  regionPreset: string;
  sort: string;
}

// Human: Dashboard visualization mode — table list, point map, or heatmap.
// Agent: UI-only enum; drives EarthquakeTable vs MapView layer visibility.
export type ViewMode = "table" | "map" | "heatmap";
