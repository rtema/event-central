import { Trans, useLingui } from "@lingui/react/macro";
import {
  Anchor,
  Code,
  Grid,
  Group,
  Paper,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import { IconArrowLeft } from "@tabler/icons-react";
import { Link, useParams } from "react-router";
import { FieldGrid } from "../ui/FieldGrid";
import { QueryState } from "../ui/QueryState";
import { formatDateTime } from "../utils/datetime";
import {
  useDocumentTemplate,
  useDocumentTemplateFiles,
} from "../../api/hooks";
import { DocumentTemplateFilesTable } from "./DocumentTemplateFilesTable";
import { DocumentTemplatePreview } from "./DocumentTemplatePreview";

export function DocumentTemplateDetail() {
  const { t, i18n } = useLingui();
  const { templateId = "" } = useParams();
  const { data: tpl, error, isLoading } = useDocumentTemplate(templateId);
  const { data: files, isLoading: filesLoading, error: filesError } =
    useDocumentTemplateFiles(templateId);

  const templateFiles = files ?? [];

  return (
    <Stack maw={1280} mx="auto" w="100%">
      <Anchor component={Link} to={`/${i18n.locale}/document-templates`} size="sm">
        <Group gap={4}>
          <IconArrowLeft size={14} />
          <Trans>Back to templates</Trans>
        </Group>
      </Anchor>

      <QueryState isLoading={isLoading} error={error}>
        {tpl && (
          <>
            <Paper withBorder p="lg" radius="md">
              <Title order={2} ff="monospace">
                {tpl.id}
              </Title>
              <FieldGrid
                cols={{ base: 1, sm: 3 }}
                fields={[
                  { label: t`Public ID`, value: tpl.publicDocumentTemplateId },
                  { label: t`Created`, value: formatDateTime(tpl.createdAt) },
                  { label: t`Created by`, value: tpl.createdBy },
                  {
                    label: t`Inline fonts`,
                    value: (tpl.fonts ?? []).map((f) => f.name).join(", "),
                  },
                  {
                    label: t`Inline images`,
                    value: (tpl.images ?? []).map((i) => i.key).join(", "),
                  },
                ]}
              />
            </Paper>

            {/* Code + rendered preview, side by side. */}
            <Grid gutter="md" align="stretch">
              <Grid.Col span={{ base: 12, lg: 6 }}>
                <Stack>
                  {tpl.html && (
                    <Paper withBorder p="lg" radius="md">
                      <Title order={4} mb="sm">
                        <Trans>HTML</Trans>
                      </Title>
                      <Code block style={{ maxHeight: 260, overflow: "auto" }}>
                        {tpl.html}
                      </Code>
                    </Paper>
                  )}
                  {tpl.css && (
                    <Paper withBorder p="lg" radius="md">
                      <Title order={4} mb="sm">
                        <Trans>CSS</Trans>
                      </Title>
                      <Code block style={{ maxHeight: 260, overflow: "auto" }}>
                        {tpl.css}
                      </Code>
                    </Paper>
                  )}
                  {!tpl.html && !tpl.css && (
                    <Paper withBorder p="lg" radius="md">
                      <Text size="sm" c="dimmed">
                        <Trans>This template has no inline HTML or CSS.</Trans>
                      </Text>
                    </Paper>
                  )}
                </Stack>
              </Grid.Col>
              <Grid.Col span={{ base: 12, lg: 6 }}>
                <DocumentTemplatePreview templateId={templateId} />
              </Grid.Col>
            </Grid>

            {/* Files referenced by this template. */}
            <Paper withBorder p="lg" radius="md">
              <Stack gap={0} mb="md">
                <Title order={4}>
                  <Trans>Referenced files</Trans>
                </Title>
                <Text size="sm" c="dimmed">
                  {tpl.publicDocumentTemplateId ? (
                    <Trans>
                      Files this version renders. To change them, edit the
                      public template — rendered versions are immutable.
                    </Trans>
                  ) : (
                    <Trans>
                      Files this version renders, referenced by key in the body.
                    </Trans>
                  )}
                </Text>
              </Stack>

              {tpl.publicDocumentTemplateId && (
                <Anchor
                  component={Link}
                  to={`/${i18n.locale}/document-templates/public/${tpl.publicDocumentTemplateId}`}
                  size="sm"
                >
                  <Trans>Edit public template</Trans>
                </Anchor>
              )}

              <QueryState
                isLoading={filesLoading}
                error={filesError}
                isEmpty={templateFiles.length === 0}
                empty={
                  <Text size="sm" c="dimmed" mt="sm">
                    <Trans>No files attached to this template.</Trans>
                  </Text>
                }
              >
                <DocumentTemplateFilesTable files={templateFiles} />
              </QueryState>
            </Paper>
          </>
        )}
      </QueryState>
    </Stack>
  );
}
