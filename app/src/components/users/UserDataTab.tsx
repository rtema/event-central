import { Trans, useLingui } from "@lingui/react/macro";
import {
  Alert,
  Button,
  Group,
  Stack,
  Text,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconDeviceFloppy, IconInfoCircle } from "@tabler/icons-react";
import { useEffect, useMemo, useState } from "react";
import { toRequestError } from "../../api/client";
import { usersApi } from "../../api/users";
import { CodeEditor } from "../ui/CodeEditor";
import { formatDateTime } from "../utils/datetime";
import { useUserData } from "./userHooks";

function pretty(value: unknown): string {
  try {
    return JSON.stringify(value ?? {}, null, 2);
  } catch {
    return "{}";
  }
}

export function UserDataTab({
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
  // syntaxError comes live from the editor; semanticError is the "must be an
  // object" rule enforced on save.
  const [syntaxError, setSyntaxError] = useState<string | null>(null);
  const [semanticError, setSemanticError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setText(initial);
    setSemanticError(null);
  }, [initial]);

  const onSave = async () => {
    let parsed: Record<string, unknown>;
    try {
      parsed = JSON.parse(text || "{}");
    } catch {
      // The editor already shows the precise syntax error inline.
      return;
    }
    if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
      setSemanticError(t`The top level must be a JSON object.`);
      return;
    }
    setSemanticError(null);
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

      <CodeEditor
        language="json"
        value={text}
        onChange={(v) => {
          setText(v);
          if (semanticError) setSemanticError(null);
        }}
        onValidityChange={setSyntaxError}
        error={semanticError}
        minRows={10}
        maxRows={24}
        disabled={disabled || isLoading}
      />

      <Group justify="flex-end">
        <Button
          leftSection={<IconDeviceFloppy size={16} />}
          loading={saving}
          disabled={disabled || Boolean(syntaxError)}
          onClick={() => void onSave()}
        >
          <Trans>Save data</Trans>
        </Button>
      </Group>
    </Stack>
  );
}
