import { Trans, useLingui } from "@lingui/react/macro";
import { Anchor, Group, Paper, Stack, Text, Title } from "@mantine/core";
import { IconArrowLeft } from "@tabler/icons-react";
import type { ColumnDef } from "@tanstack/react-table";
import { useMemo } from "react";
import { Link, useNavigate, useParams } from "react-router";
import { listLinkWithFilters } from "../utils/listQuery";
import type { Order } from "../../api/types";
import { useEvent, useEventOrders } from "../../api/hooks";
import { DataTable } from "../ui/DataTable";
import { FieldGrid } from "../ui/FieldGrid";
import { QueryState } from "../ui/QueryState";
import { OrderStatusBadge } from "../ui/StatusBadge";
import { formatDate, formatDateTime } from "../utils/datetime";
import { localizedLabel } from "../utils/format";

export function EventDetail() {
  const { t, i18n } = useLingui();
  const navigate = useNavigate();
  const { eventId = "" } = useParams();
  const { data: event, error, isLoading } = useEvent(eventId);
  const { data: ordersData } = useEventOrders(eventId, { limit: 100 });
  const orders = ordersData?.data ?? [];

  const columns = useMemo<ColumnDef<Order>[]>(
    () => [
      {
        accessorKey: "externalId",
        header: t`Order`,
        cell: (info) => (
          <Text fw={500} size="sm">
            {info.getValue<string>() || info.row.original.id}
          </Text>
        ),
      },
      {
        id: "recipient",
        header: t`Recipient`,
        accessorFn: (o) => `${o.recipient?.contactFirstname} ${o.recipient?.contactLastname}`,
        cell: (info) => <Text size="sm">{info.getValue<string>() || "—"}</Text>,
      },
      {
        id: "status",
        header: t`Status`,
        accessorFn: (o) => o.status ?? "open",
        cell: (info) => <OrderStatusBadge status={info.row.original.status} />,
      },
      {
        accessorKey: "createdAt",
        header: t`Created`,
        cell: (info) => (
          <Text size="sm">{formatDate(info.getValue<string>())}</Text>
        ),
      },
    ],
    [t],
  );

  return (
    <Stack>
      <Anchor component={Link} to={listLinkWithFilters(`/${i18n.locale}/events`, "events")} size="sm">
        <Group gap={4}>
          <IconArrowLeft size={14} />
          <Trans>Back to events</Trans>
        </Group>
      </Anchor>

      <QueryState isLoading={isLoading} error={error}>
        {event && (
          <>
            <Paper withBorder p="lg" radius="md">
              <Title order={2}>{localizedLabel(event.label)}</Title>
              <Text size="sm" c="dimmed" mb="md">
                {event.id}
              </Text>
              <FieldGrid
                cols={{ base: 1, sm: 3 }}
                fields={[
                  { label: t`Starts`, value: formatDateTime(event.startDt) },
                  { label: t`Ends`, value: formatDateTime(event.endDt) },
                  { label: t`Created`, value: formatDateTime(event.createdAt) },
                ]}
              />
            </Paper>

            <Paper withBorder p="lg" radius="md">
              <Title order={4} mb="md">
                <Trans>Orders</Trans>
              </Title>
              <DataTable
                data={orders}
                columns={columns}
                onRowClick={(row) => navigate(`/${i18n.locale}/orders/${row.id}`)}
                emptyMessage={<Trans>No orders for this event.</Trans>}
              />
            </Paper>
          </>
        )}
      </QueryState>
    </Stack>
  );
}
