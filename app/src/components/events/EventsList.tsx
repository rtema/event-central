import { Trans, useLingui } from "@lingui/react/macro";
import { Group, Paper, Stack, Text, Title } from "@mantine/core";
import { IconCalendarEvent, IconChevronRight } from "@tabler/icons-react";
import type { ColumnDef } from "@tanstack/react-table";
import { useMemo, useState } from "react";
import { useNavigate } from "react-router";
import type { Event } from "../../api/types";
import { useEvents } from "../invoices/invoicingHooks";
import { DataTable } from "../ui/DataTable";
import { Pager } from "../ui/Pager";
import { QueryState } from "../ui/QueryState";
import { formatDate } from "../utils/datetime";
import { localizedLabel } from "../utils/format";

const LIMIT = 100;

export function EventsList() {
  const { t, i18n } = useLingui();
  const navigate = useNavigate();
  const [offset, setOffset] = useState(0);
  const { data, error, isLoading } = useEvents({
    limit: LIMIT,
    offset: String(offset),
  });
  const events = data?.data ?? [];

  const columns = useMemo<ColumnDef<Event>[]>(
    () => [
      {
        id: "label",
        header: t`Event`,
        accessorFn: (e) => localizedLabel(e.label),
        cell: (info) => (
          <Stack gap={0}>
            <Text fw={500} size="sm">
              {info.getValue<string>()}
            </Text>
            <Text size="xs" c="dimmed">
              {info.row.original.id}
            </Text>
          </Stack>
        ),
      },
      {
        accessorKey: "startDt",
        header: t`Starts`,
        cell: (info) => (
          <Text size="sm">{formatDate(info.getValue<string>())}</Text>
        ),
      },
      {
        accessorKey: "endDt",
        header: t`Ends`,
        cell: (info) => (
          <Text size="sm">{formatDate(info.getValue<string>())}</Text>
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

  return (
    <Stack>
      <Stack gap={2}>
        <Title order={1}>
          <Trans>Events</Trans>
        </Title>
        <Text size="sm" c="dimmed">
          <Trans>Every event with invoices or orders on the platform.</Trans>
        </Text>
      </Stack>

      <Paper withBorder radius="md" p="md">
        <QueryState
          isLoading={isLoading}
          error={error}
          isEmpty={events.length === 0}
          empty={
            <Stack align="center" gap="xs" c="dimmed">
              <IconCalendarEvent size={32} />
              <Text size="sm">
                <Trans>No events yet.</Trans>
              </Text>
            </Stack>
          }
        >
          <DataTable
            data={events}
            columns={columns}
            searchable
            searchPlaceholder={t`Search events`}
            onRowClick={(row) => navigate(`/${i18n.locale}/events/${row.id}`)}
          />
          <Pager
            limit={LIMIT}
            offset={offset}
            count={events.length}
            pagination={data?.pagination}
            onChange={setOffset}
          />
        </QueryState>
      </Paper>
    </Stack>
  );
}
