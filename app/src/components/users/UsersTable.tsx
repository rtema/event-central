import { useMemo, useState } from "react";
import {
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getSortedRowModel,
  useReactTable,
  type ColumnDef,
  type SortingState,
} from "@tanstack/react-table";
import {
  Badge,
  Group,
  Table,
  Text,
  TextInput,
  UnstyledButton,
} from "@mantine/core";
import {
  IconArrowsSort,
  IconChevronRight,
  IconSearch,
  IconSortAscending,
  IconSortDescending,
} from "@tabler/icons-react";
import { Trans, useLingui } from "@lingui/react/macro";
import { useNavigate } from "react-router";
import type { User } from "../../api/types";
import { formatDate } from "../utils/datetime";

function displayName(u: User): string {
  return [u.title, u.firstName, u.lastName].filter(Boolean).join(" ");
}

export function UsersTable({ users }: { users: User[] }) {
  const { t } = useLingui();
  const navigate = useNavigate();
  const [sorting, setSorting] = useState<SortingState>([
    { id: "createdAt", desc: true },
  ]);
  const [globalFilter, setGlobalFilter] = useState("");

  const columns = useMemo<ColumnDef<User>[]>(
    () => [
      {
        id: "name",
        header: t`Name`,
        accessorFn: (u) => displayName(u),
        cell: (info) => (
          <Text fw={500} size="sm">
            {info.getValue<string>() || "—"}
          </Text>
        ),
      },
      {
        accessorKey: "email",
        header: t`Email`,
        cell: (info) => (
          <Text size="sm" c="dimmed">
            {info.getValue<string>()}
          </Text>
        ),
      },
      {
        accessorKey: "createdAt",
        header: t`Created`,
        cell: (info) => (
          <Text size="sm">{formatDate(info.getValue<string>())}</Text>
        ),
      },
      {
        id: "status",
        header: t`Status`,
        accessorFn: (u) => (u.deletedAt ? "deleted" : "active"),
        enableSorting: false,
        cell: (info) =>
          info.getValue<string>() === "deleted" ? (
            <Badge color="gray" variant="light">
              <Trans>Deleted</Trans>
            </Badge>
          ) : (
            <Badge color="pine" variant="light">
              <Trans>Active</Trans>
            </Badge>
          ),
      },
      {
        id: "go",
        header: "",
        enableSorting: false,
        cell: () => (
          <Group justify="flex-end">
            <IconChevronRight size={16} opacity={0.5} />
          </Group>
        ),
      },
    ],
    [t],
  );

  const table = useReactTable({
    data: users,
    columns,
    state: { sorting, globalFilter },
    onSortingChange: setSorting,
    onGlobalFilterChange: setGlobalFilter,
    globalFilterFn: "includesString",
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
  });

  return (
    <>
      <TextInput
        mb="md"
        maw={320}
        leftSection={<IconSearch size={16} />}
        placeholder={t`Search name or email`}
        value={globalFilter}
        onChange={(e) => setGlobalFilter(e.currentTarget.value)}
      />
      <Table.ScrollContainer minWidth={640}>
        <Table highlightOnHover verticalSpacing="sm" stickyHeader>
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
                          style={{ display: "inline-flex", alignItems: "center", gap: 4 }}
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
            {table.getRowModel().rows.map((row) => (
              <Table.Tr
                key={row.id}
                onClick={() => navigate(`/users/${row.original.id}`)}
                style={{ cursor: "pointer" }}
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

      {table.getRowModel().rows.length === 0 && (
        <Text c="dimmed" ta="center" py="xl" size="sm">
          <Trans>No users match your search.</Trans>
        </Text>
      )}
    </>
  );
}
