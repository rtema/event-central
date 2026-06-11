import { useState } from "react";
import {
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getSortedRowModel,
  useReactTable,
  type ColumnDef,
  type SortingState,
} from "@tanstack/react-table";
import { Table, Text, TextInput, UnstyledButton } from "@mantine/core";
import {
  IconArrowsSort,
  IconSearch,
  IconSortAscending,
  IconSortDescending,
} from "@tabler/icons-react";
import { Trans, useLingui } from "@lingui/react/macro";

interface DataTableProps<T> {
  data: T[];
  columns: ColumnDef<T>[];
  /** Initial sort state. */
  initialSorting?: SortingState;
  /** Show a global search box. */
  searchable?: boolean;
  searchPlaceholder?: string;
  /** Invoked when a row is clicked (makes rows look/behave clickable). */
  onRowClick?: (row: T) => void;
  minWidth?: number;
  emptyMessage?: React.ReactNode;
}

/**
 * Thin, reusable wrapper around TanStack Table rendered with Mantine. Each list
 * screen supplies its own columns; sorting, filtering and row interaction are
 * handled here so the screens stay declarative.
 */
export function DataTable<T>({
  data,
  columns,
  initialSorting = [],
  searchable = false,
  searchPlaceholder,
  onRowClick,
  minWidth = 640,
  emptyMessage,
}: DataTableProps<T>) {
  const { t } = useLingui();
  const [sorting, setSorting] = useState<SortingState>(initialSorting);
  const [globalFilter, setGlobalFilter] = useState("");

  const table = useReactTable({
    data,
    columns,
    state: { sorting, globalFilter },
    onSortingChange: setSorting,
    onGlobalFilterChange: setGlobalFilter,
    globalFilterFn: "includesString",
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
  });

  const rows = table.getRowModel().rows;

  return (
    <>
      {searchable && (
        <TextInput
          mb="md"
          maw={320}
          leftSection={<IconSearch size={16} />}
          placeholder={searchPlaceholder ?? t`Search`}
          value={globalFilter}
          onChange={(e) => setGlobalFilter(e.currentTarget.value)}
        />
      )}
      <Table.ScrollContainer minWidth={minWidth}>
        <Table highlightOnHover={!!onRowClick} verticalSpacing="sm" stickyHeader>
          <Table.Thead>
            {table.getHeaderGroups().map((hg) => (
              <Table.Tr key={hg.id}>
                {hg.headers.map((header) => {
                  const canSort = header.column.getCanSort();
                  const sorted = header.column.getIsSorted();
                  return (
                    <Table.Th key={header.id}>
                      {canSort ? (
                        <UnstyledButton
                          onClick={header.column.getToggleSortingHandler()}
                          style={{
                            display: "inline-flex",
                            alignItems: "center",
                            gap: 4,
                          }}
                        >
                          <Text size="xs" fw={600} tt="uppercase" c="dimmed">
                            {flexRender(
                              header.column.columnDef.header,
                              header.getContext(),
                            )}
                          </Text>
                          {sorted === "asc" ? (
                            <IconSortAscending size={14} />
                          ) : sorted === "desc" ? (
                            <IconSortDescending size={14} />
                          ) : (
                            <IconArrowsSort size={14} opacity={0.4} />
                          )}
                        </UnstyledButton>
                      ) : (
                        <Text size="xs" fw={600} tt="uppercase" c="dimmed">
                          {flexRender(
                            header.column.columnDef.header,
                            header.getContext(),
                          )}
                        </Text>
                      )}
                    </Table.Th>
                  );
                })}
              </Table.Tr>
            ))}
          </Table.Thead>
          <Table.Tbody>
            {rows.map((row) => (
              <Table.Tr
                key={row.id}
                onClick={onRowClick ? () => onRowClick(row.original) : undefined}
                style={onRowClick ? { cursor: "pointer" } : undefined}
              >
                {row.getVisibleCells().map((cell) => (
                  <Table.Td key={cell.id}>
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </Table.Td>
                ))}
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </Table.ScrollContainer>

      {rows.length === 0 && (
        <Text c="dimmed" ta="center" py="xl" size="sm">
          {emptyMessage ?? <Trans>Nothing to show.</Trans>}
        </Text>
      )}
    </>
  );
}
