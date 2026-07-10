import { Trans, useLingui } from "@lingui/react/macro";
import { Button, Group, Paper, Stack, Table, Text, TextInput, Title } from "@mantine/core";
import { useDebouncedValue } from "@mantine/hooks";
import {
  IconCalendarEvent,
  IconChevronRight,
  IconSearch,
  IconX,
} from "@tabler/icons-react";
import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router";
import { useEventSearch } from "../../api/hooks";
import type { EventSearchParams } from "../../api/types";
import { Pager } from "../ui/Pager";
import { QueryState } from "../ui/QueryState";
import { formatDate } from "../utils/datetime";
import { localizedLabel } from "../utils/format";
import { saveListQuery } from "../utils/listQuery";
import { hasActiveFilters, paramsFromUrl, paramsToUrl } from "./eventSearchParams";

const LIMIT = 100;

export function EventsList() {
  const { t, i18n } = useLingui();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  // The address bar is the source of truth for all filters.
  const params = useMemo(() => paramsFromUrl(searchParams), [searchParams]);

  // Mirror the canonical query into localStorage so the "Back to events" link
  // on detail pages can return to this exact filtered view.
  useEffect(() => {
    saveListQuery("events", paramsToUrl(params));
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
  const { data, error, isLoading } = useEventSearch({ ...params, limit: LIMIT });
  const events = data?.data ?? [];

  // Any change resets pagination unless an explicit offset is supplied.
  function commit(next: EventSearchParams) {
    setSearchParams(paramsToUrl(next), { replace: true });
  }

  const activeFilters = hasActiveFilters(params);

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
        <Group align="flex-end" wrap="wrap" gap="sm">
          <TextInput
            label={t`Search`}
            placeholder={t`Event name or id…`}
            leftSection={<IconSearch size={16} />}
            value={qInput}
            onChange={(e) => setQInput(e.currentTarget.value)}
            style={{ flex: "1 1 280px" }}
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
          isEmpty={events.length === 0}
          empty={
            <Stack align="center" gap="xs" c="dimmed">
              <IconCalendarEvent size={32} />
              <Text size="sm">
                {activeFilters ? (
                  <Trans>No events match these filters.</Trans>
                ) : (
                  <Trans>No events yet.</Trans>
                )}
              </Text>
            </Stack>
          }
        >
          <Pager
            limit={LIMIT}
            offset={offset}
            count={events.length}
            pagination={data?.pagination}
            onChange={(next) =>
              commit({ ...params, offset: next ? String(next) : undefined })
            }
          />
          <Table.ScrollContainer minWidth={640}>
            <Table verticalSpacing="sm" highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>
                    <Trans>Event</Trans>
                  </Table.Th>
                  <Table.Th>
                    <Trans>Starts</Trans>
                  </Table.Th>
                  <Table.Th>
                    <Trans>Ends</Trans>
                  </Table.Th>
                  <Table.Th />
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {events.map((event) => (
                  <Table.Tr
                    key={event.id}
                    style={{ cursor: "pointer" }}
                    onClick={() =>
                      navigate(`/${i18n.locale}/events/${event.id}`)
                    }
                  >
                    <Table.Td>
                      <Stack gap={0}>
                        <Text size="sm" fw={500}>
                          {localizedLabel(event.label)}
                        </Text>
                        <Text size="xs" c="dimmed">
                          {event.id}
                        </Text>
                      </Stack>
                    </Table.Td>
                    <Table.Td>
                      <Text size="sm">{formatDate(event.startDt)}</Text>
                    </Table.Td>
                    <Table.Td>
                      <Text size="sm">{formatDate(event.endDt)}</Text>
                    </Table.Td>
                    <Table.Td>
                      <Group justify="flex-end">
                        <IconChevronRight size={16} opacity={0.5} />
                      </Group>
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
