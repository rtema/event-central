import { Trans, useLingui } from "@lingui/react/macro";
import {
  Anchor,
  Code,
  Group,
  Paper,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import { IconArrowLeft } from "@tabler/icons-react";
import { Link, useParams } from "react-router";
import { useDocumentTemplate } from "../invoices/invoicingHooks";
import { FieldGrid } from "../ui/FieldGrid";
import { QueryState } from "../ui/QueryState";
import { formatDateTime } from "../utils/datetime";

export function DocumentTemplateDetail() {
  const { t, i18n } = useLingui();
  const { templateId = "" } = useParams();
  const { data: tpl, error, isLoading } = useDocumentTemplate(templateId);

  return (
    <Stack maw={900} mx="auto" w="100%">
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
                    label: t`Fonts`,
                    value: (tpl.fonts ?? []).map((f) => f.name).join(", "),
                  },
                  {
                    label: t`Images`,
                    value: (tpl.images ?? []).map((i) => i.name).join(", "),
                  },
                ]}
              />
            </Paper>

            {tpl.html && (
              <Paper withBorder p="lg" radius="md">
                <Title order={4} mb="sm">
                  <Trans>HTML</Trans>
                </Title>
                <Code block style={{ maxHeight: 360, overflow: "auto" }}>
                  {tpl.html}
                </Code>
              </Paper>
            )}
            {tpl.css && (
              <Paper withBorder p="lg" radius="md">
                <Title order={4} mb="sm">
                  <Trans>CSS</Trans>
                </Title>
                <Code block style={{ maxHeight: 360, overflow: "auto" }}>
                  {tpl.css}
                </Code>
              </Paper>
            )}
            {!tpl.html && !tpl.css && (
              <Text size="sm" c="dimmed">
                <Trans>This template has no inline HTML or CSS.</Trans>
              </Text>
            )}
          </>
        )}
      </QueryState>
    </Stack>
  );
}
