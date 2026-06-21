// Human: Main analytics dashboard — filters, stats, sync status, table/map/heatmap views.
// Agent: HTTP GET /earthquakes, /earthquakes/map, /earthquakes/stats, /sync/status; POST /sync/trigger; READS useFilters queryParams.
import { useCallback, useEffect, useRef, useState } from "react";
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

// Human: Dashboard page component — loads data when filters or pagination change.
// Agent: WRITES list/map/stats/sync state; CALLS apiFetch in parallel; failure mode — errors logged, UI shows stale/empty.
export function DashboardPage() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const { filters, setFilters, resetFilters, queryParams } = useFilters();
  // Human: Ref mirrors filters so bbox handler stays stable across sync-status re-renders.
  // Agent: READS filters each render; WRITES filtersRef.current; used by onBBoxChange.
  const filtersRef = useRef(filters);
  filtersRef.current = filters;

  // --- Draft vs applied filters ---
  const [draftFilters, setDraftFilters] = useState<FilterState>(filters);
  const [view, setView] = useState<ViewMode>("table");
  const [offset, setOffset] = useState(0);
  const limit = 50;

  // --- API response state ---
  const [list, setList] = useState<EarthquakeListResponse | null>(null);
  const [mapPoints, setMapPoints] = useState<MapPointsResponse | null>(null);
  const [stats, setStats] = useState<EarthquakeStats | null>(null);
  const [syncItems, setSyncItems] = useState<SyncStatusItem[]>([]);
  const [loading, setLoading] = useState(false);

  // Human: Poll sync status more frequently while backfill or incremental jobs are running.
  // Agent: HTTP GET /sync/status on interval; WRITES syncItems; READS syncItems status field.
  const loadSyncStatus = useCallback(async () => {
    try {
      const syncRes = await apiFetch<{ items: SyncStatusItem[] }>("/sync/status");
      setSyncItems(syncRes.items);
    } catch (err) {
      console.error(err);
    }
  }, []);

  // Human: Keep draft filter inputs aligned when URL filters change (e.g. map bbox).
  // Agent: READS filters; WRITES draftFilters.
  useEffect(() => {
    setDraftFilters(filters);
  }, [filters]);

  // Human: Fetch list, map points, and stats for current filters — sync status is polled separately.
  // Agent: HTTP parallel apiFetch; WRITES list, mapPoints, stats; failure mode — console.error, loading cleared.
  const loadEarthquakeData = useCallback(async () => {
    setLoading(true);
    try {
      const qs = buildQuery({ ...queryParams, limit, offset });
      const mapQs = buildQuery({ ...queryParams, limit: 10000 });
      const statsQs = buildQuery(queryParams);

      const [listRes, mapRes, statsRes] = await Promise.all([
        apiFetch<EarthquakeListResponse>(`/earthquakes${qs}`),
        apiFetch<MapPointsResponse>(`/earthquakes/map${mapQs}`),
        apiFetch<EarthquakeStats>(`/earthquakes/stats${statsQs}`),
      ]);

      setList(listRes);
      setMapPoints(mapRes);
      setStats(statsRes);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [queryParams, offset]);

  // Human: Poll sync status continuously on the dashboard for live backfill progress updates.
  // Agent: HTTP GET /sync/status every 2s; WRITES syncItems; stops when backfill completed and nothing running.
  const backfillItem = syncItems.find((item) => item.key === "backfill");
  const backfillDone = backfillItem?.status === "completed";
  const syncRunning = syncItems.some((item) => item.status === "running");
  const needsLiveSyncPoll = syncRunning || !backfillDone;

  useEffect(() => {
    if (!needsLiveSyncPoll) {
      return;
    }

    void loadSyncStatus();
    const timer = window.setInterval(() => {
      void loadSyncStatus();
    }, 2000);

    return () => window.clearInterval(timer);
  }, [needsLiveSyncPoll, loadSyncStatus]);

  // Human: One initial sync status fetch even when backfill already completed.
  // Agent: HTTP GET /sync/status once on mount when live polling is disabled.
  useEffect(() => {
    if (needsLiveSyncPoll) {
      return;
    }
    void loadSyncStatus();
  }, [needsLiveSyncPoll, loadSyncStatus]);

  useEffect(() => {
    void loadEarthquakeData();
  }, [loadEarthquakeData]);

  // Human: Initial sync status load alongside earthquake data on first mount.
  // Agent: HTTP GET /sync/status once; WRITES syncItems only.
  useEffect(() => {
    void loadSyncStatus();
  }, [loadSyncStatus]);

  // Human: Apply draft filters to URL and reset pagination to first page.
  // Agent: WRITES offset 0; CALLS setFilters with draftFilters.
  const applyFilters = () => {
    setOffset(0);
    setFilters(draftFilters);
  };

  // Human: Map draw tool updates bbox — applies immediately to URL filters; stable callback for MapView.
  // Agent: WRITES draftFilters and filters min/max lat/lon; CALLS setFilters; READS filters via functional update.
  const onBBoxChange = useCallback(
    (bbox: Pick<FilterState, "minLat" | "maxLat" | "minLon" | "maxLon">) => {
      setDraftFilters((prev) => ({ ...prev, ...bbox }));
      setFilters({ ...filtersRef.current, ...bbox });
    },
    [setFilters],
  );

  // Human: Clear token and redirect to login.
  // Agent: WRITES localStorage via setToken(null); CALLS navigate /login.
  const logout = () => {
    setToken(null);
    navigate("/login");
  };

  // Human: Switch UI language and persist preference.
  // Agent: CALLS i18n.changeLanguage; WRITES localStorage earthquake_lang.
  const changeLanguage = (lng: string) => {
    void i18n.changeLanguage(lng);
    localStorage.setItem("earthquake_lang", lng);
  };

  // Human: Trigger backend sync job then refresh earthquake data (not map teardown via sync poll).
  // Agent: HTTP POST /sync/trigger; CALLS loadSyncStatus and loadEarthquakeData.
  const triggerSync = async () => {
    await apiFetch("/sync/trigger", { method: "POST" });
    void loadSyncStatus();
    void loadEarthquakeData();
  };

  // Human: Map sync_state keys to localized labels for the progress panel.
  // Agent: READS item.key; RETURNS i18n string for backfill vs incremental rows.
  const syncLabel = (key: string) => {
    if (key === "backfill") {
      return t("syncBackfill");
    }
    if (key === "incremental") {
      return t("syncIncremental");
    }
    return key;
  };

  // Human: Incremental sync waits until backfill completes; show 0% instead of stale 100%.
  // Agent: READS syncItems backfill status; RETURNS rounded percent for progress bar width.
  const displayPercent = (item: SyncStatusItem) => {
    if (item.key === "incremental") {
      const backfill = syncItems.find((row) => row.key === "backfill");
      if (backfill && backfill.status !== "completed") {
        return 0;
      }
    }
    return Math.round(item.progress_percent ?? 0);
  };

  return (
    <div className="dashboard">
      {/* Human: Top bar — title, language, sync trigger, logout. */}
      {/* Agent: CALLS changeLanguage, triggerSync, logout on user actions. */}
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

      {/* Human: Filter panel — edits draft until Apply. */}
      {/* Agent: READS draftFilters; WRITES via setDraftFilters; CALLS applyFilters/resetFilters. */}
      <FilterBar
        filters={draftFilters}
        onChange={setDraftFilters}
        onApply={applyFilters}
        onReset={() => {
          resetFilters();
        }}
      />

      {/* Human: Summary stats for filtered dataset. */}
      {/* Agent: READS stats, loading; DISPLAYS count and max magnitude. */}
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

      {/* Human: Per-source sync job status with live percentage progress bars. */}
      {/* Agent: READS syncItems from /sync/status; DISPLAYS progress_percent and message. */}
      <section className="sync-bar">
        <strong>{t("syncStatus")}</strong>
        <div className="sync-progress-list">
          {syncItems.map((item) => {
            const percent = displayPercent(item);
            const waitingForBackfill =
              item.key === "incremental" &&
              syncItems.some((row) => row.key === "backfill" && row.status !== "completed");
            return (
              <div key={item.key} className="sync-progress-item">
                <div className="sync-progress-header">
                  <span className="sync-progress-label">{syncLabel(item.key)}</span>
                  <span className="sync-progress-meta">
                    {item.status} · {t("syncProgress", { percent })}
                  </span>
                </div>
                <div
                  className="sync-progress-track"
                  role="progressbar"
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-valuenow={percent}
                  aria-label={`${syncLabel(item.key)} ${percent}%`}
                >
                  <div className="sync-progress-fill" style={{ width: `${percent}%` }} />
                </div>
                {waitingForBackfill ? (
                  <span className="sync-progress-message">{t("syncWaitingBackfill")}</span>
                ) : null}
                {item.message ? <span className="sync-progress-message">{item.message}</span> : null}
              </div>
            );
          })}
        </div>
      </section>

      {/* Human: View mode tabs — table, map markers, heatmap. */}
      {/* Agent: WRITES view state; toggles EarthquakeTable vs MapView. */}
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
