import { Trans, useLingui } from "@lingui/react/macro";
import {
  Anchor,
  Button,
  Group,
  Modal,
  NumberInput,
  Paper,
  Select,
  Stack,
  Table,
  Tabs,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { useForm } from "@mantine/form";
import { modals } from "@mantine/modals";
import { notifications } from "@mantine/notifications";
import {
  IconArrowLeft,
  IconCash,
  IconFileInvoice,
  IconPlus,
  IconX,
} from "@tabler/icons-react";
import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router";
import { toRequestError } from "../../api/client";
import { ordersApi } from "../../api/orders";
import type { PaymentType } from "../../api/types";
import {
  useOrder,
  useOrderInvoices,
  useOrderMutations,
  useOrderPayments,
} from "../invoices/invoicingHooks";
import { FieldGrid } from "../ui/FieldGrid";
import { QueryState } from "../ui/QueryState";
import {
  InvoiceTypeBadge,
  OrderStatusBadge,
  PaymentTypeBadge,
} from "../ui/StatusBadge";
import { formatDate, formatDateTime } from "../utils/datetime";
import { formatMoney } from "../utils/format";

interface PaymentFormValues {
  type: PaymentType;
  amount: number | string;
  provider: string;
  method: string;
  externalId: string;
  status: string;
}

function CreatePaymentModal({
  orderId,
  opened,
  onClose,
}: {
  orderId: string;
  opened: boolean;
  onClose: () => void;
}) {
  const { t } = useLingui();
  const { revalidateOrder } = useOrderMutations(orderId);
  const [saving, setSaving] = useState(false);

  const form = useForm<PaymentFormValues>({
    initialValues: {
      type: "payment",
      amount: 0,
      provider: "",
      method: "",
      externalId: "",
      status: "",
    },
    validate: {
      amount: (v) =>
        Number(v) > 0 ? null : t`Enter an amount greater than zero`,
    },
  });

  const onSubmit = async () => {
    if (form.validate().hasErrors) return;
    setSaving(true);
    try {
      await ordersApi.createPayment(orderId, {
        type: form.values.type,
        amount: Number(form.values.amount),
        currency: "EUR",
        provider: form.values.provider || undefined,
        method: form.values.method || undefined,
        externalId: form.values.externalId || undefined,
        status: form.values.status || undefined,
      });
      revalidateOrder();
      notifications.show({
        color: "pine",
        title: t`Payment recorded`,
        message: formatMoney(Number(form.values.amount)),
      });
      form.reset();
      onClose();
    } catch (err) {
      notifications.show({
        color: "red",
        title: t`Could not record payment`,
        message: toRequestError(err).message,
      });
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal opened={opened} onClose={onClose} title={t`Record payment`} centered>
      <Stack>
        <Group grow>
          <Select
            label={t`Type`}
            data={[
              { value: "payment", label: t`Payment` },
              { value: "refund", label: t`Refund` },
            ]}
            allowDeselect={false}
            {...form.getInputProps("type")}
          />
          <NumberInput
            label={t`Amount (EUR)`}
            withAsterisk
            min={0}
            decimalScale={2}
            {...form.getInputProps("amount")}
          />
        </Group>
        <Group grow>
          <TextInput label={t`Provider`} placeholder="PayOne" {...form.getInputProps("provider")} />
          <TextInput label={t`Method`} placeholder="VISA" {...form.getInputProps("method")} />
        </Group>
        <TextInput
          label={t`External ID`}
          description={t`Unique per event`}
          {...form.getInputProps("externalId")}
        />
        <Group justify="flex-end" mt="sm">
          <Button variant="default" onClick={onClose}>
            <Trans>Cancel</Trans>
          </Button>
          <Button loading={saving} onClick={() => void onSubmit()}>
            <Trans>Record payment</Trans>
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}

export function OrderDetail() {
  const { t, i18n } = useLingui();
  const navigate = useNavigate();
  const { orderId = "" } = useParams();
  const { data: order, error, isLoading } = useOrder(orderId);
  const { data: payments } = useOrderPayments(orderId);
  const { data: invoicesData } = useOrderInvoices(orderId);
  const { revalidateOrder } = useOrderMutations(orderId);
  const [payOpen, setPayOpen] = useState(false);

  const invoices = invoicesData?.data ?? [];
  const cancelled = order?.status === "cancelled";

  const onCancel = () =>
    modals.openConfirmModal({
      title: t`Cancel order`,
      children: (
        <Text size="sm">
          <Trans>
            This issues the cancellation invoices needed to bring the order
            balance to zero. This cannot be undone.
          </Trans>
        </Text>
      ),
      labels: { confirm: t`Cancel order`, cancel: t`Keep order` },
      confirmProps: { color: "red" },
      onConfirm: async () => {
        try {
          const res = await ordersApi.cancel(orderId);
          revalidateOrder();
          notifications.show({
            color: "pine",
            title: t`Order cancelled`,
            message: res.invoice?.invoiceNumber ?? res.invoice?.id,
          });
          if (res.invoice?.id) navigate(`/${i18n.locale}/invoices/${res.invoice.id}`);
        } catch (err) {
          notifications.show({
            color: "red",
            title: t`Could not cancel order`,
            message: toRequestError(err).message,
          });
        }
      },
    });

  return (
    <Stack>
      <Anchor component={Link} to="/orders" size="sm">
        <Group gap={4}>
          <IconArrowLeft size={14} />
          <Trans>Back to orders</Trans>
        </Group>
      </Anchor>

      <QueryState isLoading={isLoading} error={error}>
        {order && (
          <>
            <Paper withBorder p="lg" radius="md">
              <Group justify="space-between" align="flex-start">
                <Stack gap={4}>
                  <Group gap="sm">
                    <Title order={2}>{order.externalId || order.id}</Title>
                    <OrderStatusBadge status={order.status} />
                  </Group>
                  {order.eventId && (
                    <Anchor
                      component={Link}
                      to={`/${i18n.locale}/events/${order.eventId}`}
                      size="sm"
                    >
                      {order.eventId}
                    </Anchor>
                  )}
                </Stack>
                {!cancelled && (
                  <Button
                    variant="light"
                    color="red"
                    leftSection={<IconX size={16} />}
                    onClick={onCancel}
                  >
                    <Trans>Cancel order</Trans>
                  </Button>
                )}
              </Group>

              <FieldGrid
                cols={{ base: 1, sm: 3 }}
                fields={[
                  { label: t`Recipient`, value: order.recipient?.contactName },
                  { label: t`Email`, value: order.recipient?.contactEmail },
                  { label: t`VAT ID`, value: order.recipient?.vatId },
                  { label: t`Created`, value: formatDateTime(order.createdAt) },
                  {
                    label: t`Payment link`,
                    value: order.paymentLink ? (
                      <Anchor href={order.paymentLink} target="_blank" size="sm">
                        <Trans>Open</Trans>
                      </Anchor>
                    ) : undefined,
                  },
                  {
                    label: t`Order link`,
                    value: order.link ? (
                      <Anchor href={order.link} target="_blank" size="sm">
                        <Trans>Open</Trans>
                      </Anchor>
                    ) : undefined,
                  },
                ]}
              />
            </Paper>

            <Tabs defaultValue="invoices" keepMounted={false}>
              <Tabs.List>
                <Tabs.Tab
                  value="invoices"
                  leftSection={<IconFileInvoice size={16} />}
                >
                  <Trans>Invoices</Trans>
                </Tabs.Tab>
                <Tabs.Tab value="payments" leftSection={<IconCash size={16} />}>
                  <Trans>Payments</Trans>
                </Tabs.Tab>
              </Tabs.List>

              <Tabs.Panel value="invoices" pt="lg">
                <Paper withBorder p="lg" radius="md">
                  <Table verticalSpacing="sm">
                    <Table.Thead>
                      <Table.Tr>
                        <Table.Th>
                          <Trans>Number</Trans>
                        </Table.Th>
                        <Table.Th>
                          <Trans>Type</Trans>
                        </Table.Th>
                        <Table.Th>
                          <Trans>Issued</Trans>
                        </Table.Th>
                        <Table.Th ta="right">
                          <Trans>Gross</Trans>
                        </Table.Th>
                      </Table.Tr>
                    </Table.Thead>
                    <Table.Tbody>
                      {invoices.map((inv) => (
                        <Table.Tr
                          key={inv.id}
                          style={{ cursor: "pointer" }}
                          onClick={() => navigate(`/${i18n.locale}/invoices/${inv.id}`)}
                        >
                          <Table.Td>
                            <Text size="sm" fw={500}>
                              {inv.invoiceNumber || inv.id}
                            </Text>
                          </Table.Td>
                          <Table.Td>
                            <InvoiceTypeBadge type={inv.invoiceType} />
                          </Table.Td>
                          <Table.Td>{formatDate(inv.issueDate)}</Table.Td>
                          <Table.Td ta="right">
                            {formatMoney(inv.totalGross, inv.currency)}
                          </Table.Td>
                        </Table.Tr>
                      ))}
                      {invoices.length === 0 && (
                        <Table.Tr>
                          <Table.Td colSpan={4}>
                            <Text size="sm" c="dimmed" ta="center" py="md">
                              <Trans>No invoices for this order yet.</Trans>
                            </Text>
                          </Table.Td>
                        </Table.Tr>
                      )}
                    </Table.Tbody>
                  </Table>
                </Paper>
              </Tabs.Panel>

              <Tabs.Panel value="payments" pt="lg">
                <Paper withBorder p="lg" radius="md">
                  <Group justify="flex-end" mb="md">
                    <Button
                      size="xs"
                      leftSection={<IconPlus size={14} />}
                      onClick={() => setPayOpen(true)}
                    >
                      <Trans>Record payment</Trans>
                    </Button>
                  </Group>
                  <Table verticalSpacing="sm">
                    <Table.Thead>
                      <Table.Tr>
                        <Table.Th>
                          <Trans>Type</Trans>
                        </Table.Th>
                        <Table.Th>
                          <Trans>Provider</Trans>
                        </Table.Th>
                        <Table.Th>
                          <Trans>Method</Trans>
                        </Table.Th>
                        <Table.Th>
                          <Trans>Recorded</Trans>
                        </Table.Th>
                        <Table.Th ta="right">
                          <Trans>Amount</Trans>
                        </Table.Th>
                      </Table.Tr>
                    </Table.Thead>
                    <Table.Tbody>
                      {(payments ?? []).map((p) => (
                        <Table.Tr key={p.id}>
                          <Table.Td>
                            <PaymentTypeBadge type={p.type} />
                          </Table.Td>
                          <Table.Td>{p.provider ?? "—"}</Table.Td>
                          <Table.Td>{p.method ?? "—"}</Table.Td>
                          <Table.Td>{formatDateTime(p.createdAt)}</Table.Td>
                          <Table.Td ta="right">
                            {formatMoney(p.amount, p.currency)}
                          </Table.Td>
                        </Table.Tr>
                      ))}
                      {(payments?.length ?? 0) === 0 && (
                        <Table.Tr>
                          <Table.Td colSpan={5}>
                            <Text size="sm" c="dimmed" ta="center" py="md">
                              <Trans>No payments recorded yet.</Trans>
                            </Text>
                          </Table.Td>
                        </Table.Tr>
                      )}
                    </Table.Tbody>
                  </Table>
                </Paper>
              </Tabs.Panel>
            </Tabs>
          </>
        )}
      </QueryState>

      <CreatePaymentModal
        orderId={orderId}
        opened={payOpen}
        onClose={() => setPayOpen(false)}
      />
    </Stack>
  );
}
