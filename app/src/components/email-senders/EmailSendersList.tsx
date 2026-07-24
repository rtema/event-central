import { Trans, useLingui } from "@lingui/react/macro";
import {
  ActionIcon,
  Badge,
  Button,
  Group,
  Modal,
  MultiSelect,
  Paper,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
  Tooltip,
} from "@mantine/core";
import { useForm } from "@mantine/form";
import { useDebouncedValue } from "@mantine/hooks";
import { modals } from "@mantine/modals";
import { notifications } from "@mantine/notifications";
import {
  IconKey,
  IconMail,
  IconPencil,
  IconPlus,
  IconSearch,
  IconTrash,
} from "@tabler/icons-react";
import { useEffect, useMemo, useState } from "react";
import { toRequestError } from "../../api/client";
import { emailSendersApi } from "../../api/emailSenders";
import { useEmailSenderMutations, useEmailSenderSearch } from "../../api/hooks";
import type { EmailSender, SmtpSecurity } from "../../api/types";
import { Pager } from "../ui/Pager";
import { QueryState } from "../ui/QueryState";
import { localizedLabel } from "../utils/format";
import {
  EmailSenderForm,
  emptySenderValues,
  senderToPayload,
  type SenderFormValues,
} from "./EmailSenderForm";

const LIMIT = 100;

function securityLabel(security?: string) {
  if (security === "ssl") return <Trans>SSL / TLS</Trans>;
  if (security === "plain") return <Trans>Plain</Trans>;
  return <Trans>STARTTLS</Trans>;
}

function valuesFromSender(s: EmailSender): SenderFormValues {
  return {
    ...emptySenderValues(),
    labelDe: s.label?.de ?? "",
    labelEn: s.label?.en ?? "",
    fromEmail: s.fromEmail,
    fromName: s.fromName ?? "",
    replyTo: s.replyTo ?? "",
    host: s.host,
    port: s.port,
    security: (s.security as SmtpSecurity) ?? "starttls",
    username: s.username ?? "",
    password: "",
    passwordMode: "keep",
    purposes: s.purposes ?? [],
    priority: s.priority ?? 0,
  };
}

function SenderModal({
  opened,
  onClose,
  sender,
}: {
  opened: boolean;
  onClose: () => void;
  sender: EmailSender | null;
}) {
  const { t } = useLingui();
  const mode = sender ? "edit" : "create";
  const { revalidateSenders } = useEmailSenderMutations(sender?.id);
  const [saving, setSaving] = useState(false);

  const form = useForm<SenderFormValues>({
    initialValues: sender ? valuesFromSender(sender) : emptySenderValues(),
    validate: {
      fromEmail: (v) =>
        /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(v.trim())
          ? null
          : t`Enter a valid email address`,
      host: (v) => (v.trim() ? null : t`SMTP host is required`),
    },
  });

  // Re-seed the form each time the modal opens. useForm only reads
  // initialValues on first mount, so without this the form keeps whatever
  // values it had when the (single, persistently mounted) modal first rendered
  // — which is why Edit showed a blank form.
  useEffect(() => {
    if (!opened) return;
    const values = sender ? valuesFromSender(sender) : emptySenderValues();
    form.setValues(values);
    form.resetDirty(values);
    // form is stable across renders; excluding it avoids re-running on every keystroke.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [opened, sender]);

  const onSubmit = async () => {
    if (form.validate().hasErrors) return;
    setSaving(true);
    try {
      const payload = senderToPayload(form.values, mode);
      if (sender) await emailSendersApi.update(sender.id, payload);
      else await emailSendersApi.create(payload);
      revalidateSenders();
      notifications.show({
        color: "pine",
        title: sender ? t`Sender updated` : t`Sender created`,
        message: payload.fromEmail,
      });
      onClose();
    } catch (err) {
      notifications.show({
        color: "red",
        title: sender ? t`Could not update sender` : t`Could not create sender`,
        message: toRequestError(err).message,
      });
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title={sender ? t`Edit sender` : t`New sender`}
      size="lg"
    >
      <Stack>
        <EmailSenderForm
          form={form}
          mode={mode}
          hasPassword={Boolean(sender?.password)}
        />
        <Group justify="flex-end" mt="sm">
          <Button variant="default" onClick={onClose}>
            <Trans>Cancel</Trans>
          </Button>
          <Button loading={saving} onClick={() => void onSubmit()}>
            {sender ? <Trans>Save changes</Trans> : <Trans>Create sender</Trans>}
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}

export function EmailSendersList() {
  const { t } = useLingui();
  const { revalidateSenders } = useEmailSenderMutations();

  const [qInput, setQInput] = useState("");
  const [debouncedQ] = useDebouncedValue(qInput, 350);
  const [security, setSecurity] = useState<SmtpSecurity[]>([]);
  const [offset, setOffset] = useState(0);

  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<EmailSender | null>(null);

  const params = useMemo(
    () => ({
      q: debouncedQ || undefined,
      security: security.length ? security : undefined,
      limit: LIMIT,
      offset: String(offset),
    }),
    [debouncedQ, security, offset],
  );

  const { data, error, isLoading } = useEmailSenderSearch(params);
  const senders = data?.data ?? [];
  const activeFilters = Boolean(debouncedQ || security.length);

  const openCreate = () => {
    setEditing(null);
    setModalOpen(true);
  };
  const openEdit = (sender: EmailSender) => {
    setEditing(sender);
    setModalOpen(true);
  };

  const onDelete = (sender: EmailSender) =>
    modals.openConfirmModal({
      title: t`Delete sender`,
      children: (
        <Text size="sm">
          <Trans>
            Delete the sender {sender.fromEmail}? Mail already queued is
            unaffected, but it can no longer be selected for new mail.
          </Trans>
        </Text>
      ),
      labels: { confirm: t`Delete`, cancel: t`Cancel` },
      confirmProps: { color: "red" },
      onConfirm: async () => {
        try {
          await emailSendersApi.remove(sender.id);
          revalidateSenders();
          notifications.show({
            color: "pine",
            title: t`Sender deleted`,
            message: sender.fromEmail,
          });
        } catch (err) {
          notifications.show({
            color: "red",
            title: t`Could not delete`,
            message: toRequestError(err).message,
          });
        }
      },
    });

  return (
    <Stack>
      <Group justify="space-between" align="flex-end">
        <Stack gap={2}>
          <Title order={1}>
            <Trans>Email senders</Trans>
          </Title>
          <Text size="sm" c="dimmed">
            <Trans>
              SMTP configurations used to deliver mail. The highest-priority
              sender for a purpose is chosen automatically.
            </Trans>
          </Text>
        </Stack>
        <Button leftSection={<IconPlus size={16} />} onClick={openCreate}>
          <Trans>New sender</Trans>
        </Button>
      </Group>

      <Paper withBorder radius="md" p="md">
        <Group align="flex-end" wrap="wrap" gap="sm">
          <TextInput
            label={t`Search`}
            placeholder={t`Address, host or name…`}
            leftSection={<IconSearch size={16} />}
            value={qInput}
            onChange={(e) => {
              setQInput(e.currentTarget.value);
              setOffset(0);
            }}
            style={{ flex: "1 1 260px" }}
          />
          <MultiSelect
            label={t`Security`}
            placeholder={security.length ? undefined : t`Any`}
            data={[
              { value: "starttls", label: t`STARTTLS` },
              { value: "ssl", label: t`SSL / TLS` },
              { value: "plain", label: t`Plain` },
            ]}
            value={security}
            onChange={(v) => {
              setSecurity(v as SmtpSecurity[]);
              setOffset(0);
            }}
            clearable
            style={{ flex: "1 1 220px" }}
          />
        </Group>
      </Paper>

      <Paper withBorder radius="md" p="md">
        <QueryState
          isLoading={isLoading}
          error={error}
          isEmpty={senders.length === 0}
          empty={
            <Stack align="center" gap="xs" c="dimmed">
              <IconMail size={32} />
              <Text size="sm">
                {activeFilters ? (
                  <Trans>No senders match these filters.</Trans>
                ) : (
                  <Trans>No senders yet. Add the first one.</Trans>
                )}
              </Text>
            </Stack>
          }
        >
          <Pager
            limit={LIMIT}
            offset={offset}
            count={senders.length}
            pagination={data?.pagination}
            onChange={setOffset}
          />
          <Table.ScrollContainer minWidth={820}>
            <Table verticalSpacing="sm" highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>
                    <Trans>From</Trans>
                  </Table.Th>
                  <Table.Th>
                    <Trans>Server</Trans>
                  </Table.Th>
                  <Table.Th>
                    <Trans>Security</Trans>
                  </Table.Th>
                  <Table.Th>
                    <Trans>Purposes</Trans>
                  </Table.Th>
                  <Table.Th>
                    <Trans>Priority</Trans>
                  </Table.Th>
                  <Table.Th />
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {senders.map((sender) => {
                  const name = localizedLabel(sender.label);
                  return (
                    <Table.Tr
                      key={sender.id}
                      style={{ cursor: "pointer" }}
                      onClick={() => openEdit(sender)}
                    >
                      <Table.Td>
                        <Stack gap={0}>
                          <Group gap={6}>
                            <Text size="sm" fw={500}>
                              {sender.fromName || sender.fromEmail}
                            </Text>
                            {sender.password && (
                              <Tooltip label={t`Password configured`}>
                                <IconKey
                                  size={13}
                                  style={{ opacity: 0.5 }}
                                  aria-label={t`Password configured`}
                                />
                              </Tooltip>
                            )}
                          </Group>
                          <Text size="xs" c="dimmed">
                            {sender.fromName
                              ? sender.fromEmail
                              : name !== "—"
                                ? name
                                : ""}
                          </Text>
                        </Stack>
                      </Table.Td>
                      <Table.Td>
                        <Text size="sm" ff="monospace">
                          {sender.host}:{sender.port}
                        </Text>
                      </Table.Td>
                      <Table.Td>
                        <Badge variant="light" color="gray">
                          {securityLabel(sender.security)}
                        </Badge>
                      </Table.Td>
                      <Table.Td>
                        {sender.purposes?.length ? (
                          <Group gap={4}>
                            {sender.purposes.map((p) => (
                              <Badge key={p} variant="light" color="cyan">
                                {p}
                              </Badge>
                            ))}
                          </Group>
                        ) : (
                          <Text size="sm" c="dimmed">
                            —
                          </Text>
                        )}
                      </Table.Td>
                      <Table.Td>
                        <Text size="sm">{sender.priority}</Text>
                      </Table.Td>
                      <Table.Td onClick={(e) => e.stopPropagation()}>
                        <Group gap={4} justify="flex-end" wrap="nowrap">
                          <Tooltip label={t`Edit`}>
                            <ActionIcon
                              variant="subtle"
                              onClick={() => openEdit(sender)}
                              aria-label={t`Edit`}
                            >
                              <IconPencil size={16} />
                            </ActionIcon>
                          </Tooltip>
                          <Tooltip label={t`Delete`}>
                            <ActionIcon
                              variant="subtle"
                              color="red"
                              onClick={() => onDelete(sender)}
                              aria-label={t`Delete`}
                            >
                              <IconTrash size={16} />
                            </ActionIcon>
                          </Tooltip>
                        </Group>
                      </Table.Td>
                    </Table.Tr>
                  );
                })}
              </Table.Tbody>
            </Table>
          </Table.ScrollContainer>
        </QueryState>
      </Paper>

      <SenderModal
        opened={modalOpen}
        onClose={() => setModalOpen(false)}
        sender={editing}
      />
    </Stack>
  );
}