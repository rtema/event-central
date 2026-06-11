import { Trans, useLingui } from "@lingui/react/macro";
import {
  ActionIcon,
  Alert,
  Badge,
  Box,
  Button,
  Code,
  CopyButton,
  Group,
  Modal,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
  Tooltip,
} from "@mantine/core";
import { useForm } from "@mantine/form";
import { modals } from "@mantine/modals";
import { notifications } from "@mantine/notifications";
import {
  IconCheck,
  IconCopy,
  IconKey,
  IconPlus,
  IconTrash,
} from "@tabler/icons-react";
import { useState } from "react";
import { toRequestError } from "../../api/client";
import type { UserAuth, UserAuthMethod } from "../../api/types";
import { usersApi } from "../../api/users";
import { QueryState } from "../ui/QueryState";
import { formatDateTime } from "../utils/datetime";
import { useUserAuth } from "./userHooks";

const METHOD_LABELS: Record<UserAuthMethod, string> = {
  "api-token": "API token",
  password: "Password",
  "backup-code": "Backup code",
  passwordless: "Passwordless",
  otp: "One-time password (OTP)",
};

/** Methods whose secret is shown exactly once after creation. */
const ONE_TIME_SECRET: UserAuthMethod[] = ["api-token", "backup-code", "otp"];

export function UserAuthMethodsTab({ userId }: { userId: string }) {
  const { t } = useLingui();
  const { data, error, isLoading, mutate } = useUserAuth(userId);
  const [createOpen, setCreateOpen] = useState(false);
  const [revealed, setRevealed] = useState<UserAuth | null>(null);
  const [busy, setBusy] = useState(false);

  const form = useForm<{ method: UserAuthMethod; secret: string }>({
    initialValues: { method: "api-token", secret: "" },
    validate: {
      secret: (v, values) =>
        values.method === "password" && v.length < 8
          ? t`Use at least 8 characters`
          : values.method === "passwordless" && v.trim().length === 0
            ? t`Enter an email or phone number`
            : null,
    },
  });

  const needsSecret =
    form.values.method === "password" || form.values.method === "passwordless";

  const onCreate = async () => {
    if (form.validate().hasErrors) return;
    setBusy(true);
    try {
      const created = await usersApi.createAuth(userId, {
        method: form.values.method,
        secret: needsSecret ? form.values.secret : undefined,
      });
      await mutate();
      setCreateOpen(false);
      form.reset();
      if (created.secret && ONE_TIME_SECRET.includes(created.method)) {
        setRevealed(created);
      } else {
        notifications.show({
          color: "pine",
          title: t`Auth method added`,
          message: METHOD_LABELS[created.method],
        });
      }
    } catch (err) {
      notifications.show({
        color: "red",
        title: t`Could not add auth method`,
        message: toRequestError(err).message,
      });
    } finally {
      setBusy(false);
    }
  };

  const onDelete = (item: UserAuth) =>
    modals.openConfirmModal({
      title: t`Disable auth method`,
      children: (
        <Text size="sm">
          <Trans>
            This disables the {METHOD_LABELS[item.method]} method. Auth methods
            cannot be edited — disabling keeps the history intact.
          </Trans>
        </Text>
      ),
      labels: { confirm: t`Disable`, cancel: t`Cancel` },
      confirmProps: { color: "red" },
      onConfirm: async () => {
        try {
          await usersApi.deleteAuth(userId, item.id);
          await mutate();
          notifications.show({
            color: "pine",
            title: t`Disabled`,
            message: METHOD_LABELS[item.method],
          });
        } catch (err) {
          notifications.show({
            color: "red",
            title: t`Could not disable`,
            message: toRequestError(err).message,
          });
        }
      },
    });

  const methods = data ?? [];

  return (
    <Stack>
      <Group justify="space-between">
        <Text size="sm" c="dimmed">
          <Trans>Sign-in methods configured for this user.</Trans>
        </Text>
        <Button
          size="xs"
          leftSection={<IconPlus size={14} />}
          onClick={() => setCreateOpen(true)}
        >
          <Trans>Add method</Trans>
        </Button>
      </Group>

      <QueryState
        isLoading={isLoading}
        error={error}
        isEmpty={methods.length === 0}
      >
        <Table.ScrollContainer minWidth={620}>
          <Table verticalSpacing="sm">
            <Table.Thead>
              <Table.Tr>
                <Table.Th>
                  <Trans>Method</Trans>
                </Table.Th>
                <Table.Th>
                  <Trans>Status</Trans>
                </Table.Th>
                <Table.Th>
                  <Trans>Created</Trans>
                </Table.Th>
                <Table.Th>
                  <Trans>Detail</Trans>
                </Table.Th>
                <Table.Th />
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {methods.map((m) => {
                const active = !m.deletedAt;
                return (
                  <Table.Tr key={m.id}>
                    <Table.Td>
                      <Group gap="xs">
                        <IconKey size={16} opacity={0.6} />
                        <Text size="sm" fw={500}>
                          {METHOD_LABELS[m.method]}
                        </Text>
                      </Group>
                    </Table.Td>
                    <Table.Td>
                      {active ? (
                        <Badge color="pine" variant="light">
                          <Trans>Active</Trans>
                        </Badge>
                      ) : (
                        <Badge color="gray" variant="light">
                          <Trans>Disabled</Trans>
                        </Badge>
                      )}
                    </Table.Td>
                    <Table.Td>
                      <Text size="sm">{formatDateTime(m.createdAt)}</Text>
                      {m.createdReason && (
                        <Text size="xs" c="dimmed">
                          {m.createdReason}
                        </Text>
                      )}
                    </Table.Td>
                    <Table.Td>
                      {/* Only passwordless exposes a readable secret (email/phone). */}
                      {m.method === "passwordless" && m.secret ? (
                        <Text size="sm">{m.secret}</Text>
                      ) : (
                        <Text size="sm" c="dimmed">
                          —
                        </Text>
                      )}
                    </Table.Td>
                    <Table.Td>
                      <Group justify="flex-end">
                        {active && (
                          <Tooltip label={t`Disable`}>
                            <ActionIcon
                              color="red"
                              variant="subtle"
                              onClick={() => onDelete(m)}
                              aria-label={t`Disable`}
                            >
                              <IconTrash size={16} />
                            </ActionIcon>
                          </Tooltip>
                        )}
                      </Group>
                    </Table.Td>
                  </Table.Tr>
                );
              })}
            </Table.Tbody>
          </Table>
        </Table.ScrollContainer>
      </QueryState>

      <Modal
        opened={createOpen}
        onClose={() => setCreateOpen(false)}
        title={t`Add auth method`}
        centered
      >
        <Stack>
          <Select
            label={t`Method`}
            allowDeselect={false}
            data={(Object.keys(METHOD_LABELS) as UserAuthMethod[]).map((m) => ({
              value: m,
              label: METHOD_LABELS[m],
            }))}
            value={form.values.method}
            onChange={(v) =>
              v && form.setFieldValue("method", v as UserAuthMethod)
            }
          />
          {needsSecret && (
            <TextInput
              label={
                form.values.method === "password"
                  ? t`Password`
                  : t`Email or phone number`
              }
              type={form.values.method === "password" ? "password" : "text"}
              {...form.getInputProps("secret")}
            />
          )}
          {ONE_TIME_SECRET.includes(form.values.method) && (
            <Text size="xs" c="dimmed">
              <Trans>
                A secret will be generated and shown once after creation.
              </Trans>
            </Text>
          )}
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setCreateOpen(false)}>
              <Trans>Cancel</Trans>
            </Button>
            <Button loading={busy} onClick={() => void onCreate()}>
              <Trans>Create</Trans>
            </Button>
          </Group>
        </Stack>
      </Modal>

      <Modal
        opened={Boolean(revealed)}
        onClose={() => setRevealed(null)}
        title={t`Copy this secret now`}
        centered
      >
        <Stack>
          <Alert color="yellow">
            <Trans>
              This value is shown only once and cannot be retrieved later.
            </Trans>
          </Alert>
          <Box>
            <Text size="xs" c="dimmed" mb={4}>
              {revealed && METHOD_LABELS[revealed.method]}
            </Text>
            <Group gap="xs" wrap="nowrap">
              <Code block style={{ flex: 1, wordBreak: "break-all" }}>
                {revealed?.secret}
              </Code>
              <CopyButton value={revealed?.secret ?? ""}>
                {({ copied, copy }) => (
                  <Tooltip label={copied ? t`Copied` : t`Copy`}>
                    <ActionIcon
                      variant="light"
                      color={copied ? "pine" : "gray"}
                      onClick={copy}
                      aria-label={t`Copy`}
                    >
                      {copied ? (
                        <IconCheck size={16} />
                      ) : (
                        <IconCopy size={16} />
                      )}
                    </ActionIcon>
                  </Tooltip>
                )}
              </CopyButton>
            </Group>
          </Box>
          <Group justify="flex-end">
            <Button onClick={() => setRevealed(null)}>
              <Trans>Done</Trans>
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Stack>
  );
}
