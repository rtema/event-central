import { Trans, useLingui } from "@lingui/react/macro";
import {
  Button,
  Group,
  MultiSelect,
  Paper,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { useDebouncedValue } from "@mantine/hooks";
import { IconSearch, IconShoppingCart, IconX } from "@tabler/icons-react";
import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router";
import { useEvents, useOrderSearch } from "../../api/hooks";
import type { OrderSearchParams, OrderStatus } from "../../api/types";
import { Pager } from "../ui/Pager";
import { QueryState } from "../ui/QueryState";
import { OrderStatusBadge } from "../ui/StatusBadge";
import { formatDate } from "../utils/datetime";
import { localizedLabel } from "../utils/format";
import { saveListQuery } from "../utils/listQuery";
import { hasActiveFilters, paramsFromUrl, paramsToUrl } from "./orderSearchParams";

const LIMIT = 100;

export function OrdersList() {
  const { t, i18n } = useLingui();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  // The address bar is the source of truth for all filters.
  const params = useMemo(() => paramsFromUrl(searchParams), [searchParams]);

  // Mirror the canonical query into localStorage so the "Back to orders" link
  // on detail pages can return to this exact filtered view.
  useEffect(() => {
    saveListQuery("orders", paramsToUrl(params));
  }, [params]);

  // Free-text box is debounced before it hits the URL.
  const [qInput, setQInput] = useState(params.q ?? "");
  const [debouncedQ] = useDebouncedValue(qInput, 350);
  useEffect(() => {
    setQInput(params.q ?? "");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params.q]);
  useEffect(() => {
    if ((debouncedQ || "") === (params.q ?? "")) return;
    commit({ ...params, q: debouncedQ || undefined, offset: undefined });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedQ]);

  const offset = Number(params.offset ?? "0");
  const { data, error, isLoading } = useOrderSearch({ ...params, limit: LIMIT });
  const orders = data?.data ?? [];

  // Populate the event filter from the events endpoint (labelled, id as value).
  const { data: eventsData } = useEvents({ limit: LIMIT });
  const eventOptions = useMemo(
    () =>
      (eventsData?.data ?? [])
        .filter((e): e is typeof e & { id: string } => Boolean(e.id))
        .map((e) => {
          const label = localizedLabel(e.label);
          return { value: e.id, label: label !== "—" ? label : e.id };
        }),
    [eventsData],
  );

  // Any change resets pagination unless an explicit offset is supplied.
  function commit(next: OrderSearchParams) {
    setSearchParams(paramsToUrl(next), { replace: true });
  }

  const activeFilters = hasActiveFilters(params);

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
        <Group align="flex-end" wrap="wrap" gap="sm">
          <TextInput
            label={t`Search`}
            placeholder={t`Order id or recipient…`}
            leftSection={<IconSearch size={16} />}
            value={qInput}
            onChange={(e) => setQInput(e.currentTarget.value)}
            style={{ flex: "1 1 240px" }}
          />
          <MultiSelect
            label={t`Status`}
            placeholder={params.status?.length ? undefined : t`Any`}
            data={[
              { value: "open", label: t`Open` },
              { value: "paid", label: t`Paid` },
              { value: "cancelled", label: t`Cancelled` },
            ]}
            value={params.status ?? []}
            onChange={(v) =>
              commit({
                ...params,
                status: v as OrderStatus[],
                offset: undefined,
              })
            }
            clearable
            style={{ flex: "1 1 200px" }}
          />
          <MultiSelect
            label={t`Events`}
            placeholder={params.event?.length ? undefined : t`Any`}
            data={eventOptions}
            value={params.event ?? []}
            onChange={(v) =>
              commit({
                ...params,
                event: v.length ? v : undefined,
                offset: undefined,
              })
            }
            searchable
            clearable
            nothingFoundMessage={t`No events`}
            style={{ flex: "1 1 240px" }}
          />
          {activeFilters && (
            <Button
              variant="subtle"
              color="gray"
              leftSection={<IconX size={14} />}
              onClick={() => {
                setQInput("");
                commit({});
              }}
            >
              <Trans>Clear filters</Trans>
            </Button>
          )}
        </Group>
      </Paper>

      <Paper withBorder radius="md" p="md">
        <QueryState
          isLoading={isLoading}
          error={error}
          isEmpty={orders.length === 0}
          empty={
            <Stack align="center" gap="xs" c="dimmed">
              <IconShoppingCart size={32} />
              <Text size="sm">
                {activeFilters ? (
                  <Trans>No orders match these filters.</Trans>
                ) : (
                  <Trans>No orders yet.</Trans>
                )}
              </Text>
            </Stack>
          }
        >
          <Pager
            limit={LIMIT}
            offset={offset}
            count={orders.length}
            pagination={data?.pagination}
            onChange={(next) =>
              commit({ ...params, offset: next ? String(next) : undefined })
            }
          />
          <Table.ScrollContainer minWidth={720}>
            <Table verticalSpacing="sm" highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>
                    <Trans>Order</Trans>
                  </Table.Th>
                  <Table.Th>
                    <Trans>Event</Trans>
                  </Table.Th>
                  <Table.Th>
                    <Trans>Recipient</Trans>
                  </Table.Th>
                  <Table.Th>
                    <Trans>Status</Trans>
                  </Table.Th>
                  <Table.Th>
                    <Trans>Created</Trans>
                  </Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {orders.map((order) => {
                  const recipient = [
                    order.recipient?.contactFirstname,
                    order.recipient?.contactLastname,
                  ]
                    .filter(Boolean)
                    .join(" ");
                  return (
                    <Table.Tr
                      key={order.id}
                      style={{ cursor: "pointer" }}
                      onClick={() =>
                        navigate(`/${i18n.locale}/orders/${order.id}`)
                      }
                    >
                      <Table.Td>
                        <Text size="sm" fw={500}>
                          {order.externalId || order.id}
                        </Text>
                      </Table.Td>
                      <Table.Td>
                        <Text size="sm">{order.eventId || "—"}</Text>
                      </Table.Td>
                      <Table.Td>
                        <Text size="sm">{recipient || "—"}</Text>
                      </Table.Td>
                      <Table.Td>
                        <OrderStatusBadge status={order.status} />
                      </Table.Td>
                      <Table.Td>
                        <Text size="sm">{formatDate(order.createdAt)}</Text>
                      </Table.Td>
                    </Table.Tr>
                  );
                })}
              </Table.Tbody>
            </Table>
          </Table.ScrollContainer>
        </QueryState>
      </Paper>
    </Stack>
  );
}