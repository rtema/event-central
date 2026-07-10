import { Trans, useLingui } from "@lingui/react/macro";
import {
  Button,
  Group,
  Modal,
  MultiSelect,
  Paper,
  Select,
  Stack,
  Table,
  TagsInput,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { useForm } from "@mantine/form";
import { useDebouncedValue } from "@mantine/hooks";
import { notifications } from "@mantine/notifications";
import {
  IconDownload,
  IconFileInvoice,
  IconPlus,
  IconSearch,
  IconX,
} from "@tabler/icons-react";
import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router";
import { toRequestError } from "../../api/client";
import { useAccountingEntities, useInvoiceSearch } from "../../api/hooks";
import { invoicesApi } from "../../api/invoices";
import type {
  InvoiceExportFormat,
  InvoiceSearchParams,
  InvoiceType,
  Locale,
} from "../../api/types";
import { Pager } from "../ui/Pager";
import { QueryState } from "../ui/QueryState";
import { InvoiceTypeBadge } from "../ui/StatusBadge";
import { formatDate } from "../utils/datetime";
import { formatMoney } from "../utils/format";
import { saveListQuery } from "../utils/listQuery";
import {
  hasActiveFilters,
  paramsFromUrl,
  paramsToUrl,
} from "./invoiceSearchParams";

const LIMIT = 100;

function ExportModal({ opened, onClose }: { opened: boolean; onClose: () => void }) {
  const { t } = useLingui();
  const [busy, setBusy] = useState(false);
  const form = useForm<{ format: InvoiceExportFormat; accountingEntity: string }>({
    initialValues: { format: "xlsx", accountingEntity: "" },
  });

  const onSubmit = async () => {
    setBusy(true);
    try {
      const res = await invoicesApi.export({
        format: form.values.format,
        accountingEntity: form.values.accountingEntity || undefined,
      });
      if (res.url) window.open(res.url, "_blank", "noopener");
      notifications.show({
        color: "pine",
        title: t`Export ready`,
        message: t`Your download should start in a new tab.`,
      });
      onClose();
    } catch (err) {
      notifications.show({
        color: "red",
        title: t`Export failed`,
        message: toRequestError(err).message,
      });
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal opened={opened} onClose={onClose} title={t`Export invoices`} centered>
      <Stack>
        <Select
          label={t`Format`}
          data={[
            { value: "xlsx", label: t`Spreadsheet (.xlsx)` },
            { value: "zip", label: t`Documents archive (.zip)` },
          ]}
          allowDeselect={false}
          {...form.getInputProps("format")}
        />
        <TextInput
          label={t`Accounting entity`}
          description={t`Optional. Restrict the export to one accounting entity (prefix).`}
          placeholder="TEMA26-"
          {...form.getInputProps("accountingEntity")}
        />
        <Group justify="flex-end" mt="sm">
          <Button variant="default" onClick={onClose}>
            <Trans>Cancel</Trans>
          </Button>
          <Button
            loading={busy}
            leftSection={<IconDownload size={16} />}
            onClick={() => void onSubmit()}
          >
            <Trans>Start export</Trans>
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}

export function InvoicesList() {
  const { t, i18n } = useLingui();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [exportOpen, setExportOpen] = useState(false);

  // The address bar is the source of truth for all filters.
  const params = useMemo(() => paramsFromUrl(searchParams), [searchParams]);

  // Mirror the canonical query into localStorage so the "Back to invoices" link
  // on detail pages can return to this exact filtered view.
  useEffect(() => {
    saveListQuery("invoices", paramsToUrl(params));
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
  const { data, error, isLoading } = useInvoiceSearch({
    ...params,
    limit: LIMIT,
  });
  const invoices = data?.data ?? [];

  // Populate the accounting entity filter
  const { data: accountingEntitiesData } = useAccountingEntities();
  const accountingEntityOptions = useMemo(
    () =>
      (accountingEntitiesData ?? [])
        .map((e) => {
          return { value: e, label: e };
        }),
    [accountingEntitiesData],
  );

  // Any change resets pagination unless an explicit offset is supplied.
  function commit(next: InvoiceSearchParams) {
    setSearchParams(paramsToUrl(next), { replace: true });
  }

  const activeFilters = hasActiveFilters(params);

  return (
    <Stack>
      <Group justify="space-between" align="flex-end">
        <Stack gap={2}>
          <Title order={1}>
            <Trans>Invoices</Trans>
          </Title>
          <Text size="sm" c="dimmed">
            <Trans>Browse issued invoices, generate new ones and export.</Trans>
          </Text>
        </Stack>
        <Group>
          <Button
            variant="default"
            leftSection={<IconDownload size={16} />}
            onClick={() => setExportOpen(true)}
          >
            <Trans>Export</Trans>
          </Button>
          <Button
            leftSection={<IconPlus size={16} />}
            onClick={() => navigate(`/${i18n.locale}/invoices/new`)}
          >
            <Trans>New invoice</Trans>
          </Button>
        </Group>
      </Group>

      <Paper withBorder radius="md" p="md">
        <Group align="flex-end" wrap="wrap" gap="sm">
          <TextInput
            label={t`Search`}
            placeholder={t`Number or recipient…`}
            leftSection={<IconSearch size={16} />}
            value={qInput}
            onChange={(e) => setQInput(e.currentTarget.value)}
            style={{ flex: "1 1 240px" }}
          />
          <MultiSelect
            label={t`Type`}
            placeholder={params.invoiceType?.length ? undefined : t`Any`}
            data={[
              { value: "invoice", label: t`Invoice` },
              { value: "cancellation", label: t`Cancellation` },
            ]}
            value={params.invoiceType ?? []}
            onChange={(v) =>
              commit({
                ...params,
                invoiceType: v as InvoiceType[],
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
            style={{ flex: "1 1 160px" }}
          />
          <TagsInput
            label={t`Accounting entities`}
            placeholder={t`e.g. TEMA26-`}
            value={params.accountingEntity ?? []}
            onChange={(v) =>
              commit({
                ...params,
                accountingEntity: v.length ? v : undefined,
                offset: undefined,
              })
            }
            style={{ flex: "1 1 220px" }}
          />
          <MultiSelect
            label={t`Accounting entities`}
            placeholder={params.accountingEntity?.length ? undefined : t`Any`}
            data={accountingEntityOptions}
            value={params.accountingEntity ?? []}
            onChange={(v) =>
              commit({
                ...params,
                accountingEntity: v.length ? v : undefined,
                offset: undefined,
              })
            }
            searchable
            clearable
            nothingFoundMessage={t`No accounting entities`}
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
          isEmpty={invoices.length === 0}
          empty={
            <Stack align="center" gap="xs" c="dimmed">
              <IconFileInvoice size={32} />
              <Text size="sm">
                {activeFilters ? (
                  <Trans>No invoices match these filters.</Trans>
                ) : (
                  <Trans>No invoices yet. Create the first one.</Trans>
                )}
              </Text>
            </Stack>
          }
        >
          <Pager
            limit={LIMIT}
            offset={offset}
            count={invoices.length}
            pagination={data?.pagination}
            onChange={(next) =>
              commit({ ...params, offset: next ? String(next) : undefined })
            }
          />
          <Table.ScrollContainer minWidth={760}>
            <Table verticalSpacing="sm" highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>
                    <Trans>Number</Trans>
                  </Table.Th>
                  <Table.Th>
                    <Trans>Type</Trans>
                  </Table.Th>
                  <Table.Th>
                    <Trans>Recipient</Trans>
                  </Table.Th>
                  <Table.Th>
                    <Trans>Issued</Trans>
                  </Table.Th>
                  <Table.Th>
                    <Trans>Due</Trans>
                  </Table.Th>
                  <Table.Th>
                    <Trans>Gross</Trans>
                  </Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {invoices.map((invoice) => {
                  const recipient = [
                    invoice.recipient?.contactFirstname,
                    invoice.recipient?.contactLastname,
                  ]
                    .filter(Boolean)
                    .join(" ");
                  return (
                    <Table.Tr
                      key={invoice.id}
                      style={{ cursor: "pointer" }}
                      onClick={() =>
                        navigate(`/${i18n.locale}/invoices/${invoice.id}`)
                      }
                    >
                      <Table.Td>
                        <Text size="sm" fw={500}>
                          {invoice.invoiceNumber || "—"}
                        </Text>
                      </Table.Td>
                      <Table.Td>
                        <InvoiceTypeBadge type={invoice.invoiceType} />
                      </Table.Td>
                      <Table.Td>
                        <Text size="sm">{recipient || "—"}</Text>
                      </Table.Td>
                      <Table.Td>
                        <Text size="sm">{formatDate(invoice.issueDate)}</Text>
                      </Table.Td>
                      <Table.Td>
                        <Text size="sm">{formatDate(invoice.dueDate)}</Text>
                      </Table.Td>
                      <Table.Td>
                        <Text size="sm" fw={500}>
                          {formatMoney(invoice.totalGross, invoice.currency)}
                        </Text>
                      </Table.Td>
                    </Table.Tr>
                  );
                })}
              </Table.Tbody>
            </Table>
          </Table.ScrollContainer>
        </QueryState>
      </Paper>

      <ExportModal opened={exportOpen} onClose={() => setExportOpen(false)} />
    </Stack>
  );
}
