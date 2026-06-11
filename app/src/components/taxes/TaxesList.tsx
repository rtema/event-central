import { Trans, useLingui } from "@lingui/react/macro";
import { Badge, Paper, Stack, Text, Title } from "@mantine/core";
import { IconPercentage } from "@tabler/icons-react";
import type { ColumnDef } from "@tanstack/react-table";
import { useMemo } from "react";
import type { Tax } from "../../api/types";
import { DataTable } from "../ui/DataTable";
import { QueryState } from "../ui/QueryState";
import { useTaxes } from "../invoices/invoicingHooks";
import { formatNumber, localizedLabel } from "../utils/format";

export function TaxesList() {
  const { t } = useLingui();
  const { data, error, isLoading } = useTaxes();
  const taxes = data ?? [];

  const columns = useMemo<ColumnDef<Tax>[]>(
    () => [
      {
        id: "label",
        header: t`Label`,
        accessorFn: (tax) => localizedLabel(tax.label),
        cell: (info) => (
          <Text fw={500} size="sm">
            {info.getValue<string>()}
          </Text>
        ),
      },
      {
        accessorKey: "rate",
        header: t`Rate`,
        cell: (info) =>
          info.getValue<number>() != null ? (
            <Text size="sm">{formatNumber(info.getValue<number>())}%</Text>
          ) : (
            <Text size="sm">—</Text>
          ),
      },
      {
        id: "type",
        header: t`Type`,
        accessorFn: (tax) => tax.type ?? "standard",
        cell: (info) =>
          info.getValue<string>() === "exempt-verein" ? (
            <Badge color="grape" variant="light">
              <Trans>Exempt (Verein)</Trans>
            </Badge>
          ) : (
            <Badge color="pine" variant="light">
              <Trans>Standard</Trans>
            </Badge>
          ),
      },
      {
        accessorKey: "externalId",
        header: t`Reference ID`,
        cell: (info) => (
          <Text size="sm" c="dimmed">
            {info.getValue<string>() || "—"}
          </Text>
        ),
      },
      {
        accessorKey: "taxExemptionReason",
        header: t`Exemption reason`,
        enableSorting: false,
        cell: (info) => <Text size="sm">{info.getValue<string>() || "—"}</Text>,
      },
    ],
    [t],
  );

  return (
    <Stack>
      <Stack gap={2}>
        <Title order={1}>
          <Trans>Tax rates</Trans>
        </Title>
        <Text size="sm" c="dimmed">
          <Trans>Every tax rate referenced by an invoice line.</Trans>
        </Text>
      </Stack>

      <Paper withBorder radius="md" p="md">
        <QueryState
          isLoading={isLoading}
          error={error}
          isEmpty={taxes.length === 0}
          empty={
            <Stack align="center" gap="xs" c="dimmed">
              <IconPercentage size={32} />
              <Text size="sm">
                <Trans>No tax rates yet.</Trans>
              </Text>
            </Stack>
          }
        >
          <DataTable
            data={taxes}
            columns={columns}
            searchable
            searchPlaceholder={t`Search tax rates`}
            minWidth={640}
          />
        </QueryState>
      </Paper>
    </Stack>
  );
}
