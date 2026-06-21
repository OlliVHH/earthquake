// Human: Persisted table column selection for the earthquake list (localStorage).
// Agent: READS/WRITES localStorage earthquake_table_columns; RETURNS visible column keys and setter.
import { useCallback, useMemo, useState } from "react";

// Human: All USGS-backed fields exposed as optional table columns.
// Agent: UI column keys; maps to Earthquake interface and i18n labels.
export type TableColumnKey =
  | "event_id"
  | "time_utc"
  | "location_name"
  | "magnitude"
  | "mag_type"
  | "depth_km"
  | "latitude"
  | "longitude"
  | "author"
  | "catalog"
  | "contributor"
  | "updated_at"
  | "fetched_at"
  | "coordinates";

// Human: Default visible columns matching the original table layout.
// Agent: READ on first visit; WRITTEN when user resets column picker.
export const DEFAULT_TABLE_COLUMNS: TableColumnKey[] = [
  "time_utc",
  "location_name",
  "magnitude",
  "depth_km",
  "coordinates",
];

// Human: Full catalog of selectable columns in display order.
// Agent: READ by column picker UI; order defines checkbox list sequence.
export const ALL_TABLE_COLUMNS: TableColumnKey[] = [
  "event_id",
  "time_utc",
  "location_name",
  "magnitude",
  "mag_type",
  "depth_km",
  "latitude",
  "longitude",
  "coordinates",
  "author",
  "catalog",
  "contributor",
  "updated_at",
  "fetched_at",
];

const STORAGE_KEY = "earthquake_table_columns";

// Human: Parse stored column JSON; fall back to defaults when missing or invalid.
// Agent: READS localStorage; RETURNS TableColumnKey[]; failure modes: corrupt JSON -> defaults.
function readStoredColumns(): TableColumnKey[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return DEFAULT_TABLE_COLUMNS;
    }
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) {
      return DEFAULT_TABLE_COLUMNS;
    }
    const allowed = new Set(ALL_TABLE_COLUMNS);
    const columns = parsed.filter((key): key is TableColumnKey => typeof key === "string" && allowed.has(key as TableColumnKey));
    return columns.length > 0 ? columns : DEFAULT_TABLE_COLUMNS;
  } catch {
    return DEFAULT_TABLE_COLUMNS;
  }
}

// Human: Hook exposing visible table columns with persistent user customization.
// Agent: WRITES localStorage on setColumns/resetColumns; RETURNS columns and picker helpers.
export function useTableColumns() {
  const [columns, setColumnsState] = useState<TableColumnKey[]>(() => readStoredColumns());

  const setColumns = useCallback((next: TableColumnKey[]) => {
    const allowed = new Set(ALL_TABLE_COLUMNS);
    const sanitized = next.filter((key) => allowed.has(key));
    const effective = sanitized.length > 0 ? sanitized : DEFAULT_TABLE_COLUMNS;
    setColumnsState(effective);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(effective));
  }, []);

  const resetColumns = useCallback(() => {
    setColumns(DEFAULT_TABLE_COLUMNS);
  }, [setColumns]);

  const toggleColumn = useCallback(
    (key: TableColumnKey) => {
      setColumns(
        columns.includes(key)
          ? columns.filter((column) => column !== key)
          : [...columns, key],
      );
    },
    [columns, setColumns],
  );

  const columnSet = useMemo(() => new Set(columns), [columns]);

  return { columns, columnSet, setColumns, resetColumns, toggleColumn };
}
