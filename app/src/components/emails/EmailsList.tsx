import { Trans, useLingui } from "@lingui/react/macro";
import {
  Button,
  Group,
  MultiSelect,
  Paper,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { useDebouncedValue } from "@mantine/hooks";
import { IconMailbox, IconSearch, IconX } from "@tabler/icons-react";
import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router";
import {
  useEmailSearch,
  useEmailSenders,
  useEmailTemplates,
} from "../../api/hooks";
import type { EmailSearchParams, EmailStatus, Locale } from "../../api/types";
import { Pager } from "../ui/Pager";
import { QueryState } from "../ui/QueryState";
import { formatDateTime } from "../utils/datetime";
import { localizedLabel } from "../utils/format";
import { saveListQuery } from "../utils/listQuery";
import { EmailStatusBadge } from "./EmailStatusBadge";
import { hasActiveFilters, paramsFromUrl, paramsToUrl } from "./emailSearchParams";

const LIMIT = 100;

export function EmailsList() {
  const { t, i18n } = useLingui();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const params = useMemo(() => paramsFromUrl(searchParams), [searchParams]);

  useEffect(() => {
    saveListQuery("emails", paramsToUrl(params));
  }, [params]);

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
  const { data, error, isLoading } = useEmailSearch({ ...params, limit: LIMIT });
  const emails = data?.data ?? [];

  // Look up templates and senders so filters and rows show names, not UUIDs.
  const { data: templatesData } = useEmailTemplates({ limit: LIMIT });
  const { data: sendersData } = useEmailSenders({ limit: LIMIT });

  const senderName = useMemo(() => {
    const map = new Map<string, string>();
    for (const s of sendersData?.data ?? [])
      map.set(s.id, s.fromName || s.fromEmail);
    return map;
  }, [sendersData]);

  const templateOptions = useMemo(
    () =>
      (templatesData?.data ?? []).map((tpl) => ({
        value: tpl.id,
        label: localizedLabel(tpl.label),
      })),
    [templatesData],
  );
  const senderOptions = useMemo(
    () =>
      (sendersData?.data ?? []).map((s) => ({
        value: s.id,
        label: s.fromName ? `${s.fromName} · ${s.fromEmail}` : s.fromEmail,
      })),
    [sendersData],
  );

  function commit(next: EmailSearchParams) {
    setSearchParams(paramsToUrl(next), { replace: true });
  }

  const activeFilters = hasActiveFilters(params);
  const attachmentValue =
    params.hasAttachments?.length === 1
      ? params.hasAttachments[0]
        ? "true"
        : "false"
      : "";

  return (
    <Stack>
      <Stack gap={2}>
        <Title order={1}>
          <Trans>Emails</Trans>
        </Title>
        <Text size="sm" c="dimmed">
          <Trans>
            Every queued, sent, and failed email. Open one to see its rendered
            body and delivery details.
          </Trans>
        </Text>
      </Stack>

      <Paper withBorder radius="md" p="md">
        <Group align="flex-end" wrap="wrap" gap="sm">
          <TextInput
            label={t`Search`}
            placeholder={t`Recipient or subject…`}
            leftSection={<IconSearch size={16} />}
            value={qInput}
            onChange={(e) => setQInput(e.currentTarget.value)}
            style={{ flex: "1 1 240px" }}
          />
          <MultiSelect
            label={t`Status`}
            placeholder={params.status?.length ? undefined : t`Any`}
            data={[
              { value: "scheduled", label: t`Scheduled` },
              { value: "in-progress", label: t`Sending` },
              { value: "delivered", label: t`Delivered` },
              { value: "retry", label: t`Retrying` },
              { value: "failed", label: t`Failed` },
              { value: "cancelled", label: t`Cancelled` },
            ]}
            value={params.status ?? []}
            onChange={(v) =>
              commit({ ...params, status: v as EmailStatus[], offset: undefined })
            }
            clearable
            style={{ flex: "1 1 200px" }}
          />
          <MultiSelect
            label={t`Template`}
            placeholder={params.emailTemplate?.length ? undefined : t`Any`}
            data={templateOptions}
            value={params.emailTemplate ?? []}
            onChange={(v) =>
              commit({ ...params, emailTemplate: v, offset: undefined })
            }
            searchable
            clearable
            nothingFoundMessage={t`No templates`}
            style={{ flex: "1 1 220px" }}
          />
          <MultiSelect
            label={t`Sender`}
            placeholder={params.emailSender?.length ? undefined : t`Any`}
            data={senderOptions}
            value={params.emailSender ?? []}
            onChange={(v) =>
              commit({ ...params, emailSender: v, offset: undefined })
            }
            searchable
            clearable
            nothingFoundMessage={t`No senders`}
            style={{ flex: "1 1 220px" }}
          />
          <Select
            label={t`Attachments`}
            placeholder={t`Any`}
            data={[
              { value: "true", label: t`With attachments` },
              { value: "false", label: t`Without` },
            ]}
            value={attachmentValue}
            onChange={(v) =>
              commit({
                ...params,
                hasAttachments: v ? [v === "true"] : undefined,
                offset: undefined,
              })
            }
            clearable
            style={{ flex: "1 1 180px" }}
          />
          <MultiSelect
            label={t`Locale`}
            placeholder={params.locale?.length ? undefined : t`Any`}
            data={[
              { value: "de", label: t`German` },
              { value: "en", label: t`English` },
            ]}
            value={params.locale ?? []}
            onChange={(v) =>
              commit({ ...params, locale: v as Locale[], offset: undefined })
            }
            clearable
            style={{ flex: "1 1 150px" }}
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
          isEmpty={emails.length === 0}
          empty={
            <Stack align="center" gap="xs" c="dimmed">
              <IconMailbox size={32} />
              <Text size="sm">
                {activeFilters ? (
                  <Trans>No emails match these filters.</Trans>
                ) : (
                  <Trans>No emails yet.</Trans>
                )}
              </Text>
            </Stack>
          }
        >
          <Pager
            limit={LIMIT}
            offset={offset}
            count={emails.length}
            pagination={data?.pagination}
            onChange={(next) =>
              commit({ ...params, offset: next ? String(next) : undefined })
            }
          />
          <Table.ScrollContainer minWidth={860}>
            <Table verticalSpacing="sm" highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>
                    <Trans>Recipient</Trans>
                  </Table.Th>
                  <Table.Th>
                    <Trans>Subject</Trans>
                  </Table.Th>
                  <Table.Th>
                    <Trans>Status</Trans>
                  </Table.Th>
                  <Table.Th>
                    <Trans>Sender</Trans>
                  </Table.Th>
                  <Table.Th>
                    <Trans>Created</Trans>
                  </Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {emails.map((email) => (
                  <Table.Tr
                    key={email.id}
                    style={{ cursor: "pointer" }}
                    onClick={() =>
                      navigate(`/${i18n.locale}/emails/${email.id}`)
                    }
                  >
                    <Table.Td>
                      <Text size="sm" fw={500}>
                        {email.to?.[0] || "—"}
                      </Text>
                      {email.to?.length > 1 && (
                        <Text size="xs" c="dimmed">
                          <Trans>+{email.to.length - 1} more</Trans>
                        </Text>
                      )}
                    </Table.Td>
                    <Table.Td>
                      <Text size="sm" truncate maw={280}>
                        {email.subject || "—"}
                      </Text>
                    </Table.Td>
                    <Table.Td>
                      <EmailStatusBadge status={email.status} />
                    </Table.Td>
                    <Table.Td>
                      <Text size="sm">
                        {senderName.get(email.emailSenderId) ||
                          email.sender ||
                          "—"}
                      </Text>
                    </Table.Td>
                    <Table.Td>
                      <Text size="sm">{formatDateTime(email.createdAt)}</Text>
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
