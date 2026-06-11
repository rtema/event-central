import { Trans, useLingui } from "@lingui/react/macro";
import {
  Anchor,
  Button,
  Group,
  Menu,
  Paper,
  Stack,
  Table,
  Text,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import {
  IconArrowLeft,
  IconDownload,
} from "@tabler/icons-react";
import { useState } from "react";
import { Link, useParams } from "react-router";
import { toRequestError } from "../../api/client";
import { invoicesApi } from "../../api/invoices";
import type { InvoiceFileType } from "../../api/types";
import { FieldGrid } from "../ui/FieldGrid";
import { QueryState } from "../ui/QueryState";
import { InvoiceTypeBadge } from "../ui/StatusBadge";
import { formatDateTime } from "../utils/datetime";
import { formatMoney, formatNumber, localizedLabel } from "../utils/format";
import {
  useInvoice,
  useInvoiceLineItems,
  useInvoiceTaxes,
} from "./invoicingHooks";

export function InvoiceDetail() {
  const { t, i18n } = useLingui();
  const { invoiceId = "" } = useParams();
  const { data: invoice, error, isLoading } = useInvoice(invoiceId);
  const { data: lineItems } = useInvoiceLineItems(invoiceId);
  const { data: taxes } = useInvoiceTaxes(invoiceId);
  const [downloading, setDownloading] = useState<InvoiceFileType | null>(null);

  const currency = invoice?.currency;

  const download = async (fileType: InvoiceFileType) => {
    setDownloading(fileType);
    try {
      const { url } = await invoicesApi.link(invoiceId, {
        fileType,
        expiresIn: 3600,
      });
      if (url) window.open(url, "_blank", "noopener");
    } catch (err) {
      notifications.show({
        color: "red",
        title: t`Could not create download link`,
        message: toRequestError(err).message,
      });
    } finally {
      setDownloading(null);
    }
  };

  return (
    <Stack>
      <Anchor component={Link} to="/invoices" size="sm">
        <Group gap={4}>
          <IconArrowLeft size={14} />
          <Trans>Back to invoices</Trans>
        </Group>
      </Anchor>

      <QueryState isLoading={isLoading} error={error}>
        {invoice && (
          <>
            <Paper withBorder p="lg" radius="md">
              <Group justify="space-between" align="flex-start">
                <Stack gap={4}>
                  <Group gap="sm">
                    <Title order={2}>
                      {invoice.invoiceNumber || invoice.id}
                    </Title>
                    <InvoiceTypeBadge type={invoice.invoiceType} />
                  </Group>
                  <Text size="sm" c="dimmed">
                    <Trans>Issued</Trans> {formatDateTime(invoice.issueDate)}
                    {invoice.dueDate && (
                      <>
                        {" · "}
                        <Trans>Due</Trans> {formatDateTime(invoice.dueDate)}
                      </>
                    )}
                  </Text>
                </Stack>
                <Menu position="bottom-end" withinPortal>
                  <Menu.Target>
                    <Button
                      leftSection={<IconDownload size={16} />}
                      loading={downloading !== null}
                    >
                      <Trans>Download</Trans>
                    </Button>
                  </Menu.Target>
                  <Menu.Dropdown>
                    <Menu.Item onClick={() => void download("pdf")}>
                      <Trans>PDF (ZUGFeRD)</Trans>
                    </Menu.Item>
                    <Menu.Item onClick={() => void download("xrechnung")}>
                      <Trans>XRechnung (XML)</Trans>
                    </Menu.Item>
                  </Menu.Dropdown>
                </Menu>
              </Group>
            </Paper>

            <Paper withBorder p="lg" radius="md">
              <Title order={4} mb="md">
                <Trans>Summary</Trans>
              </Title>
              <FieldGrid
                cols={{ base: 1, sm: 3 }}
                fields={[
                  { label: t`Accounting entity`, value: invoice.accountingEntity },
                  {
                    label: t`Accounting number`,
                    value:
                      invoice.accountingNumber != null
                        ? formatNumber(invoice.accountingNumber)
                        : undefined,
                  },
                  { label: t`Type code`, value: invoice.invoiceTypeCode },
                  { label: t`Language`, value: invoice.locale?.toUpperCase() },
                  { label: t`Currency`, value: invoice.currency },
                  { label: t`Created by`, value: invoice.createdBy },
                  {
                    label: t`Order`,
                    value: invoice.orderId ? (
                      <Anchor component={Link} to={`/${i18n.locale}/orders/${invoice.orderId}`} size="sm">
                        {invoice.orderId}
                      </Anchor>
                    ) : undefined,
                  },
                  { label: t`Net total`, value: formatMoney(invoice.totalNet, currency) },
                  { label: t`Tax total`, value: formatMoney(invoice.totalTax, currency) },
                  {
                    label: t`Gross total`,
                    value: (
                      <Text fw={700}>{formatMoney(invoice.totalGross, currency)}</Text>
                    ),
                  },
                ]}
              />
            </Paper>

            <Group align="stretch" grow wrap="wrap">
              <Paper withBorder p="lg" radius="md" miw={280}>
                <Title order={4} mb="md">
                  <Trans>Supplier</Trans>
                </Title>
                <FieldGrid
                  cols={1}
                  fields={[
                    { label: t`Legal name`, value: invoice.supplier?.legalName },
                    { label: t`VAT ID`, value: invoice.supplier?.vatId },
                    { label: t`IBAN`, value: invoice.supplier?.iban },
                    {
                      label: t`Address`,
                      value: [
                        invoice.supplier?.line1,
                        invoice.supplier?.line2,
                        [invoice.supplier?.zipCode, invoice.supplier?.city]
                          .filter(Boolean)
                          .join(" "),
                        invoice.supplier?.country?.toUpperCase(),
                      ]
                        .filter(Boolean)
                        .join(", "),
                    },
                    { label: t`Contact`, value: invoice.supplier?.contactName },
                    { label: t`Email`, value: invoice.supplier?.contactEmail },
                  ]}
                />
              </Paper>
              <Paper withBorder p="lg" radius="md" miw={280}>
                <Title order={4} mb="md">
                  <Trans>Recipient</Trans>
                </Title>
                <FieldGrid
                  cols={1}
                  fields={[
                    { label: t`Contact`, value: invoice.recipient?.contactName },
                    { label: t`Email`, value: invoice.recipient?.contactEmail },
                    { label: t`VAT ID`, value: invoice.recipient?.vatId },
                    {
                      label: t`Address`,
                      value: [
                        invoice.recipient?.line1,
                        invoice.recipient?.line2,
                        [invoice.recipient?.zipCode, invoice.recipient?.city]
                          .filter(Boolean)
                          .join(" "),
                        invoice.recipient?.country?.toUpperCase(),
                      ]
                        .filter(Boolean)
                        .join(", "),
                    },
                    {
                      label: t`PO reference`,
                      value: invoice.recipient?.purchaseOrderReference,
                    },
                  ]}
                />
              </Paper>
            </Group>

            <Paper withBorder p="lg" radius="md">
              <Title order={4} mb="md">
                <Trans>Line items</Trans>
              </Title>
              <Table.ScrollContainer minWidth={640}>
                <Table verticalSpacing="sm">
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>
                        <Trans>Description</Trans>
                      </Table.Th>
                      <Table.Th ta="right">
                        <Trans>Qty</Trans>
                      </Table.Th>
                      <Table.Th ta="right">
                        <Trans>Unit price</Trans>
                      </Table.Th>
                      <Table.Th ta="right">
                        <Trans>Tax</Trans>
                      </Table.Th>
                      <Table.Th ta="right">
                        <Trans>Net</Trans>
                      </Table.Th>
                      <Table.Th ta="right">
                        <Trans>Gross</Trans>
                      </Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {(lineItems ?? []).map((li) => (
                      <Table.Tr key={li.id ?? li.position}>
                        <Table.Td>
                          <Text size="sm">{li.name}</Text>
                          {li.ticket?.externalTicketOptionLabel && (
                            <Text size="xs" c="dimmed">
                              {li.ticket.externalTicketOptionLabel}
                            </Text>
                          )}
                        </Table.Td>
                        <Table.Td ta="right">{formatNumber(li.quantity)}</Table.Td>
                        <Table.Td ta="right">
                          {formatMoney(li.pricePerUnit, currency)}
                        </Table.Td>
                        <Table.Td ta="right">
                          {li.taxRate != null ? `${formatNumber(li.taxRate)}%` : "—"}
                        </Table.Td>
                        <Table.Td ta="right">
                          {formatMoney(li.totalNet, currency)}
                        </Table.Td>
                        <Table.Td ta="right">
                          {formatMoney(li.totalGross, currency)}
                        </Table.Td>
                      </Table.Tr>
                    ))}
                    {(lineItems?.length ?? 0) === 0 && (
                      <Table.Tr>
                        <Table.Td colSpan={6}>
                          <Text size="sm" c="dimmed" ta="center" py="md">
                            <Trans>No line items.</Trans>
                          </Text>
                        </Table.Td>
                      </Table.Tr>
                    )}
                  </Table.Tbody>
                </Table>
              </Table.ScrollContainer>
            </Paper>

            {(taxes?.length ?? 0) > 0 && (
              <Paper withBorder p="lg" radius="md">
                <Title order={4} mb="md">
                  <Trans>Applied tax rates</Trans>
                </Title>
                <Table verticalSpacing="sm">
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>
                        <Trans>Label</Trans>
                      </Table.Th>
                      <Table.Th ta="right">
                        <Trans>Rate</Trans>
                      </Table.Th>
                      <Table.Th>
                        <Trans>Type</Trans>
                      </Table.Th>
                      <Table.Th>
                        <Trans>Exemption reason</Trans>
                      </Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {(taxes ?? []).map((tax) => (
                      <Table.Tr key={tax.id}>
                        <Table.Td>{localizedLabel(tax.label)}</Table.Td>
                        <Table.Td ta="right">
                          {tax.rate != null ? `${formatNumber(tax.rate)}%` : "—"}
                        </Table.Td>
                        <Table.Td>{tax.type ?? "standard"}</Table.Td>
                        <Table.Td>{tax.taxExemptionReason ?? "—"}</Table.Td>
                      </Table.Tr>
                    ))}
                  </Table.Tbody>
                </Table>
              </Paper>
            )}
          </>
        )}
      </QueryState>
    </Stack>
  );
}
