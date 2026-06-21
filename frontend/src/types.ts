/** Shared API and domain types. */

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

export interface EarthquakeListResponse {
  items: Earthquake[];
  total: number;
  limit: number;
  offset: number;
}

export interface MapPoint {
  event_id: string;
  latitude: number;
  longitude: number;
  magnitude: number | null;
  time_utc: string;
  location_name: string | null;
}

export interface MapPointsResponse {
  points: MapPoint[];
  total: number;
}

export interface EarthquakeStats {
  count: number;
  max_magnitude: number | null;
  min_time: string | null;
  max_time: string | null;
}

export interface SyncStatusItem {
  key: string;
  status: string;
  last_success_at: string | null;
  last_updatedafter: string | null;
  message: string | null;
}

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

export type ViewMode = "table" | "map" | "heatmap";
