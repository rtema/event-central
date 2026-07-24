import { Trans, useLingui } from "@lingui/react/macro";
import {
  ActionIcon,
  Alert,
  Center,
  Group,
  Loader,
  Paper,
  Stack,
  Text,
  Tooltip,
} from "@mantine/core";
import { IconAlertTriangle, IconRefresh } from "@tabler/icons-react";
import { useCallback, useEffect, useState } from "react";
import { toRequestError } from "../../api/client";
import { emailTemplatesApi } from "../../api/emailTemplates";
import type { EmailTemplatePreview as Preview } from "../../api/types";

interface EmailTemplatePreviewProps {
  templateId: string;
  /** Bump this to force a re-fetch (e.g. after saving the template). */
  refreshKey?: number;
  height?: number;
}

/**
 * Renders the server-side preview of an email template. The `/preview` endpoint
 * fills the template with representative user/event/order/invoice data and
 * returns a resolved subject plus an HTML body, which we sandbox in an iframe.
 */
export function EmailTemplatePreview({
  templateId,
  refreshKey = 0,
  height = 560,
}: EmailTemplatePreviewProps) {
  const { t } = useLingui();
  const [preview, setPreview] = useState<Preview | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!templateId) return;
    setLoading(true);
    setError(null);
    try {
      setPreview(await emailTemplatesApi.preview(templateId));
    } catch (err) {
      setError(toRequestError(err).message);
    } finally {
      setLoading(false);
    }
  }, [templateId]);

  useEffect(() => {
    void load();
  }, [load, refreshKey]);

  return (
    <Paper withBorder radius="md" p="sm" h="100%">
      <Group justify="space-between" mb="xs">
        <Text size="sm" fw={500}>
          <Trans>Preview</Trans>
        </Text>
        <Tooltip label={t`Refresh preview`}>
          <ActionIcon
            variant="subtle"
            loading={loading}
            onClick={() => void load()}
            aria-label={t`Refresh preview`}
          >
            <IconRefresh size={16} />
          </ActionIcon>
        </Tooltip>
      </Group>

      {error ? (
        <Alert
          color="red"
          icon={<IconAlertTriangle size={18} />}
          title={<Trans>Preview unavailable</Trans>}
        >
          <Text size="sm">{error}</Text>
        </Alert>
      ) : loading && !preview ? (
        <Center mih={height}>
          <Stack align="center" gap="xs" c="dimmed">
            <Loader />
            <Text size="sm">
              <Trans>Rendering preview…</Trans>
            </Text>
          </Stack>
        </Center>
      ) : preview ? (
        <Stack gap="xs">
          <Stack gap={2}>
            <Text size="xs" tt="uppercase" fw={600} c="dimmed">
              <Trans>Subject</Trans>
            </Text>
            <Text size="sm" fw={500}>
              {preview.subject || "—"}
            </Text>
          </Stack>
          <iframe
            title={t`Email preview`}
            srcDoc={preview.body}
            sandbox=""
            style={{
              width: "100%",
              height,
              border: "1px solid var(--mantine-color-default-border)",
              borderRadius: 8,
              background: "#ffffff",
            }}
          />
        </Stack>
      ) : null}
    </Paper>
  );
}
