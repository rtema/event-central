import { Trans, useLingui } from "@lingui/react/macro";
import {
  Button,
  Group,
  Modal,
  Paper,
  Select,
  Stack,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { useForm } from "@mantine/form";
import { notifications } from "@mantine/notifications";
import { IconDownload, IconFileInvoice, IconPlus } from "@tabler/icons-react";
import type { ColumnDef } from "@tanstack/react-table";
import { useMemo, useState } from "react";
import { useNavigate } from "react-router";
import { toRequestError } from "../../api/client";
import { invoicesApi } from "../../api/invoices";
import type { Invoice, InvoiceExportFormat } from "../../api/types";
import { DataTable } from "../ui/DataTable";
import { Pager } from "../ui/Pager";
import { QueryState } from "../ui/QueryState";
import { InvoiceTypeBadge } from "../ui/StatusBadge";
import { formatDate } from "../utils/datetime";
import { formatMoney } from "../utils/format";
import { useInvoices } from "./invoicingHooks";

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
  const [offset, setOffset] = useState(0);
  const [exportOpen, setExportOpen] = useState(false);
  const { data, error, isLoading } = useInvoices({
    limit: LIMIT,
    offset: String(offset),
  });

  const invoices = data?.data ?? [];

  const columns = useMemo<ColumnDef<Invoice>[]>(
    () => [
      {
        accessorKey: "invoiceNumber",
        header: t`Number`,
        cell: (info) => (
          <Text fw={500} size="sm">
            {info.getValue<string>() || "—"}
          </Text>
        ),
      },
      {
        id: "type",
        header: t`Type`,
        accessorFn: (i) => i.invoiceType ?? "invoice",
        enableSorting: false,
        cell: (info) => <InvoiceTypeBadge type={info.row.original.invoiceType} />,
      },
      {
        id: "recipient",
        header: t`Recipient`,
        accessorFn: (i) => `${i.recipient?.contactFirstname} ${i.recipient?.contactLastname}`,
        cell: (info) => (
          <Text size="sm">{info.getValue<string>() || "—"}</Text>
        ),
      },
      {
        accessorKey: "issueDate",
        header: t`Issued`,
        cell: (info) => (
          <Text size="sm">{formatDate(info.getValue<string>())}</Text>
        ),
      },
      {
        accessorKey: "dueDate",
        header: t`Due`,
        cell: (info) => (
          <Text size="sm">{formatDate(info.getValue<string>())}</Text>
        ),
      },
      {
        accessorKey: "totalGross",
        header: t`Gross`,
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
        <QueryState
          isLoading={isLoading}
          error={error}
          isEmpty={invoices.length === 0}
          empty={
            <Stack align="center" gap="xs" c="dimmed">
              <IconFileInvoice size={32} />
              <Text size="sm">
                <Trans>No invoices yet. Create the first one.</Trans>
              </Text>
            </Stack>
          }
        >
          <DataTable
            data={invoices}
            columns={columns}
            searchable
            searchPlaceholder={t`Search number or recipient`}
            initialSorting={[{ id: "issueDate", desc: true }]}
            onRowClick={(row) => navigate(`/${i18n.locale}/invoices/${row.id}`)}
            minWidth={760}
          />
          <Pager
            limit={LIMIT}
            offset={offset}
            count={invoices.length}
            pagination={data?.pagination}
            onChange={setOffset}
          />
        </QueryState>
      </Paper>

      <ExportModal opened={exportOpen} onClose={() => setExportOpen(false)} />
    </Stack>
  );
}
