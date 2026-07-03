import { Trans, useLingui } from "@lingui/react/macro";
import {
  Accordion,
  ActionIcon,
  Anchor,
  Button,
  Divider,
  Grid,
  Group,
  NumberInput,
  Paper,
  Select,
  SimpleGrid,
  Stack,
  TagsInput,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { DateTimePicker } from "@mantine/dates";
import { useForm } from "@mantine/form";
import { modals } from "@mantine/modals";
import { notifications } from "@mantine/notifications";
import {
  IconArrowLeft,
  IconBuildingStore,
  IconCalendarEvent,
  IconDownload,
  IconFileText,
  IconPercentage,
  IconPlus,
  IconReceipt,
  IconTrash,
  IconUser,
} from "@tabler/icons-react";
import { useMemo, useState } from "react";
import { Link, useNavigate } from "react-router";
import { useSWRConfig } from "swr";
import { toRequestError } from "../../api/client";
import { invoicesApi } from "../../api/invoices";
import type {
  InvoiceCreateRequest,
  InvoiceCreateResponse,
  Locale,
  TaxType,
} from "../../api/types";
import { downloadBase64, formatMoney } from "../utils/format";

interface TaxRateForm {
  externalId: string;
  rate: number | string;
  label: string;
  type: TaxType;
  taxExemptionReason: string;
}
interface LineItemForm {
  name: string;
  quantity: number | string;
  pricePerUnit: number | string;
  externalTaxId: string;
  ticketLabel: string;
}
interface InvoiceFormValues {
  eventId: string;
  eventLabel: string;
  eventStartDt: Date | null;
  eventEndDt: Date | null;
  externalOrderId: string;
  locale: Locale;
  dueDate: Date | null;
  acctPrefix: string;
  acctFirstNumber: number | string;
  acctPad: number | string;
  supplier: {
    legalName: string;
    legalRegistration: string;
    vatId: string;
    iban: string;
    line1: string;
    line2: string;
    city: string;
    zipCode: string;
    country: string;
    contactName: string;
    contactEmail: string;
    contactPhone: string;
  };
  recipient: {
    contactName: string;
    contactEmail: string;
    contactPhone: string;
    contactCcEmail: string[];
    line1: string;
    line2: string;
    city: string;
    zipCode: string;
    country: string;
    vatId: string;
    purchaseOrderReference: string;
  };
  taxRates: TaxRateForm[];
  lineItems: LineItemForm[];
  paymentLink: string;
  orderLink: string;
  templateName: string;
}

const num = (v: number | string): number => {
  const n = typeof v === "number" ? v : parseFloat(v);
  return Number.isFinite(n) ? n : 0;
};

/** Drop empty strings / undefined so we don't send noise to the API. */
function clean<T extends Record<string, unknown>>(obj: T): Partial<T> {
  const out: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(obj)) {
    if (v === "" || v == null) continue;
    if (Array.isArray(v) && v.length === 0) continue;
    out[k] = v;
  }
  return out as Partial<T>;
}

function SuccessModalContent({ res }: { res: InvoiceCreateResponse }) {
  const number = res.invoice?.invoiceNumber ?? res.invoice?.id;
  return (
    <Stack>
      <Text size="sm">
        <Trans>Invoice {number} was generated successfully.</Trans>
      </Text>
      <Group>
        {res.invoicePdf && (
          <Button
            variant="light"
            leftSection={<IconDownload size={16} />}
            onClick={() =>
              downloadBase64(res.invoicePdf!, `${number}.pdf`, "application/pdf")
            }
          >
            <Trans>Download PDF</Trans>
          </Button>
        )}
        {res.invoiceXml && (
          <Button
            variant="light"
            leftSection={<IconDownload size={16} />}
            onClick={() =>
              downloadBase64(res.invoiceXml!, `${number}.xml`, "application/xml")
            }
          >
            <Trans>Download XRechnung</Trans>
          </Button>
        )}
      </Group>
    </Stack>
  );
}

export function InvoiceCreate() {
  const { t, i18n } = useLingui();
  const navigate = useNavigate();
  const { mutate } = useSWRConfig();
  const [saving, setSaving] = useState(false);

  const form = useForm<InvoiceFormValues>({
    initialValues: {
      eventId: "",
      eventLabel: "",
      eventStartDt: null,
      eventEndDt: null,
      externalOrderId: "",
      locale: "de",
      dueDate: null,
      acctPrefix: "",
      acctFirstNumber: 1,
      acctPad: 6,
      supplier: {
        legalName: "",
        legalRegistration: "",
        vatId: "",
        iban: "",
        line1: "",
        line2: "",
        city: "",
        zipCode: "",
        country: "de",
        contactName: "",
        contactEmail: "",
        contactPhone: "",
      },
      recipient: {
        contactName: "",
        contactEmail: "",
        contactPhone: "",
        contactCcEmail: [],
        line1: "",
        line2: "",
        city: "",
        zipCode: "",
        country: "de",
        vatId: "",
        purchaseOrderReference: "",
      },
      taxRates: [
        {
          externalId: "vat-standard",
          rate: 19,
          label: "USt. 19 %",
          type: "standard",
          taxExemptionReason: "",
        },
      ],
      lineItems: [
        {
          name: "",
          quantity: 1,
          pricePerUnit: 0,
          externalTaxId: "vat-standard",
          ticketLabel: "",
        },
      ],
      paymentLink: "",
      orderLink: "",
      templateName: "",
    },
    validate: {
      eventId: (v) => (v.trim() ? null : t`Event ID is required`),
      recipient: {
        contactName: (v) => (v.trim() ? null : t`Recipient name is required`),
      },
      acctPrefix: (v) => (v.trim() ? null : t`Accounting prefix is required`),
      taxRates: {
        externalId: (v) => (v.trim() ? null : t`Required`),
        label: (v) => (v.trim() ? null : t`Required`),
      },
      lineItems: {
        name: (v) => (v.trim() ? null : t`Required`),
        externalTaxId: (v) => (v.trim() ? null : t`Pick a tax rate`),
      },
    },
  });

  const taxOptions = useMemo(
    () =>
      form.values.taxRates
        .filter((r) => r.externalId.trim())
        .map((r) => ({
          value: r.externalId,
          label: `${r.label || r.externalId} (${num(r.rate)}%)`,
        })),
    [form.values.taxRates],
  );

  // Live gross total preview (prices are tax-inclusive per the spec).
  const grossTotal = useMemo(
    () =>
      form.values.lineItems.reduce(
        (sum, li) => sum + num(li.quantity) * num(li.pricePerUnit),
        0,
      ),
    [form.values.lineItems],
  );

  const onSubmit = async () => {
    const result = form.validate();
    if (result.hasErrors) {
      notifications.show({
        color: "red",
        title: t`Check the form`,
        message: t`Some required fields are missing or invalid.`,
      });
      return;
    }
    const v = form.values;
    const payload: InvoiceCreateRequest = {
      event: clean({
        id: v.eventId,
        label: v.eventLabel,
        startDt: v.eventStartDt?.toISOString(),
        endDt: v.eventEndDt?.toISOString(),
      }),
      externalOrderId: v.externalOrderId || undefined,
      locale: v.locale,
      currency: "EUR",
      dueDate: v.dueDate?.toISOString(),
      accountingEntity: {
        prefix: v.acctPrefix,
        firstInvoiceNumber: num(v.acctFirstNumber),
        ...(v.acctPad !== "" ? { padNumber: num(v.acctPad) } : {}),
      },
      supplier: clean(v.supplier),
      recipient: clean(v.recipient),
      taxRates: v.taxRates.map((r) => ({
        externalId: r.externalId,
        rate: num(r.rate),
        label: r.label,
        type: r.type,
        ...(r.type === "exempt-verein" && r.taxExemptionReason
          ? { taxExemptionReason: r.taxExemptionReason }
          : {}),
      })),
      lineItems: v.lineItems.map((li) => ({
        name: li.name,
        quantity: num(li.quantity),
        pricePerUnit: num(li.pricePerUnit),
        externalTaxId: li.externalTaxId,
        ...(li.ticketLabel
          ? { ticket: { externalTicketOptionLabel: li.ticketLabel } }
          : {}),
      })),
      links:
        v.paymentLink || v.orderLink
          ? clean({ paymentLink: v.paymentLink, orderLink: v.orderLink })
          : undefined,
      invoiceTemplate: v.templateName
        ? { templateName: v.templateName }
        : undefined,
    };

    setSaving(true);
    try {
      const res = await invoicesApi.create(payload);
      void mutate((key) => Array.isArray(key) && key[0] === "invoices");
      modals.open({
        title: t`Invoice created`,
        children: <SuccessModalContent res={res} />,
      });
      notifications.show({
        color: "pine",
        title: t`Invoice created`,
        message: res.invoice?.invoiceNumber ?? res.invoice?.id,
      });
      if (res.invoice?.id) navigate(`/${i18n.locale}/invoices/${res.invoice.id}`);
    } catch (err) {
      notifications.show({
        color: "red",
        title: t`Could not create invoice`,
        message: toRequestError(err).message,
      });
    } finally {
      setSaving(false);
    }
  };

  return (
    <Stack maw={900} mx="auto" w="100%">
      <Anchor component={Link} to={`/${i18n.locale}/invoices`} size="sm">
        <Group gap={4}>
          <IconArrowLeft size={14} />
          <Trans>Back to invoices</Trans>
        </Group>
      </Anchor>

      <Group justify="space-between" align="flex-end">
        <Stack gap={2}>
          <Title order={1}>
            <Trans>New invoice</Trans>
          </Title>
          <Text size="sm" c="dimmed">
            <Trans>
              Generate an invoice and its e-invoice documents in one step.
            </Trans>
          </Text>
        </Stack>
      </Group>

      <Accordion
        multiple
        defaultValue={["basics", "recipient", "taxes", "items"]}
        variant="separated"
      >
        <Accordion.Item value="basics">
          <Accordion.Control icon={<IconCalendarEvent size={18} />}>
            <Trans>Event & basics</Trans>
          </Accordion.Control>
          <Accordion.Panel>
            <Stack>
              <SimpleGrid cols={{ base: 1, sm: 2 }}>
                <TextInput
                  label={t`Event ID`}
                  withAsterisk
                  placeholder="tech-summit-2026"
                  {...form.getInputProps("eventId")}
                />
                <TextInput
                  label={t`Event name`}
                  {...form.getInputProps("eventLabel")}
                />
                <DateTimePicker
                  label={t`Event start`}
                  clearable
                  {...form.getInputProps("eventStartDt")}
                />
                <DateTimePicker
                  label={t`Event end`}
                  clearable
                  {...form.getInputProps("eventEndDt")}
                />
                <TextInput
                  label={t`External order ID`}
                  description={t`Unique per event`}
                  {...form.getInputProps("externalOrderId")}
                />
                <Select
                  label={t`Language`}
                  data={[
                    { value: "de", label: t`German` },
                    { value: "en", label: t`English` },
                  ]}
                  allowDeselect={false}
                  {...form.getInputProps("locale")}
                />
                <DateTimePicker
                  label={t`Due date`}
                  clearable
                  {...form.getInputProps("dueDate")}
                />
              </SimpleGrid>
              <Divider
                label={t`Accounting entity (invoice numbering)`}
                labelPosition="left"
              />
              <SimpleGrid cols={{ base: 1, sm: 3 }}>
                <TextInput
                  label={t`Prefix`}
                  withAsterisk
                  placeholder="TEMA26-"
                  {...form.getInputProps("acctPrefix")}
                />
                <NumberInput
                  label={t`First number`}
                  min={1}
                  {...form.getInputProps("acctFirstNumber")}
                />
                <NumberInput
                  label={t`Pad digits`}
                  min={0}
                  max={12}
                  {...form.getInputProps("acctPad")}
                />
              </SimpleGrid>
            </Stack>
          </Accordion.Panel>
        </Accordion.Item>

        <Accordion.Item value="supplier">
          <Accordion.Control icon={<IconBuildingStore size={18} />}>
            <Trans>Supplier</Trans>
          </Accordion.Control>
          <Accordion.Panel>
            <SimpleGrid cols={{ base: 1, sm: 2 }}>
              <TextInput
                label={t`Legal name`}
                {...form.getInputProps("supplier.legalName")}
              />
              <TextInput
                label={t`Commercial register`}
                {...form.getInputProps("supplier.legalRegistration")}
              />
              <TextInput
                label={t`VAT ID`}
                {...form.getInputProps("supplier.vatId")}
              />
              <TextInput
                label={t`IBAN`}
                {...form.getInputProps("supplier.iban")}
              />
              <TextInput
                label={t`Address line 1`}
                {...form.getInputProps("supplier.line1")}
              />
              <TextInput
                label={t`Address line 2`}
                {...form.getInputProps("supplier.line2")}
              />
              <TextInput
                label={t`ZIP code`}
                {...form.getInputProps("supplier.zipCode")}
              />
              <TextInput
                label={t`City`}
                {...form.getInputProps("supplier.city")}
              />
              <TextInput
                label={t`Country (ISO 2-letter)`}
                {...form.getInputProps("supplier.country")}
              />
              <TextInput
                label={t`Contact name`}
                {...form.getInputProps("supplier.contactName")}
              />
              <TextInput
                label={t`Contact email`}
                {...form.getInputProps("supplier.contactEmail")}
              />
              <TextInput
                label={t`Contact phone`}
                {...form.getInputProps("supplier.contactPhone")}
              />
            </SimpleGrid>
          </Accordion.Panel>
        </Accordion.Item>

        <Accordion.Item value="recipient">
          <Accordion.Control icon={<IconUser size={18} />}>
            <Trans>Recipient</Trans>
          </Accordion.Control>
          <Accordion.Panel>
            <SimpleGrid cols={{ base: 1, sm: 2 }}>
              <TextInput
                label={t`Contact name`}
                withAsterisk
                {...form.getInputProps("recipient.contactName")}
              />
              <TextInput
                label={t`Contact email`}
                {...form.getInputProps("recipient.contactEmail")}
              />
              <TextInput
                label={t`Contact phone`}
                {...form.getInputProps("recipient.contactPhone")}
              />
              <TagsInput
                label={t`CC emails`}
                placeholder={t`Add email and press Enter`}
                {...form.getInputProps("recipient.contactCcEmail")}
              />
              <TextInput
                label={t`Address line 1`}
                {...form.getInputProps("recipient.line1")}
              />
              <TextInput
                label={t`Address line 2`}
                {...form.getInputProps("recipient.line2")}
              />
              <TextInput
                label={t`ZIP code`}
                {...form.getInputProps("recipient.zipCode")}
              />
              <TextInput
                label={t`City`}
                {...form.getInputProps("recipient.city")}
              />
              <TextInput
                label={t`Country (ISO 2-letter)`}
                {...form.getInputProps("recipient.country")}
              />
              <TextInput
                label={t`VAT ID`}
                {...form.getInputProps("recipient.vatId")}
              />
              <TextInput
                label={t`Purchase order reference`}
                {...form.getInputProps("recipient.purchaseOrderReference")}
              />
            </SimpleGrid>
          </Accordion.Panel>
        </Accordion.Item>

        <Accordion.Item value="taxes">
          <Accordion.Control icon={<IconPercentage size={18} />}>
            <Trans>Tax rates</Trans>
          </Accordion.Control>
          <Accordion.Panel>
            <Stack>
              {form.values.taxRates.map((rate, idx) => (
                <Paper key={idx} withBorder p="sm" radius="md">
                  <Grid align="flex-end" gutter="xs">
                    <Grid.Col span={{ base: 12, sm: 3 }}>
                      <TextInput
                        label={t`Reference ID`}
                        {...form.getInputProps(`taxRates.${idx}.externalId`)}
                      />
                    </Grid.Col>
                    <Grid.Col span={{ base: 6, sm: 2 }}>
                      <NumberInput
                        label={t`Rate %`}
                        min={0}
                        max={100}
                        decimalScale={2}
                        {...form.getInputProps(`taxRates.${idx}.rate`)}
                      />
                    </Grid.Col>
                    <Grid.Col span={{ base: 6, sm: 3 }}>
                      <TextInput
                        label={t`Label`}
                        {...form.getInputProps(`taxRates.${idx}.label`)}
                      />
                    </Grid.Col>
                    <Grid.Col span={{ base: 10, sm: 3 }}>
                      <Select
                        label={t`Type`}
                        data={[
                          { value: "standard", label: t`Standard VAT` },
                          { value: "exempt-verein", label: t`Exempt (Verein)` },
                        ]}
                        allowDeselect={false}
                        {...form.getInputProps(`taxRates.${idx}.type`)}
                      />
                    </Grid.Col>
                    <Grid.Col span={{ base: 2, sm: 1 }}>
                      <ActionIcon
                        variant="subtle"
                        color="red"
                        disabled={form.values.taxRates.length <= 1}
                        onClick={() => form.removeListItem("taxRates", idx)}
                        aria-label={t`Remove tax rate`}
                      >
                        <IconTrash size={16} />
                      </ActionIcon>
                    </Grid.Col>
                    {rate.type === "exempt-verein" && (
                      <Grid.Col span={12}>
                        <TextInput
                          label={t`Tax exemption reason`}
                          {...form.getInputProps(
                            `taxRates.${idx}.taxExemptionReason`,
                          )}
                        />
                      </Grid.Col>
                    )}
                  </Grid>
                </Paper>
              ))}
              <Group>
                <Button
                  variant="light"
                  size="xs"
                  leftSection={<IconPlus size={14} />}
                  onClick={() =>
                    form.insertListItem("taxRates", {
                      externalId: "",
                      rate: 0,
                      label: "",
                      type: "standard",
                      taxExemptionReason: "",
                    })
                  }
                >
                  <Trans>Add tax rate</Trans>
                </Button>
              </Group>
            </Stack>
          </Accordion.Panel>
        </Accordion.Item>

        <Accordion.Item value="items">
          <Accordion.Control icon={<IconReceipt size={18} />}>
            <Trans>Line items</Trans>
          </Accordion.Control>
          <Accordion.Panel>
            <Stack>
              {form.values.lineItems.map((li, idx) => (
                <Paper key={idx} withBorder p="sm" radius="md">
                  <Grid align="flex-end" gutter="xs">
                    <Grid.Col span={{ base: 12, sm: 4 }}>
                      <TextInput
                        label={t`Description`}
                        {...form.getInputProps(`lineItems.${idx}.name`)}
                      />
                    </Grid.Col>
                    <Grid.Col span={{ base: 4, sm: 2 }}>
                      <NumberInput
                        label={t`Qty`}
                        min={0}
                        decimalScale={2}
                        {...form.getInputProps(`lineItems.${idx}.quantity`)}
                      />
                    </Grid.Col>
                    <Grid.Col span={{ base: 8, sm: 2 }}>
                      <NumberInput
                        label={t`Unit price`}
                        min={0}
                        decimalScale={2}
                        {...form.getInputProps(`lineItems.${idx}.pricePerUnit`)}
                      />
                    </Grid.Col>
                    <Grid.Col span={{ base: 10, sm: 3 }}>
                      <Select
                        label={t`Tax`}
                        data={taxOptions}
                        allowDeselect={false}
                        {...form.getInputProps(`lineItems.${idx}.externalTaxId`)}
                      />
                    </Grid.Col>
                    <Grid.Col span={{ base: 2, sm: 1 }}>
                      <ActionIcon
                        variant="subtle"
                        color="red"
                        disabled={form.values.lineItems.length <= 1}
                        onClick={() => form.removeListItem("lineItems", idx)}
                        aria-label={t`Remove line item`}
                      >
                        <IconTrash size={16} />
                      </ActionIcon>
                    </Grid.Col>
                    <Grid.Col span={12}>
                      <TextInput
                        label={t`Ticket option label (optional)`}
                        {...form.getInputProps(`lineItems.${idx}.ticketLabel`)}
                      />
                    </Grid.Col>
                  </Grid>
                  <Text size="xs" c="dimmed" mt={6}>
                    <Trans>Line total</Trans>:{" "}
                    {formatMoney(num(li.quantity) * num(li.pricePerUnit))}
                  </Text>
                </Paper>
              ))}
              <Group justify="space-between">
                <Button
                  variant="light"
                  size="xs"
                  leftSection={<IconPlus size={14} />}
                  onClick={() =>
                    form.insertListItem("lineItems", {
                      name: "",
                      quantity: 1,
                      pricePerUnit: 0,
                      externalTaxId: taxOptions[0]?.value ?? "",
                      ticketLabel: "",
                    })
                  }
                >
                  <Trans>Add line item</Trans>
                </Button>
                <Text fw={600}>
                  <Trans>Total (gross)</Trans>: {formatMoney(grossTotal)}
                </Text>
              </Group>
            </Stack>
          </Accordion.Panel>
        </Accordion.Item>

        <Accordion.Item value="extras">
          <Accordion.Control icon={<IconFileText size={18} />}>
            <Trans>Links & template</Trans>
          </Accordion.Control>
          <Accordion.Panel>
            <Stack>
              <SimpleGrid cols={{ base: 1, sm: 2 }}>
                <TextInput
                  label={t`Payment link`}
                  {...form.getInputProps("paymentLink")}
                />
                <TextInput
                  label={t`Order link`}
                  {...form.getInputProps("orderLink")}
                />
              </SimpleGrid>
              <TextInput
                label={t`Template name`}
                description={t`Leave blank to use the default invoice template.`}
                placeholder="invoice-v01"
                {...form.getInputProps("templateName")}
              />
            </Stack>
          </Accordion.Panel>
        </Accordion.Item>
      </Accordion>

      <Group justify="flex-end" mt="md">
        <Button variant="default" onClick={() => navigate(`/${i18n.locale}/invoices`)}>
          <Trans>Cancel</Trans>
        </Button>
        <Button
          loading={saving}
          leftSection={<IconReceipt size={16} />}
          onClick={() => void onSubmit()}
        >
          <Trans>Create invoice</Trans>
        </Button>
      </Group>
    </Stack>
  );
}
