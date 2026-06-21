// Human: Paginated earthquake data table using TanStack Table.
// Agent: READS rows/total/offset/limit props; CALLS onPageChange for pagination; no HTTP.
import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  useReactTable,
} from "@tanstack/react-table";
import { useTranslation } from "react-i18next";
import type { Earthquake } from "../types";

// Human: Column helper typed to Earthquake rows.
// Agent: USED by column definitions below.
const columnHelper = createColumnHelper<Earthquake>();

interface Props {
  rows: Earthquake[];
  total: number;
  offset: number;
  limit: number;
  onPageChange: (offset: number) => void;
}

// Human: Renders sortable-style table with localized columns and page controls.
// Agent: RETURNS table JSX; READS i18n.language for date formatting; WRITES none.
export function EarthquakeTable({ rows, total, offset, limit, onPageChange }: Props) {
  const { t, i18n } = useTranslation();

  // Human: Column definitions — time, location, magnitude, depth, coordinates.
  // Agent: READS row accessors; formats dates and numbers for display.
  const columns = [
    columnHelper.accessor("time_utc", {
      header: t("time"),
      cell: (info) => new Date(info.getValue()).toLocaleString(i18n.language),
    }),
    columnHelper.accessor("location_name", {
      header: t("location"),
      cell: (info) => info.getValue() ?? "—",
    }),
    columnHelper.accessor("magnitude", {
      header: t("magnitude"),
      cell: (info) => info.getValue()?.toFixed(1) ?? "—",
    }),
    columnHelper.accessor("depth_km", {
      header: t("depth"),
      cell: (info) => info.getValue().toFixed(1),
    }),
    columnHelper.display({
      id: "coords",
      header: t("coordinates"),
      cell: ({ row }) => `${row.original.latitude.toFixed(3)}, ${row.original.longitude.toFixed(3)}`,
    }),
  ];

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
      {/* Human: Table header and body from TanStack row model. */}
      {/* Agent: READS table.getHeaderGroups and getRowModel; DISPLAYS noData when empty. */}
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
            table.getRowModel().rows.map((row) => (
              <tr key={row.id}>
                {row.getVisibleCells().map((cell) => (
                  <td key={cell.id}>{flexRender(cell.column.columnDef.cell, cell.getContext())}</td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
      {/* Human: Previous/next page buttons with current page indicator. */}
      {/* Agent: CALLS onPageChange(offset ± limit); disabled at bounds. */}
      <div className="pagination">
        <button type="button" disabled={offset <= 0} onClick={() => onPageChange(Math.max(0, offset - limit))}>
          ←
        </button>
        <span>{page} / {pageCount} ({total})</span>
        <button type="button" disabled={offset + limit >= total} onClick={() => onPageChange(offset + limit)}>
          →
        </button>
      </div>
    </div>
  );
}
