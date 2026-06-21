// Human: MapLibre map with OSM tiles, earthquake layers, draw-to-filter bbox, and heatmap toggle.
// Agent: READS points/mode/filters props; CALLS onBBoxChange; HTTP none — tiles from openstreetmap.org.
import { syncDrawBBox } from "./mapDrawUtils";
import MapboxDraw from "@mapbox/mapbox-gl-draw";
import maplibregl, { Map, Popup } from "maplibre-gl";
import { useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import type { FilterState, MapPoint, ViewMode } from "../types";

interface Props {
  points: MapPoint[];
  mode: ViewMode;
  filters: FilterState;
  onBBoxChange: (bbox: Pick<FilterState, "minLat" | "maxLat" | "minLon" | "maxLon">) => void;
}

// Human: Interactive map panel — markers or heatmap, polygon draw for spatial filter.
// Agent: WRITES map/draw refs; READS points, mode; CALLS syncDrawBBox and onBBoxChange on draw events.
export function MapView({ points, mode, filters, onBBoxChange }: Props) {
  const { t, i18n } = useTranslation();
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<Map | null>(null);
  const drawRef = useRef<MapboxDraw | null>(null);
  // Human: Stable ref so map init effect does not re-run when parent re-renders (e.g. sync polling).
  // Agent: READS latest onBBoxChange; WRITES onBBoxChangeRef.current each render; avoids map teardown.
  const onBBoxChangeRef = useRef(onBBoxChange);
  onBBoxChangeRef.current = onBBoxChange;

  // --- Map initialization (once) ---
  // Human: Create MapLibre map, OSM raster, navigation, and MapboxDraw for bbox.
  // Agent: CALLS maplibregl.Map, MapboxDraw; WRITES mapRef/drawRef; cleanup removes map on unmount.
  useEffect(() => {
    if (!containerRef.current || mapRef.current) {
      return;
    }

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: {
        version: 8,
        sources: {
          osm: {
            type: "raster",
            tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
            tileSize: 256,
            attribution: "© OpenStreetMap contributors",
          },
        },
        layers: [{ id: "osm", type: "raster", source: "osm" }],
      },
      center: [10, 20],
      zoom: 1.5,
    });

    map.addControl(new maplibregl.NavigationControl(), "top-right");

    const draw = new MapboxDraw({
      displayControlsDefault: false,
      controls: { polygon: false, trash: true },
      defaultMode: "simple_select",
    });
    map.addControl(draw as unknown as maplibregl.IControl, "top-left");
    drawRef.current = draw;

    // Human: Push drawn polygon bounds to parent filters on create/update.
    // Agent: CALLS syncDrawBBox via onBBoxChangeRef so parent re-renders do not recreate the map.
    const syncBBox = () => {
      if (drawRef.current) {
        syncDrawBBox(drawRef.current, (bbox) => onBBoxChangeRef.current(bbox));
      }
    };

    map.on("draw.create", syncBBox);
    map.on("draw.update", syncBBox);
  // Human: Deleting draw clears spatial filter fields.
  // Agent: CALLS onBBoxChangeRef with empty min/max lat/lon strings.
    map.on("draw.delete", () =>
      onBBoxChangeRef.current({ minLat: "", maxLat: "", minLon: "", maxLon: "" }),
    );

    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
      drawRef.current = null;
    };
  }, []);

  // --- Layer updates when points or mode change ---
  // Human: Refresh GeoJSON source and toggle heatmap vs circle visibility.
  // Agent: READS points, mode; WRITES map layers eq-heatmap and eq-points; HTTP tile clicks show Popup.
  useEffect(() => {
    const map = mapRef.current;
    if (!map) {
      return;
    }

    const geojson: GeoJSON.FeatureCollection = {
      type: "FeatureCollection",
      features: points.map((p) => ({
        type: "Feature",
        geometry: { type: "Point", coordinates: [p.longitude, p.latitude] },
        properties: {
          event_id: p.event_id,
          magnitude: p.magnitude ?? 0,
          location_name: p.location_name,
          time_utc: p.time_utc,
        },
      })),
    };

    const updateLayers = () => {
      if (map.getSource("earthquakes")) {
        (map.getSource("earthquakes") as maplibregl.GeoJSONSource).setData(geojson);
      } else {
        map.addSource("earthquakes", { type: "geojson", data: geojson });
      }

      const showHeatmap = mode === "heatmap";

      if (!map.getLayer("eq-heatmap")) {
        map.addLayer({
          id: "eq-heatmap",
          type: "heatmap",
          source: "earthquakes",
          paint: {
            "heatmap-weight": ["interpolate", ["linear"], ["get", "magnitude"], 0, 0, 8, 1],
            "heatmap-intensity": 1,
            "heatmap-radius": 20,
          },
          layout: { visibility: showHeatmap ? "visible" : "none" },
        });
      } else {
        map.setLayoutProperty("eq-heatmap", "visibility", showHeatmap ? "visible" : "none");
      }

      if (!map.getLayer("eq-points")) {
        map.addLayer({
          id: "eq-points",
          type: "circle",
          source: "earthquakes",
          paint: {
            "circle-radius": ["interpolate", ["linear"], ["get", "magnitude"], 0, 3, 8, 12],
            "circle-color": "#e74c3c",
            "circle-opacity": 0.75,
          },
          layout: { visibility: showHeatmap ? "none" : "visible" },
        });

        // Human: Click marker to show popup with location, magnitude, and localized time.
        // Agent: READS feature properties; WRITES Popup HTML to map.
        map.on("click", "eq-points", (e) => {
          const feature = e.features?.[0];
          if (!feature) {
            return;
          }
          const props = feature.properties ?? {};
          new Popup()
            .setLngLat(e.lngLat)
            .setHTML(
              `<strong>${props.location_name ?? ""}</strong><br/>` +
                `M ${props.magnitude ?? "—"}<br/>` +
                `${new Date(props.time_utc).toLocaleString(i18n.language)}`,
            )
            .addTo(map);
        });
        map.on("mouseenter", "eq-points", () => {
          map.getCanvas().style.cursor = "pointer";
        });
        map.on("mouseleave", "eq-points", () => {
          map.getCanvas().style.cursor = "";
        });
      } else {
        map.setLayoutProperty("eq-points", "visibility", showHeatmap ? "none" : "visible");
      }
    };

    if (map.isStyleLoaded()) {
      updateLayers();
    } else {
      map.once("load", updateLayers);
    }
  }, [points, mode, i18n.language]);

  // Human: Enter polygon draw mode for spatial bbox filter.
  // Agent: CALLS drawRef.changeMode draw_polygon.
  const startDraw = () => {
    drawRef.current?.changeMode("draw_polygon");
  };

  // Human: Remove all drawn shapes and clear bbox filter fields.
  // Agent: CALLS draw.deleteAll; CALLS onBBoxChange with empty bounds.
  const clearDraw = () => {
    drawRef.current?.deleteAll();
    onBBoxChange({ minLat: "", maxLat: "", minLon: "", maxLon: "" });
  };

  // Human: Zoom map to fit all current result points.
  // Agent: READS points; CALLS map.fitBounds; failure mode — no-op when map missing or points empty.
  const fitResults = () => {
    const map = mapRef.current;
    if (!map || points.length === 0) {
      return;
    }
    const bounds = new maplibregl.LngLatBounds();
    for (const p of points) {
      bounds.extend([p.longitude, p.latitude]);
    }
    map.fitBounds(bounds, { padding: 40, maxZoom: 10 });
  };

  return (
    <div className="map-panel">
      {/* Human: Toolbar — draw bbox, clear, fit to results, active bbox hint. */}
      {/* Agent: CALLS startDraw, clearDraw, fitResults; READS filters for bbox hint. */}
      <div className="map-toolbar">
        <button type="button" onClick={startDraw}>{t("drawBBox")}</button>
        <button type="button" className="secondary" onClick={clearDraw}>{t("clearBBox")}</button>
        <button type="button" className="secondary" onClick={fitResults}>{t("fitResults")}</button>
        {(filters.minLat || filters.maxLat) && (
          <span className="bbox-hint">
            BBox: {filters.minLat}, {filters.minLon} → {filters.maxLat}, {filters.maxLon}
          </span>
        )}
      </div>
      {/* Human: MapLibre container element — map attaches to this div ref. */}
      {/* Agent: READS containerRef; WRITES map instance into mapRef. */}
      <div ref={containerRef} className="map-container" />
    </div>
  );
}
