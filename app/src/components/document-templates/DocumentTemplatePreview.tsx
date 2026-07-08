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
import {
  IconAlertTriangle,
  IconExternalLink,
  IconRefresh,
} from "@tabler/icons-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { toRequestError } from "../../api/client";
import { documentTemplatesApi } from "../../api/documentTemplates";

interface DocumentTemplatePreviewProps {
  templateId: string;
  /** Height of the embedded PDF viewport. */
  height?: number;
}

/**
 * Renders the server-side PDF preview of a template (`/preview`) and keeps the
 * object URL alive for the lifetime of the component, revoking it on unmount or
 * refresh. Used alongside the HTML/CSS editor so authors see code and output
 * side by side.
 */
export function DocumentTemplatePreview({ templateId, height = 620 }: DocumentTemplatePreviewProps) {
  const { t } = useLingui();
  const [url, setUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const urlRef = useRef<string | null>(null);

  const revoke = () => {
    if (urlRef.current) {
      URL.revokeObjectURL(urlRef.current);
      urlRef.current = null;
    }
  };

  const load = useCallback(async () => {
    if (!templateId) return;
    setLoading(true);
    setError(null);
    try {
      const next = await documentTemplatesApi.preview(templateId);
      revoke();
      urlRef.current = next;
      setUrl(next);
    } catch (err) {
      setError(toRequestError(err).message);
    } finally {
      setLoading(false);
    }
  }, [templateId]);

  useEffect(() => {
    void load();
    return revoke;
  }, [load]);

  return (
    <Paper withBorder radius="md" p="sm" h="100%">
      <Group justify="space-between" mb="xs">
        <Text size="sm" fw={500}>
          <Trans>Preview</Trans>
        </Text>
        <Group gap="xs">
          <Tooltip label={t`Open in new tab`}>
            <ActionIcon
              variant="subtle"
              disabled={!url}
              onClick={() => url && window.open(url, "_blank", "noopener")}
              aria-label={t`Open in new tab`}
            >
              <IconExternalLink size={16} />
            </ActionIcon>
          </Tooltip>
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
      </Group>

      {error ? (
        <Alert
          color="red"
          icon={<IconAlertTriangle size={18} />}
          title={<Trans>Preview unavailable</Trans>}
        >
          <Text size="sm">{error}</Text>
        </Alert>
      ) : loading && !url ? (
        <Center mih={height}>
          <Stack align="center" gap="xs" c="dimmed">
            <Loader />
            <Text size="sm">
              <Trans>Rendering preview…</Trans>
            </Text>
          </Stack>
        </Center>
      ) : url ? (
        <iframe
          title={t`Template preview`}
          src={url}
          style={{
            width: "100%",
            height,
            border: 0,
            borderRadius: 8,
            background: "var(--mantine-color-body)",
          }}
        />
      ) : null}
    </Paper>
  );
}
