// Human: MapLibre map with OSM tiles, earthquake layers, draw-to-filter bbox, and heatmap toggle.
// Agent: READS points/mode/filters props; CALLS onBBoxChange; HTTP none — tiles from openstreetmap.org.
import { syncDrawBBox } from "./mapDrawUtils";
import { createRadiusCircleGeoJson } from "./mapCircleUtils";
import MapboxDraw from "@mapbox/mapbox-gl-draw";
import maplibregl, { Map, Popup } from "maplibre-gl";
import { useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import type { FilterState, MapFocusContext, MapPoint, ViewMode } from "../types";

interface Props {
  points: MapPoint[];
  mode: ViewMode;
  filters: FilterState;
  focus?: MapFocusContext | null;
  onBBoxChange: (bbox: Pick<FilterState, "minLat" | "maxLat" | "minLon" | "maxLon">) => void;
}

// Human: Escape user/API strings before embedding in popup HTML.
// Agent: READS raw string; RETURNS HTML-safe string for setHTML.
function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

// Human: Build readable popup markup with fixed dark-on-white colors.
// Agent: READS feature properties + i18n labels; RETURNS HTML string for MapLibre Popup.
function buildEarthquakePopupHtml(
  props: Record<string, GeoJSON.GeoJsonProperties | undefined>,
  language: string,
  labels: { magnitude: string; time: string },
): string {
  const location = String(props.location_name ?? "");
  const magnitude = props.magnitude ?? "—";
  const timeUtc = props.time_utc
    ? new Date(String(props.time_utc)).toLocaleString(language)
    : "—";

  return (
    `<div class="earthquake-popup">` +
    `<div class="earthquake-popup__location">${escapeHtml(location)}</div>` +
    `<div class="earthquake-popup__row">${escapeHtml(labels.magnitude)}: M ${escapeHtml(String(magnitude))}</div>` +
    `<div class="earthquake-popup__row">${escapeHtml(labels.time)}: ${escapeHtml(timeUtc)}</div>` +
    `</div>`
  );
}

// Human: Interactive map panel — markers or heatmap, polygon draw for spatial filter, table focus overlay.
// Agent: WRITES map/draw refs; READS points, mode, focus; CALLS syncDrawBBox and onBBoxChange on draw events.
export function MapView({ points, mode, filters, focus, onBBoxChange }: Props) {
  const { t, i18n } = useTranslation();
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<Map | null>(null);
  const drawRef = useRef<MapboxDraw | null>(null);
  // Human: Stable ref so map init effect does not re-run when parent re-renders (e.g. sync polling).
  // Agent: READS latest onBBoxChange; WRITES onBBoxChangeRef.current each render; avoids map teardown.
  const onBBoxChangeRef = useRef(onBBoxChange);
  onBBoxChangeRef.current = onBBoxChange;
  const popupRef = useRef<Popup | null>(null);
  const popupLabelsRef = useRef({ magnitude: t("magnitude"), time: t("time") });
  const languageRef = useRef(i18n.language);
  popupLabelsRef.current = { magnitude: t("magnitude"), time: t("time") };
  languageRef.current = i18n.language;

  // Human: Show one popup for map marker or heatmap click; closes any previous popup first.
  // Agent: READS feature properties; WRITES MapLibre Popup; CALLS buildEarthquakePopupHtml.
  const showEarthquakePopup = (map: Map, lngLat: maplibregl.LngLatLike, props: Record<string, unknown>) => {
    popupRef.current?.remove();
    popupRef.current = new Popup({
      className: "earthquake-popup-container",
      closeButton: true,
      maxWidth: "320px",
    })
      .setLngLat(lngLat)
      .setHTML(
        buildEarthquakePopupHtml(
          props as Record<string, GeoJSON.GeoJsonProperties | undefined>,
          languageRef.current,
          popupLabelsRef.current,
        ),
      )
      .addTo(map);
  };

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

    // Human: Map/heatmap clicks query invisible eq-points layer for feature details popup.
    // Agent: CALLS queryRenderedFeatures on eq-points; WRITES popup via showEarthquakePopup ref.
    map.on("click", (e) => {
      if (!map.getLayer("eq-points")) {
        return;
      }
      const features = map.queryRenderedFeatures(e.point, { layers: ["eq-points"] });
      const feature = features[0];
      if (!feature) {
        return;
      }
      showEarthquakePopup(map, e.lngLat, feature.properties ?? {});
    });

    map.on("mouseenter", "eq-points", () => {
      map.getCanvas().style.cursor = "pointer";
    });
    map.on("mouseleave", "eq-points", () => {
      map.getCanvas().style.cursor = "";
    });

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
          emphasis: p.emphasis ?? "",
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
            "circle-radius": showHeatmap
              ? [
                  "match",
                  ["get", "emphasis"],
                  "selected",
                  18,
                  "nearby",
                  12,
                  ["interpolate", ["linear"], ["get", "magnitude"], 0, 10, 8, 22],
                ]
              : [
                  "match",
                  ["get", "emphasis"],
                  "selected",
                  14,
                  "nearby",
                  8,
                  ["interpolate", ["linear"], ["get", "magnitude"], 0, 3, 8, 12],
                ],
            "circle-color": [
              "match",
              ["get", "emphasis"],
              "selected",
              "#2563eb",
              "nearby",
              "#f59e0b",
              "#e74c3c",
            ],
            "circle-opacity": showHeatmap ? 0 : 0.85,
            "circle-stroke-width": ["match", ["get", "emphasis"], "selected", 3, 0],
            "circle-stroke-color": "#ffffff",
          },
        });
      } else {
        // Human: Keep eq-points queryable in heatmap mode via opacity 0 (visibility:none blocks clicks).
        // Agent: WRITES circle-opacity, radius, and emphasis colors when heatmap is active.
        map.setPaintProperty("eq-points", "circle-opacity", showHeatmap ? 0 : 0.85);
        map.setPaintProperty(
          "eq-points",
          "circle-radius",
          showHeatmap
            ? [
                "match",
                ["get", "emphasis"],
                "selected",
                18,
                "nearby",
                12,
                ["interpolate", ["linear"], ["get", "magnitude"], 0, 10, 8, 22],
              ]
            : [
                "match",
                ["get", "emphasis"],
                "selected",
                14,
                "nearby",
                8,
                ["interpolate", ["linear"], ["get", "magnitude"], 0, 3, 8, 12],
              ],
        );
        map.setPaintProperty("eq-points", "circle-color", [
          "match",
          ["get", "emphasis"],
          "selected",
          "#2563eb",
          "nearby",
          "#f59e0b",
          "#e74c3c",
        ]);
        map.setPaintProperty("eq-points", "circle-stroke-width", [
          "match",
          ["get", "emphasis"],
          "selected",
          3,
          0,
        ]);
      }
    };

    if (map.isStyleLoaded()) {
      updateLayers();
    } else {
      map.once("load", updateLayers);
    }
  }, [points, mode, i18n.language]);

  // Human: When user selects a table row, center map, draw 100 km circle, and open popup.
  // Agent: READS focus; WRITES focus-radius layers; CALLS flyTo and showEarthquakePopup.
  useEffect(() => {
    const map = mapRef.current;
    if (!map) {
      return;
    }

    const applyFocus = () => {
      if (!focus) {
        if (map.getLayer("focus-radius-fill")) {
          map.setLayoutProperty("focus-radius-fill", "visibility", "none");
        }
        if (map.getLayer("focus-radius-line")) {
          map.setLayoutProperty("focus-radius-line", "visibility", "none");
        }
        return;
      }

      const circle = createRadiusCircleGeoJson(focus.longitude, focus.latitude, focus.radiusKm);
      if (map.getSource("focus-radius")) {
        (map.getSource("focus-radius") as maplibregl.GeoJSONSource).setData(circle);
      } else {
        map.addSource("focus-radius", { type: "geojson", data: circle });
        map.addLayer({
          id: "focus-radius-fill",
          type: "fill",
          source: "focus-radius",
          paint: { "fill-color": "#3b82f6", "fill-opacity": 0.1 },
        });
        map.addLayer({
          id: "focus-radius-line",
          type: "line",
          source: "focus-radius",
          paint: { "line-color": "#3b82f6", "line-width": 2, "line-opacity": 0.65 },
        });
      }

      if (map.getLayer("focus-radius-fill")) {
        map.setLayoutProperty("focus-radius-fill", "visibility", "visible");
      }
      if (map.getLayer("focus-radius-line")) {
        map.setLayoutProperty("focus-radius-line", "visibility", "visible");
      }

      map.flyTo({
        center: [focus.longitude, focus.latitude],
        zoom: 7,
        essential: true,
      });

      showEarthquakePopup(map, [focus.longitude, focus.latitude], {
        location_name: focus.locationName,
        magnitude: focus.magnitude,
        time_utc: focus.timeUtc,
        emphasis: "selected",
      });
    };

    if (map.isStyleLoaded()) {
      applyFocus();
    } else {
      map.once("load", applyFocus);
    }
  }, [focus]);

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
