import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { apiFetch, buildQuery, setToken } from "../api/client";
import { EarthquakeTable } from "../components/EarthquakeTable";
import { FilterBar } from "../components/FilterBar";
import { MapView } from "../components/MapView";
import { useFilters } from "../hooks/useFilters";
import type {
  EarthquakeListResponse,
  EarthquakeStats,
  FilterState,
  MapPointsResponse,
  SyncStatusItem,
  ViewMode,
} from "../types";

/** Main analytics dashboard with table, map, and heatmap views. */
export function DashboardPage() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const { filters, setFilters, resetFilters, queryParams } = useFilters();

  const [draftFilters, setDraftFilters] = useState<FilterState>(filters);
  const [view, setView] = useState<ViewMode>("table");
  const [offset, setOffset] = useState(0);
  const limit = 50;

  const [list, setList] = useState<EarthquakeListResponse | null>(null);
  const [mapPoints, setMapPoints] = useState<MapPointsResponse | null>(null);
  const [stats, setStats] = useState<EarthquakeStats | null>(null);
  const [syncItems, setSyncItems] = useState<SyncStatusItem[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setDraftFilters(filters);
  }, [filters]);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const qs = buildQuery({ ...queryParams, limit, offset });
      const mapQs = buildQuery({ ...queryParams, limit: 10000 });
      const statsQs = buildQuery(queryParams);

      const [listRes, mapRes, statsRes, syncRes] = await Promise.all([
        apiFetch<EarthquakeListResponse>(`/earthquakes${qs}`),
        apiFetch<MapPointsResponse>(`/earthquakes/map${mapQs}`),
        apiFetch<EarthquakeStats>(`/earthquakes/stats${statsQs}`),
        apiFetch<{ items: SyncStatusItem[] }>("/sync/status"),
      ]);

      setList(listRes);
      setMapPoints(mapRes);
      setStats(statsRes);
      setSyncItems(syncRes.items);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [queryParams, offset]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const applyFilters = () => {
    setOffset(0);
    setFilters(draftFilters);
  };

  const onBBoxChange = (bbox: Pick<FilterState, "minLat" | "maxLat" | "minLon" | "maxLon">) => {
    setDraftFilters((prev) => ({ ...prev, ...bbox }));
    setFilters({ ...filters, ...bbox });
  };

  const logout = () => {
    setToken(null);
    navigate("/login");
  };

  const changeLanguage = (lng: string) => {
    void i18n.changeLanguage(lng);
    localStorage.setItem("earthquake_lang", lng);
  };

  const triggerSync = async () => {
    await apiFetch("/sync/trigger", { method: "POST" });
    void loadData();
  };

  return (
    <div className="dashboard">
      <header className="topbar">
        <h1>{t("appTitle")}</h1>
        <div className="topbar-actions">
          <label>
            {t("language")}
            <select value={i18n.language} onChange={(e) => changeLanguage(e.target.value)}>
              <option value="de">DE</option>
              <option value="en">EN</option>
            </select>
          </label>
          <button type="button" className="secondary" onClick={() => void triggerSync()}>{t("triggerSync")}</button>
          <button type="button" className="secondary" onClick={logout}>{t("logout")}</button>
        </div>
      </header>

      <FilterBar
        filters={draftFilters}
        onChange={setDraftFilters}
        onApply={applyFilters}
        onReset={() => {
          resetFilters();
          setDraftFilters({
            startDate: "", endDate: "", minMagnitude: "", maxMagnitude: "",
            minDepth: "", maxDepth: "", minLat: "", maxLat: "", minLon: "", maxLon: "",
            locationQuery: "", regionPreset: "", sort: "time_desc",
          });
        }}
      />

      <section className="stats-bar">
        {loading ? (
          <span>{t("loading")}</span>
        ) : (
          <>
            <span>{t("total")}: {stats?.count ?? 0}</span>
            <span>{t("maxMag")}: {stats?.max_magnitude?.toFixed(1) ?? "—"}</span>
          </>
        )}
      </section>

      <section className="sync-bar">
        <strong>{t("syncStatus")}:</strong>
        {syncItems.map((item) => (
          <span key={item.key} className="sync-chip">
            {item.key}: {item.status} {item.message ? `— ${item.message}` : ""}
          </span>
        ))}
      </section>

      <div className="view-tabs">
        <button type="button" className={view === "table" ? "active" : ""} onClick={() => setView("table")}>{t("viewTable")}</button>
        <button type="button" className={view === "map" ? "active" : ""} onClick={() => setView("map")}>{t("viewMap")}</button>
        <button type="button" className={view === "heatmap" ? "active" : ""} onClick={() => setView("heatmap")}>{t("viewHeatmap")}</button>
      </div>

      {view === "table" ? (
        <EarthquakeTable
          rows={list?.items ?? []}
          total={list?.total ?? 0}
          offset={offset}
          limit={limit}
          onPageChange={setOffset}
        />
      ) : (
        <MapView
          points={mapPoints?.points ?? []}
          mode={view}
          filters={filters}
          onBBoxChange={onBBoxChange}
        />
      )}
    </div>
  );
}
