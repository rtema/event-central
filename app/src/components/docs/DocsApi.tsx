import { Trans, useLingui } from "@lingui/react/macro";
import {
  Button,
  Group,
  Loader,
  Paper,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import { IconApi, IconDownload, IconRefresh } from "@tabler/icons-react";
import { lazy, Suspense } from "react";
import { useDocsApiSpec } from "../../api/hooks";
import { QueryState } from "../ui/QueryState";

// Heavy dependency: only loaded once this route is opened.
const DocsSwaggerView = lazy(() => import("./DocsSwaggerView"));

function specInfo(spec: Record<string, unknown> | undefined) {
  const info = (spec?.info ?? {}) as { title?: string; version?: string };
  return { title: info.title, version: info.version };
}

export function DocsApi() {
  const { t } = useLingui();
  const { data, error, isLoading, isValidating, mutate } = useDocsApiSpec();
  const { title, version } = specInfo(data?.spec);

  const handleDownload = () => {
    if (!data?.raw) return;
    const blob = new Blob([data.raw], { type: "application/yaml" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "api-spec.yaml";
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <Stack>
      <Group justify="space-between" align="flex-end" wrap="nowrap">
        <Stack gap={2}>
          <Title order={1}>
            <Trans>API documentation</Trans>
          </Title>
          <Text size="sm" c="dimmed">
            {title ? (
              `${title}${version ? ` · v${version}` : ""}`
            ) : (
              <Trans>The Event Central OpenAPI specification.</Trans>
            )}
          </Text>
        </Stack>

        <Group gap="xs">
          <Button
            variant="default"
            size="sm"
            leftSection={<IconRefresh size={16} />}
            loading={isValidating}
            onClick={() => void mutate()}
          >
            <Trans>Refresh</Trans>
          </Button>
          <Button
            variant="light"
            size="sm"
            leftSection={<IconDownload size={16} />}
            disabled={!data?.raw}
            onClick={handleDownload}
          >
            <Trans>Download YAML</Trans>
          </Button>
        </Group>
      </Group>

      <Paper withBorder radius="md" p="xs">
        <QueryState
          isLoading={isLoading}
          error={error}
          isEmpty={!data?.spec}
          empty={
            <Stack align="center" gap="xs" c="dimmed">
              <IconApi size={32} />
              <Text size="sm">
                <Trans>No specification available.</Trans>
              </Text>
            </Stack>
          }
        >
          <Suspense
            fallback={
              <Group justify="center" py="xl">
                <Loader />
                <Text size="sm" c="dimmed">
                  {t`Loading viewer…`}
                </Text>
              </Group>
            }
          >
            {data?.spec && <DocsSwaggerView spec={data.spec} />}
          </Suspense>
        </QueryState>
      </Paper>
    </Stack>
  );
}