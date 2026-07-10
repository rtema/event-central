import { Trans, useLingui } from "@lingui/react/macro";
import { Anchor, Paper, Stack, Text, Title } from "@mantine/core";
import { IconCash } from "@tabler/icons-react";
import type { ColumnDef } from "@tanstack/react-table";
import { useMemo, useState } from "react";
import { Link } from "react-router";
import { usePayments } from "../../api/hooks";
import type { Payment } from "../../api/types";
import { DataTable } from "../ui/DataTable";
import { Pager } from "../ui/Pager";
import { QueryState } from "../ui/QueryState";
import { PaymentTypeBadge } from "../ui/StatusBadge";
import { formatDateTime } from "../utils/datetime";
import { formatMoney } from "../utils/format";

const LIMIT = 100;

export function PaymentsList() {
  const { t, i18n } = useLingui();
  const [offset, setOffset] = useState(0);
  const { data, error, isLoading } = usePayments({
    limit: LIMIT,
    offset: String(offset),
  });
  const payments = data?.data ?? [];

  const columns = useMemo<ColumnDef<Payment>[]>(
    () => [
      {
        id: "type",
        header: t`Type`,
        accessorFn: (p) => p.type ?? "payment",
        cell: (info) => <PaymentTypeBadge type={info.row.original.type} />,
      },
      {
        accessorKey: "provider",
        header: t`Provider`,
        cell: (info) => <Text size="sm">{info.getValue<string>() || "—"}</Text>,
      },
      {
        accessorKey: "method",
        header: t`Method`,
        cell: (info) => <Text size="sm">{info.getValue<string>() || "—"}</Text>,
      },
      {
        id: "order",
        header: t`Order`,
        accessorFn: (p) => p.orderId ?? "",
        enableSorting: false,
        cell: (info) =>
          info.getValue<string>() ? (
            <Anchor
              component={Link}
              to={`/${i18n.locale}/orders/${info.getValue<string>()}`}
              size="sm"
              onClick={(e) => e.stopPropagation()}
            >
              <Trans>View order</Trans>
            </Anchor>
          ) : (
            <Text size="sm">—</Text>
          ),
      },
      {
        accessorKey: "createdAt",
        header: t`Recorded`,
        cell: (info) => (
          <Text size="sm">{formatDateTime(info.getValue<string>())}</Text>
        ),
      },
      {
        accessorKey: "amount",
        header: t`Amount`,
        cell: (info) => (
          <Text size="sm" fw={500}>
            {formatMoney(info.getValue<number>(), info.row.original.currency)}
          </Text>
        ),
      },
    ],
    [t],
  );

  return (
    <Stack>
      <Stack gap={2}>
        <Title order={1}>
          <Trans>Payments</Trans>
        </Title>
        <Text size="sm" c="dimmed">
          <Trans>All payments and refunds recorded across orders.</Trans>
        </Text>
      </Stack>

      <Paper withBorder radius="md" p="md">
        <QueryState
          isLoading={isLoading}
          error={error}
          isEmpty={payments.length === 0}
          empty={
            <Stack align="center" gap="xs" c="dimmed">
              <IconCash size={32} />
              <Text size="sm">
                <Trans>No payments yet.</Trans>
              </Text>
            </Stack>
          }
        >
          <Pager
            limit={LIMIT}
            offset={offset}
            count={payments.length}
            pagination={data?.pagination}
            onChange={setOffset}
          />
          <DataTable
            data={payments}
            columns={columns}
            initialSorting={[{ id: "createdAt", desc: true }]}
            minWidth={720}
          />
        </QueryState>
      </Paper>
    </Stack>
  );
}
