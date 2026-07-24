import { Trans, useLingui } from "@lingui/react/macro";
import {
  Badge,
  Button,
  Group,
  Modal,
  Paper,
  Stack,
  Table,
  Text,
  Title,
} from "@mantine/core";
import { useForm } from "@mantine/form";
import { notifications } from "@mantine/notifications";
import { IconMailForward, IconPlus } from "@tabler/icons-react";
import { useState } from "react";
import { useNavigate } from "react-router";
import { toRequestError } from "../../api/client";
import { emailTemplatesApi } from "../../api/emailTemplates";
import { useEmailTemplateMutations, useEmailTemplates } from "../../api/hooks";
import { Pager } from "../ui/Pager";
import { QueryState } from "../ui/QueryState";
import { formatDateTime } from "../utils/datetime";
import { localizedLabel } from "../utils/format";
import {
  EmailTemplateForm,
  emptyTemplateValues,
  templateToPayload,
  type TemplateFormValues,
} from "./EmailTemplateForm";

const LIMIT = 100;

function CreateTemplateModal({
  opened,
  onClose,
}: {
  opened: boolean;
  onClose: () => void;
}) {
  const { t, i18n } = useLingui();
  const navigate = useNavigate();
  const { revalidateTemplate } = useEmailTemplateMutations();
  const [saving, setSaving] = useState(false);
  const [htmlError, setHtmlError] = useState<string | null>(null);

  const form = useForm<TemplateFormValues>({
    initialValues: emptyTemplateValues(),
    validate: {
      subject: (v) => (v.trim() ? null : t`Subject is required`),
      previewText: (v) => (v.trim() ? null : t`Preview text is required`),
      html: (v) => (v.trim() ? null : t`HTML body is required`),
    },
  });

  const onSubmit = async () => {
    if (form.validate().hasErrors || htmlError) return;
    setSaving(true);
    try {
      const created = await emailTemplatesApi.create(
        templateToPayload(form.values),
      );
      revalidateTemplate();
      notifications.show({
        color: "pine",
        title: t`Template created`,
        message: localizedLabel(created.label),
      });
      form.reset();
      onClose();
      navigate(`/${i18n.locale}/email-templates/${created.id}`);
    } catch (err) {
      notifications.show({
        color: "red",
        title: t`Could not create template`,
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
      title={t`New email template`}
      size="xl"
    >
      <Stack>
        <EmailTemplateForm form={form} onHtmlValidityChange={setHtmlError} />
        <Group justify="flex-end" mt="sm">
          <Button variant="default" onClick={onClose}>
            <Trans>Cancel</Trans>
          </Button>
          <Button loading={saving} onClick={() => void onSubmit()}>
            <Trans>Create template</Trans>
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}

export function EmailTemplatesList() {
  const { i18n } = useLingui();
  const navigate = useNavigate();
  const [offset, setOffset] = useState(0);
  const [createOpen, setCreateOpen] = useState(false);
  const { data, error, isLoading } = useEmailTemplates({
    limit: LIMIT,
    offset: String(offset),
  });
  const templates = data?.data ?? [];

  return (
    <Stack>
      <Group justify="space-between" align="flex-end">
        <Stack gap={2}>
          <Title order={1}>
            <Trans>Email templates</Trans>
          </Title>
          <Text size="sm" c="dimmed">
            <Trans>
              The subject and HTML used to compose each kind of email. Saving
              keeps a full version history.
            </Trans>
          </Text>
        </Stack>
        <Button
          leftSection={<IconPlus size={16} />}
          onClick={() => setCreateOpen(true)}
        >
          <Trans>New template</Trans>
        </Button>
      </Group>

      <Paper withBorder radius="md" p="md">
        <QueryState
          isLoading={isLoading}
          error={error}
          isEmpty={templates.length === 0}
          empty={
            <Stack align="center" gap="xs" c="dimmed">
              <IconMailForward size={32} />
              <Text size="sm">
                <Trans>No templates yet. Create the first one.</Trans>
              </Text>
            </Stack>
          }
        >
          <Pager
            limit={LIMIT}
            offset={offset}
            count={templates.length}
            pagination={data?.pagination}
            onChange={setOffset}
          />
          <Table.ScrollContainer minWidth={780}>
            <Table verticalSpacing="sm" highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>
                    <Trans>Name</Trans>
                  </Table.Th>
                  <Table.Th>
                    <Trans>Subject</Trans>
                  </Table.Th>
                  <Table.Th>
                    <Trans>Locale</Trans>
                  </Table.Th>
                  <Table.Th>
                    <Trans>Purposes</Trans>
                  </Table.Th>
                  <Table.Th>
                    <Trans>Updated</Trans>
                  </Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {templates.map((tpl) => (
                  <Table.Tr
                    key={tpl.id}
                    style={{ cursor: "pointer" }}
                    onClick={() =>
                      navigate(`/${i18n.locale}/email-templates/${tpl.id}`)
                    }
                  >
                    <Table.Td>
                      <Text size="sm" fw={500}>
                        {localizedLabel(tpl.label)}
                      </Text>
                    </Table.Td>
                    <Table.Td>
                      <Text size="sm" truncate maw={280}>
                        {tpl.subject || "—"}
                      </Text>
                    </Table.Td>
                    <Table.Td>
                      <Badge variant="light" color="gray">
                        {tpl.locale?.toUpperCase()}
                      </Badge>
                    </Table.Td>
                    <Table.Td>
                      {tpl.purposes?.length ? (
                        <Group gap={4}>
                          {tpl.purposes.map((p) => (
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
                      <Text size="sm">{formatDateTime(tpl.updatedAt)}</Text>
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Table.ScrollContainer>
        </QueryState>
      </Paper>

      <CreateTemplateModal
        opened={createOpen}
        onClose={() => setCreateOpen(false)}
      />
    </Stack>
  );
}
