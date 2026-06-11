import { Trans, useLingui } from "@lingui/react/macro";
import {
  Button,
  Group,
  Modal,
  Paper,
  Stack,
  Table,
  Tabs,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { useForm } from "@mantine/form";
import { notifications } from "@mantine/notifications";
import {
  IconFileCode,
  IconPlus,
  IconTemplate,
} from "@tabler/icons-react";
import { useState } from "react";
import { useNavigate } from "react-router";
import { useSWRConfig } from "swr";
import { toRequestError } from "../../api/client";
import { templatesApi } from "../../api/templates";
import {
  assetsToPayload,
  TemplateAssetsFields,
  type TemplateAssetsValues,
} from "../invoices/TemplateAssetsFields";
import {
  invKeys,
  useDocumentTemplates,
  usePublicTemplates,
} from "../invoices/invoicingHooks";
import { QueryState } from "../ui/QueryState";
import { formatDateTime } from "../utils/datetime";
import { localizedLabel } from "../utils/format";

interface CreateValues extends TemplateAssetsValues {
  id: string;
}

function CreatePublicTemplateModal({
  opened,
  onClose,
}: {
  opened: boolean;
  onClose: () => void;
}) {
  const { t } = useLingui();
  const { mutate } = useSWRConfig();
  const [saving, setSaving] = useState(false);

  const form = useForm<CreateValues>({
    initialValues: { id: "", html: "", css: "", images: [], fonts: [] },
    validate: {
      id: (v) =>
        /^[a-z0-9_-]+$/.test(v)
          ? null
          : t`Use lowercase letters, numbers, '-' and '_' only`,
    },
  });

  const onSubmit = async () => {
    if (form.validate().hasErrors) return;
    setSaving(true);
    try {
      const created = await templatesApi.createPublic({
        id: form.values.id,
        ...assetsToPayload(form.values),
      });
      void mutate(invKeys.publicTemplates());
      notifications.show({
        color: "pine",
        title: t`Template created`,
        message: created.id,
      });
      form.reset();
      onClose();
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
      title={t`New public template`}
      size="xl"
    >
      <Stack>
        <TextInput
          label={t`Template ID`}
          withAsterisk
          description={t`Referenced when generating invoices by template.`}
          placeholder="invoice-default"
          {...form.getInputProps("id")}
        />
        <TemplateAssetsFields form={form} />
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

function PublicTemplatesTab() {
  const { i18n } = useLingui();
  const navigate = useNavigate();
  const { data, error, isLoading } = usePublicTemplates();
  const [createOpen, setCreateOpen] = useState(false);
  const templates = data ?? [];

  return (
    <Paper withBorder p="lg" radius="md">
      <Group justify="space-between" mb="md">
        <Text size="sm" c="dimmed">
          <Trans>
            Public templates can be referenced by ID when creating invoices.
          </Trans>
        </Text>
        <Button
          size="xs"
          leftSection={<IconPlus size={14} />}
          onClick={() => setCreateOpen(true)}
        >
          <Trans>New template</Trans>
        </Button>
      </Group>

      <QueryState
        isLoading={isLoading}
        error={error}
        isEmpty={templates.length === 0}
        empty={
          <Stack align="center" gap="xs" c="dimmed">
            <IconTemplate size={32} />
            <Text size="sm">
              <Trans>No public templates yet.</Trans>
            </Text>
          </Stack>
        }
      >
        <Table verticalSpacing="sm" highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>
                <Trans>ID</Trans>
              </Table.Th>
              <Table.Th>
                <Trans>Label</Trans>
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
                onClick={() => navigate(`/${i18n.locale}/document-templates/public/${tpl.id}`)}
              >
                <Table.Td>
                  <Text size="sm" fw={500}>
                    {tpl.id}
                  </Text>
                </Table.Td>
                <Table.Td>{localizedLabel(tpl.label)}</Table.Td>
                <Table.Td>{formatDateTime(tpl.updatedAt ?? tpl.createdAt)}</Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </QueryState>

      <CreatePublicTemplateModal
        opened={createOpen}
        onClose={() => setCreateOpen(false)}
      />
    </Paper>
  );
}

function RenderedTemplatesTab() {
  const navigate = useNavigate();
  const { i18n } = useLingui();
  const { data, error, isLoading } = useDocumentTemplates();
  const templates = data ?? [];

  return (
    <Paper withBorder p="lg" radius="md">
      <Text size="sm" c="dimmed" mb="md">
        <Trans>
          The underlying rendered templates. Each version is immutable.
        </Trans>
      </Text>
      <QueryState
        isLoading={isLoading}
        error={error}
        isEmpty={templates.length === 0}
        empty={
          <Stack align="center" gap="xs" c="dimmed">
            <IconFileCode size={32} />
            <Text size="sm">
              <Trans>No rendered templates yet.</Trans>
            </Text>
          </Stack>
        }
      >
        <Table verticalSpacing="sm" highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>
                <Trans>ID</Trans>
              </Table.Th>
              <Table.Th>
                <Trans>Public ID</Trans>
              </Table.Th>
              <Table.Th>
                <Trans>Created</Trans>
              </Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {templates.map((tpl) => (
              <Table.Tr
                key={tpl.id}
                style={{ cursor: "pointer" }}
                onClick={() => navigate(`/${i18n.locale}/document-templates/rendered/${tpl.id}`)}
              >
                <Table.Td>
                  <Text size="sm" fw={500} ff="monospace">
                    {tpl.id}
                  </Text>
                </Table.Td>
                <Table.Td>{tpl.publicDocumentTemplateId ?? "—"}</Table.Td>
                <Table.Td>{formatDateTime(tpl.createdAt)}</Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </QueryState>
    </Paper>
  );
}

export function DocumentTemplatesList() {
  return (
    <Stack>
      <Stack gap={2}>
        <Title order={1}>
          <Trans>Document templates</Trans>
        </Title>
        <Text size="sm" c="dimmed">
          <Trans>Design the documents generated for invoices.</Trans>
        </Text>
      </Stack>

      <Tabs defaultValue="public" keepMounted={false}>
        <Tabs.List>
          <Tabs.Tab value="public" leftSection={<IconTemplate size={16} />}>
            <Trans>Public templates</Trans>
          </Tabs.Tab>
          <Tabs.Tab value="rendered" leftSection={<IconFileCode size={16} />}>
            <Trans>Rendered templates</Trans>
          </Tabs.Tab>
        </Tabs.List>
        <Tabs.Panel value="public" pt="lg">
          <PublicTemplatesTab />
        </Tabs.Panel>
        <Tabs.Panel value="rendered" pt="lg">
          <RenderedTemplatesTab />
        </Tabs.Panel>
      </Tabs>
    </Stack>
  );
}
