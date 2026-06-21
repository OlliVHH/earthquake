// Human: Paginated earthquake table with configurable columns and row-to-map selection.
// Agent: READS rows/total/offset/limit; CALLS onPageChange, onRowSelect; WRITES column prefs via useTableColumns.
import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  useReactTable,
} from "@tanstack/react-table";
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  ALL_TABLE_COLUMNS,
  type TableColumnKey,
  useTableColumns,
} from "../hooks/useTableColumns";
import type { Earthquake } from "../types";

// Human: Column helper typed to Earthquake rows.
// Agent: USED by dynamic column definitions below.
const columnHelper = createColumnHelper<Earthquake>();

interface Props {
  rows: Earthquake[];
  total: number;
  offset: number;
  limit: number;
  selectedEventId?: string | null;
  onPageChange: (offset: number) => void;
  onRowSelect: (earthquake: Earthquake) => void;
}

// Human: Map column keys to i18n label keys for headers and picker.
// Agent: READS TableColumnKey; RETURNS translation key string.
function columnLabelKey(key: TableColumnKey): string {
  if (key === "time_utc") {
    return "time";
  }
  if (key === "depth_km") {
    return "depth";
  }
  if (key === "coordinates") {
    return "coordinates";
  }
  return key;
}

// Human: Format one cell value for a given column key and current locale.
// Agent: READS Earthquake row + column key; RETURNS display string for table cell.
function formatCellValue(
  row: Earthquake,
  key: TableColumnKey,
  language: string,
): string {
  switch (key) {
    case "event_id":
      return row.event_id;
    case "time_utc":
      return new Date(row.time_utc).toLocaleString(language);
    case "location_name":
      return row.location_name ?? "—";
    case "magnitude":
      return row.magnitude?.toFixed(1) ?? "—";
    case "mag_type":
      return row.mag_type ?? "—";
    case "depth_km":
      return row.depth_km.toFixed(1);
    case "latitude":
      return row.latitude.toFixed(3);
    case "longitude":
      return row.longitude.toFixed(3);
    case "coordinates":
      return `${row.latitude.toFixed(3)}, ${row.longitude.toFixed(3)}`;
    case "author":
      return row.author ?? "—";
    case "catalog":
      return row.catalog ?? "—";
    case "contributor":
      return row.contributor ?? "—";
    case "updated_at":
      return row.updated_at ? new Date(row.updated_at).toLocaleString(language) : "—";
    case "fetched_at":
      return new Date(row.fetched_at).toLocaleString(language);
    default:
      return "—";
  }
}

// Human: Renders paginated table with column picker and clickable rows for map focus.
// Agent: RETURNS table JSX; READS i18n + localStorage columns; CALLS onRowSelect on row click.
export function EarthquakeTable({
  rows,
  total,
  offset,
  limit,
  selectedEventId,
  onPageChange,
  onRowSelect,
}: Props) {
  const { t, i18n } = useTranslation();
  const { columns: visibleColumns, columnSet, toggleColumn, resetColumns } = useTableColumns();
  const [pickerOpen, setPickerOpen] = useState(false);

  // Human: Build TanStack columns from user-selected visible column keys.
  // Agent: READS visibleColumns; RETURNS column defs with localized headers and formatters.
  const columns = useMemo(
    () =>
      visibleColumns.map((key) =>
        columnHelper.display({
          id: key,
          header: t(columnLabelKey(key)),
          cell: ({ row }) => formatCellValue(row.original, key, i18n.language),
        }),
      ),
    [visibleColumns, t, i18n.language],
  );

  const table = useReactTable({
    data: rows,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  // Human: 1-based page index and total page count from offset/limit/total.
  // Agent: READS offset, limit, total; used for pagination label and disabled states.
  const page = Math.floor(offset / limit) + 1;
  const pageCount = Math.max(1, Math.ceil(total / limit));

  return (
    <div className="table-wrap">
      {/* Human: Toolbar — open column picker and reset to default columns. */}
      {/* Agent: TOGGLES pickerOpen; CALLS resetColumns to restore DEFAULT_TABLE_COLUMNS. */}
      <div className="table-toolbar">
        <button type="button" className="secondary" onClick={() => setPickerOpen((open) => !open)}>
          {t("columnPicker")}
        </button>
        <button type="button" className="secondary" onClick={resetColumns}>
          {t("columnReset")}
        </button>
      </div>

      {pickerOpen ? (
        <div className="column-picker" role="group" aria-label={t("columnPicker")}>
          <p className="column-picker-hint">{t("columnPickerHint")}</p>
          <div className="column-picker-grid">
            {ALL_TABLE_COLUMNS.map((key) => (
              <label key={key} className="column-picker-item">
                <input
                  type="checkbox"
                  checked={columnSet.has(key)}
                  onChange={() => toggleColumn(key)}
                />
                <span>{t(columnLabelKey(key))}</span>
              </label>
            ))}
          </div>
        </div>
      ) : null}

      {/* Human: Table header and body from TanStack row model. */}
      {/* Agent: READS table.getHeaderGroups and getRowModel; row click CALLS onRowSelect. */}
      <table>
        <thead>
          {table.getHeaderGroups().map((hg) => (
            <tr key={hg.id}>
              {hg.headers.map((header) => (
                <th key={header.id}>
                  {flexRender(header.column.columnDef.header, header.getContext())}
                </th>
              ))}
            </tr>
          ))}
        </thead>
        <tbody>
          {rows.length === 0 ? (
            <tr>
              <td colSpan={columns.length}>{t("noData")}</td>
            </tr>
          ) : (
            table.getRowModel().rows.map((row) => {
              const isSelected = row.original.event_id === selectedEventId;
              return (
                <tr
                  key={row.id}
                  className={isSelected ? "table-row-selected" : "table-row-clickable"}
                  onClick={() => onRowSelect(row.original)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      onRowSelect(row.original);
                    }
                  }}
                  tabIndex={0}
                  role="button"
                  aria-label={t("openOnMap")}
                >
                  {row.getVisibleCells().map((cell) => (
                    <td key={cell.id}>{flexRender(cell.column.columnDef.cell, cell.getContext())}</td>
                  ))}
                </tr>
              );
            })
          )}
        </tbody>
      </table>
      {/* Human: Previous/next page buttons with current page indicator. */}
      {/* Agent: CALLS onPageChange(offset ± limit); disabled at bounds. */}
      <div className="pagination">
        <button type="button" disabled={offset <= 0} onClick={() => onPageChange(Math.max(0, offset - limit))}>
          ←
        </button>
        <span>
          {page} / {pageCount} ({total})
        </span>
        <button type="button" disabled={offset + limit >= total} onClick={() => onPageChange(offset + limit)}>
          →
        </button>
      </div>
    </div>
  );
}
