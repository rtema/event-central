import { Trans, useLingui } from "@lingui/react/macro";
import { Paper, Stack, Text, Title } from "@mantine/core";
import { IconShoppingCart } from "@tabler/icons-react";
import type { ColumnDef } from "@tanstack/react-table";
import { useMemo, useState } from "react";
import { useNavigate } from "react-router";
import type { Order } from "../../api/types";
import { useOrders } from "../invoices/invoicingHooks";
import { DataTable } from "../ui/DataTable";
import { Pager } from "../ui/Pager";
import { QueryState } from "../ui/QueryState";
import { OrderStatusBadge } from "../ui/StatusBadge";
import { formatDate } from "../utils/datetime";

const LIMIT = 100;

export function OrdersList() {
  const { t, i18n } = useLingui();
  const navigate = useNavigate();
  const [offset, setOffset] = useState(0);
  const { data, error, isLoading } = useOrders({
    limit: LIMIT,
    offset: String(offset),
  });
  const orders = data?.data ?? [];

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
        accessorKey: "eventId",
        header: t`Event`,
        cell: (info) => <Text size="sm">{info.getValue<string>() || "—"}</Text>,
      },
      {
        id: "recipient",
        header: t`Recipient`,
        accessorFn: (o) => o.recipient?.contactName ?? "",
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
      <Stack gap={2}>
        <Title order={1}>
          <Trans>Orders</Trans>
        </Title>
        <Text size="sm" c="dimmed">
          <Trans>Track order status, payments and invoices.</Trans>
        </Text>
      </Stack>

      <Paper withBorder radius="md" p="md">
        <QueryState
          isLoading={isLoading}
          error={error}
          isEmpty={orders.length === 0}
          empty={
            <Stack align="center" gap="xs" c="dimmed">
              <IconShoppingCart size={32} />
              <Text size="sm">
                <Trans>No orders yet.</Trans>
              </Text>
            </Stack>
          }
        >
          <DataTable
            data={orders}
            columns={columns}
            searchable
            searchPlaceholder={t`Search orders`}
            onRowClick={(row) => navigate(`/${i18n.locale}/orders/${row.id}`)}
            minWidth={720}
          />
          <Pager
            limit={LIMIT}
            offset={offset}
            count={orders.length}
            pagination={data?.pagination}
            onChange={setOffset}
          />
        </QueryState>
      </Paper>
    </Stack>
  );
}
