import { Trans, useLingui } from "@lingui/react/macro";
import {
  Alert,
  Button,
  Group,
  Stack,
  Text,
  Textarea,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconDeviceFloppy, IconInfoCircle } from "@tabler/icons-react";
import { useEffect, useMemo, useState } from "react";
import { toRequestError } from "../../../api/client";
import { usersApi } from "../../../api/users";
import { useUserData } from "../../users/userHooks";
import { formatDateTime } from "../../utils/datetime";

function pretty(value: unknown): string {
  try {
    return JSON.stringify(value ?? {}, null, 2);
  } catch {
    return "{}";
  }
}

export function DataTab({
  userId,
  disabled,
}: {
  userId: string;
  disabled?: boolean;
}) {
  const { t } = useLingui();
  const { data, error, isLoading, mutate } = useUserData(userId);

  const requestError = error ? toRequestError(error) : null;
  const notFound = requestError?.status === 404;
  const realError = requestError && !notFound ? requestError : null;

  const initial = useMemo(() => pretty(data?.data ?? {}), [data]);
  const [text, setText] = useState(initial);
  const [jsonError, setJsonError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setText(initial);
    setJsonError(null);
  }, [initial]);

  const onSave = async () => {
    let parsed: Record<string, unknown>;
    try {
      parsed = JSON.parse(text || "{}");
    } catch {
      setJsonError(t`Invalid JSON — please fix the syntax.`);
      return;
    }
    if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
      setJsonError(t`The top level must be a JSON object.`);
      return;
    }
    setJsonError(null);
    setSaving(true);
    try {
      await usersApi.setData(userId, parsed);
      await mutate();
      notifications.show({
        color: "pine",
        title: t`Data saved`,
        message: t`User data has been replaced.`,
      });
    } catch (err) {
      notifications.show({
        color: "red",
        title: t`Could not save data`,
        message: toRequestError(err).message,
      });
    } finally {
      setSaving(false);
    }
  };

  if (realError) {
    return (
      <Alert color="red" icon={<IconInfoCircle size={18} />}>
        {realError.message}
      </Alert>
    );
  }

  return (
    <Stack maw={720}>
      <Group justify="space-between" align="flex-end">
        <Text size="sm" c="dimmed">
          <Trans>
            Schemaless data used by apps. Saving replaces the whole object — no
            server-side merge is performed.
          </Trans>
        </Text>
        {data && !notFound && (
          <Text size="xs" c="dimmed">
            <Trans>Updated</Trans> {formatDateTime(data.createdAt)}
            {data.changedBy ? ` · ${data.changedBy}` : ""}
          </Text>
        )}
      </Group>

      {notFound && (
        <Alert color="gray" icon={<IconInfoCircle size={18} />}>
          <Trans>No data has been stored for this user yet.</Trans>
        </Alert>
      )}

      <Textarea
        autosize
        minRows={10}
        maxRows={24}
        spellCheck={false}
        disabled={disabled || isLoading}
        styles={{ input: { fontFamily: "var(--mantine-font-family-monospace)" } }}
        value={text}
        error={jsonError}
        onChange={(e) => setText(e.currentTarget.value)}
      />

      <Group justify="flex-end">
        <Button
          leftSection={<IconDeviceFloppy size={16} />}
          loading={saving}
          disabled={disabled}
          onClick={() => void onSave()}
        >
          <Trans>Save data</Trans>
        </Button>
      </Group>
    </Stack>
  );
}
