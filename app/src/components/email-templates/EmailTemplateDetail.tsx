import { Trans, useLingui } from "@lingui/react/macro";
import {
  Anchor,
  Badge,
  Button,
  Grid,
  Group,
  Paper,
  Stack,
  Table,
  Text,
  Title,
} from "@mantine/core";
import { useForm } from "@mantine/form";
import { modals } from "@mantine/modals";
import { notifications } from "@mantine/notifications";
import {
  IconArrowLeft,
  IconDeviceFloppy,
  IconHistory,
  IconTrash,
} from "@tabler/icons-react";
import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router";
import { toRequestError } from "../../api/client";
import { emailTemplatesApi } from "../../api/emailTemplates";
import {
  useEmailTemplate,
  useEmailTemplateFiles,
  useEmailTemplateMutations,
  useEmailTemplateVersions,
} from "../../api/hooks";
import { FieldGrid } from "../ui/FieldGrid";
import { QueryState } from "../ui/QueryState";
import { formatDateTime } from "../utils/datetime";
import { localizedLabel } from "../utils/format";
import { EmailTemplateFilesTable } from "./EmailTemplateFilesTable";
import {
  EmailTemplateForm,
  templateToPayload,
  valuesFromTemplate,
  type TemplateFormValues,
} from "./EmailTemplateForm";
import { EmailTemplatePreview } from "./EmailTemplatePreview";

export function EmailTemplateDetail() {
  const { t, i18n } = useLingui();
  const navigate = useNavigate();
  const { templateId = "" } = useParams();
  const { data: tpl, error, isLoading } = useEmailTemplate(templateId);
  const { data: files, isLoading: filesLoading, error: filesError } =
    useEmailTemplateFiles(templateId);
  const { data: versions } = useEmailTemplateVersions(templateId);
  const { revalidateTemplate } = useEmailTemplateMutations(templateId);

  const [saving, setSaving] = useState(false);
  const [htmlError, setHtmlError] = useState<string | null>(null);
  const [previewKey, setPreviewKey] = useState(0);

  const form = useForm<TemplateFormValues>({
    initialValues: tpl
      ? valuesFromTemplate(tpl)
      : {
          locale: "de",
          labelDe: "",
          labelEn: "",
          subject: "",
          previewText: "",
          html: "",
          purposes: [],
          priority: 0,
        },
  });

  useEffect(() => {
    if (!tpl) return;
    form.setValues(valuesFromTemplate(tpl));
    form.resetDirty();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tpl?.id, tpl?.updatedAt]);

  const onSave = async () => {
    if (htmlError) return;
    setSaving(true);
    try {
      await emailTemplatesApi.update(templateId, templateToPayload(form.values));
      revalidateTemplate();
      setPreviewKey((k) => k + 1);
      notifications.show({
        color: "pine",
        title: t`Template saved`,
        message: localizedLabel(tpl?.label),
      });
    } catch (err) {
      notifications.show({
        color: "red",
        title: t`Could not save template`,
        message: toRequestError(err).message,
      });
    } finally {
      setSaving(false);
    }
  };

  const onDelete = () =>
    modals.openConfirmModal({
      title: t`Delete template`,
      children: (
        <Text size="sm">
          <Trans>
            Delete this template? Emails already sent are unaffected, but it can
            no longer be used to compose new mail.
          </Trans>
        </Text>
      ),
      labels: { confirm: t`Delete`, cancel: t`Cancel` },
      confirmProps: { color: "red" },
      onConfirm: async () => {
        try {
          await emailTemplatesApi.remove(templateId);
          revalidateTemplate();
          notifications.show({
            color: "pine",
            title: t`Template deleted`,
            message: localizedLabel(tpl?.label),
          });
          navigate(`/${i18n.locale}/email-templates`);
        } catch (err) {
          notifications.show({
            color: "red",
            title: t`Could not delete`,
            message: toRequestError(err).message,
          });
        }
      },
    });

  const templateFiles = files ?? [];
  const versionList = versions ?? [];

  return (
    <Stack maw={1320} mx="auto" w="100%">
      <Anchor
        component={Link}
        to={`/${i18n.locale}/email-templates`}
        size="sm"
      >
        <Group gap={4}>
          <IconArrowLeft size={14} />
          <Trans>Back to templates</Trans>
        </Group>
      </Anchor>

      <QueryState isLoading={isLoading} error={error}>
        {tpl && (
          <>
            <Paper withBorder p="lg" radius="md">
              <Group justify="space-between" align="flex-start">
                <Stack gap={4}>
                  <Title order={2}>{localizedLabel(tpl.label)}</Title>
                  <Group gap="xs">
                    <Badge variant="light" color="gray">
                      {tpl.locale?.toUpperCase()}
                    </Badge>
                    {tpl.purposes?.map((p) => (
                      <Badge key={p} variant="light" color="cyan">
                        {p}
                      </Badge>
                    ))}
                  </Group>
                </Stack>
                <Button
                  variant="light"
                  color="red"
                  leftSection={<IconTrash size={16} />}
                  onClick={onDelete}
                >
                  <Trans>Delete</Trans>
                </Button>
              </Group>
              <FieldGrid
                cols={{ base: 1, sm: 3 }}
                fields={[
                  { label: t`Priority`, value: String(tpl.priority) },
                  { label: t`Created`, value: formatDateTime(tpl.createdAt) },
                  { label: t`Updated`, value: formatDateTime(tpl.updatedAt) },
                ]}
              />
            </Paper>

            <Grid gutter="md" align="stretch">
              <Grid.Col span={{ base: 12, lg: 7 }}>
                <Paper withBorder p="lg" radius="md">
                  <EmailTemplateForm
                    form={form}
                    onHtmlValidityChange={setHtmlError}
                  />
                  <Group justify="flex-end" mt="lg">
                    <Button
                      leftSection={<IconDeviceFloppy size={16} />}
                      loading={saving}
                      onClick={() => void onSave()}
                    >
                      <Trans>Save template</Trans>
                    </Button>
                  </Group>
                </Paper>
              </Grid.Col>
              <Grid.Col span={{ base: 12, lg: 5 }}>
                <EmailTemplatePreview
                  templateId={templateId}
                  refreshKey={previewKey}
                />
              </Grid.Col>
            </Grid>

            <Paper withBorder p="lg" radius="md">
              <Title order={4} mb="md">
                <Trans>Attached files</Trans>
              </Title>
              <QueryState isLoading={filesLoading} error={filesError}>
                <EmailTemplateFilesTable
                  templateId={templateId}
                  files={templateFiles}
                />
              </QueryState>
            </Paper>

            <Paper withBorder p="lg" radius="md">
              <Group gap="xs" mb="md">
                <IconHistory size={18} />
                <Title order={4}>
                  <Trans>Version history</Trans>
                </Title>
              </Group>
              {versionList.length === 0 ? (
                <Text size="sm" c="dimmed">
                  <Trans>No saved versions yet.</Trans>
                </Text>
              ) : (
                <Table.ScrollContainer minWidth={620}>
                  <Table verticalSpacing="sm">
                    <Table.Thead>
                      <Table.Tr>
                        <Table.Th>
                          <Trans>Saved</Trans>
                        </Table.Th>
                        <Table.Th>
                          <Trans>Subject</Trans>
                        </Table.Th>
                        <Table.Th>
                          <Trans>Locale</Trans>
                        </Table.Th>
                        <Table.Th>
                          <Trans>By</Trans>
                        </Table.Th>
                      </Table.Tr>
                    </Table.Thead>
                    <Table.Tbody>
                      {versionList.map((v) => (
                        <Table.Tr key={v.id}>
                          <Table.Td>
                            <Text size="sm">{formatDateTime(v.createdAt)}</Text>
                          </Table.Td>
                          <Table.Td>
                            <Text size="sm" truncate maw={320}>
                              {v.subject}
                            </Text>
                          </Table.Td>
                          <Table.Td>
                            <Badge variant="light" color="gray">
                              {v.locale?.toUpperCase()}
                            </Badge>
                          </Table.Td>
                          <Table.Td>
                            <Text size="xs" c="dimmed" ff="monospace">
                              {v.createdBy ?? "—"}
                            </Text>
                          </Table.Td>
                        </Table.Tr>
                      ))}
                    </Table.Tbody>
                  </Table>
                </Table.ScrollContainer>
              )}
            </Paper>
          </>
        )}
      </QueryState>
    </Stack>
  );
}
