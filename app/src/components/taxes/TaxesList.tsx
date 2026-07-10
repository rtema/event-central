import { Trans } from "@lingui/react/macro";
import { Badge, Paper, Stack, Table, Text, Title } from "@mantine/core";
import { IconPercentage } from "@tabler/icons-react";
import { useState } from "react";
import { useTaxes } from "../../api/hooks";
import { Pager } from "../ui/Pager";
import { QueryState } from "../ui/QueryState";
import { formatNumber, localizedLabel } from "../utils/format";

const LIMIT = 100;

export function TaxesList() {
  const [offset, setOffset] = useState(0);
  const { data, error, isLoading } = useTaxes({
    limit: LIMIT,
    offset: String(offset),
  });
  const taxes = data?.data ?? [];

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
          <Pager
            limit={LIMIT}
            offset={offset}
            count={taxes.length}
            pagination={data?.pagination}
            onChange={setOffset}
          />
          <Table.ScrollContainer minWidth={640}>
            <Table verticalSpacing="sm" highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>
                    <Trans>Label</Trans>
                  </Table.Th>
                  <Table.Th>
                    <Trans>Rate</Trans>
                  </Table.Th>
                  <Table.Th>
                    <Trans>Type</Trans>
                  </Table.Th>
                  <Table.Th>
                    <Trans>Reference ID</Trans>
                  </Table.Th>
                  <Table.Th>
                    <Trans>Exemption reason</Trans>
                  </Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {taxes.map((tax) => (
                  <Table.Tr key={tax.id}>
                    <Table.Td>
                      <Text size="sm" fw={500}>
                        {localizedLabel(tax.label)}
                      </Text>
                    </Table.Td>
                    <Table.Td>
                      <Text size="sm">
                        {tax.rate != null ? `${formatNumber(tax.rate)}%` : "—"}
                      </Text>
                    </Table.Td>
                    <Table.Td>
                      {tax.type === "exempt-verein" ? (
                        <Badge color="grape" variant="light">
                          <Trans>Exempt (Verein)</Trans>
                        </Badge>
                      ) : (
                        <Badge color="pine" variant="light">
                          <Trans>Standard</Trans>
                        </Badge>
                      )}
                    </Table.Td>
                    <Table.Td>
                      <Text size="sm" c="dimmed">
                        {tax.externalId || "—"}
                      </Text>
                    </Table.Td>
                    <Table.Td>
                      <Text size="sm">{tax.taxExemptionReason || "—"}</Text>
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Table.ScrollContainer>
        </QueryState>
      </Paper>
    </Stack>
  );
}