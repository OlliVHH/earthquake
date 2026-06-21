/** Sync bounding box from drawn polygon to parent filters. */

import type MapboxDraw from "@mapbox/mapbox-gl-draw";
import type { FilterState } from "../types";

export function syncDrawBBox(
  draw: MapboxDraw,
  onBBoxChange: (bbox: Pick<FilterState, "minLat" | "maxLat" | "minLon" | "maxLon">) => void,
): void {
  const data = draw.getAll();
  const feature = data.features[0];
  if (!feature || feature.geometry.type !== "Polygon") {
    return;
  }
  const coords = feature.geometry.coordinates[0] as [number, number][];
  const lons = coords.map((c) => c[0]);
  const lats = coords.map((c) => c[1]);
  onBBoxChange({
    minLon: String(Math.min(...lons)),
    maxLon: String(Math.max(...lons)),
    minLat: String(Math.min(...lats)),
    maxLat: String(Math.max(...lats)),
  });
}
