import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  useReactTable,
} from "@tanstack/react-table";
import { useTranslation } from "react-i18next";
import type { Earthquake } from "../types";

const columnHelper = createColumnHelper<Earthquake>();

interface Props {
  rows: Earthquake[];
  total: number;
  offset: number;
  limit: number;
  onPageChange: (offset: number) => void;
}

/** Sortable paginated earthquake table. */
export function EarthquakeTable({ rows, total, offset, limit, onPageChange }: Props) {
  const { t, i18n } = useTranslation();

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

  const page = Math.floor(offset / limit) + 1;
  const pageCount = Math.max(1, Math.ceil(total / limit));

  return (
    <div className="table-wrap">
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
