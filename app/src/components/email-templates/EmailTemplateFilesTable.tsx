import { Trans, useLingui } from "@lingui/react/macro";
import {
  ActionIcon,
  Badge,
  Button,
  Code,
  FileButton,
  Group,
  Modal,
  SegmentedControl,
  Stack,
  Table,
  Text,
  TextInput,
  Tooltip,
} from "@mantine/core";
import { useForm } from "@mantine/form";
import { modals } from "@mantine/modals";
import { notifications } from "@mantine/notifications";
import {
  IconExternalLink,
  IconPencil,
  IconPhoto,
  IconPlus,
  IconTrash,
  IconTypography,
  IconUpload,
} from "@tabler/icons-react";
import { useState } from "react";
import { toRequestError } from "../../api/client";
import { emailTemplatesApi } from "../../api/emailTemplates";
import { useEmailTemplateMutations } from "../../api/hooks";
import type { EmailTemplateFile, File as StoredFile } from "../../api/types";
import { FilePickerModal } from "../document-templates/FilePickerModal";
import { useOpenFile } from "../files/useFileActions";
import { fileToBase64, localizedLabel } from "../utils/format";

function TypeBadge({ type }: { type?: string }) {
  if (type === "font") {
    return (
      <Badge variant="light" color="grape" leftSection={<IconTypography size={12} />}>
        <Trans>Font</Trans>
      </Badge>
    );
  }
  return (
    <Badge variant="light" color="blue" leftSection={<IconPhoto size={12} />}>
      <Trans>Image</Trans>
    </Badge>
  );
}

/** Modal for referencing an existing file or uploading a new one under a key. */
function AddFileModal({
  templateId,
  opened,
  onClose,
}: {
  templateId: string;
  opened: boolean;
  onClose: () => void;
}) {
  const { t } = useLingui();
  const { revalidateTemplate } = useEmailTemplateMutations(templateId);
  const [source, setSource] = useState<"library" | "upload">("library");
  const [picked, setPicked] = useState<StoredFile | null>(null);
  const [upload, setUpload] = useState<File | null>(null);
  const [pickerOpen, setPickerOpen] = useState(false);
  const [saving, setSaving] = useState(false);

  const form = useForm<{ key: string }>({
    initialValues: { key: "" },
    validate: {
      key: (v) =>
        /^[a-z0-9_-]+$/i.test(v.trim())
          ? null
          : t`Use letters, numbers, '-' and '_' only`,
    },
  });

  const reset = () => {
    form.reset();
    setPicked(null);
    setUpload(null);
    setSource("library");
  };

  const close = () => {
    reset();
    onClose();
  };

  const onSubmit = async () => {
    if (form.validate().hasErrors) return;
    if (source === "library" && !picked) {
      notifications.show({
        color: "red",
        title: t`Pick a file`,
        message: t`Choose a file from the library first.`,
      });
      return;
    }
    if (source === "upload" && !upload) {
      notifications.show({
        color: "red",
        title: t`Choose a file`,
        message: t`Select a file to upload first.`,
      });
      return;
    }
    setSaving(true);
    try {
      const body =
        source === "library"
          ? { key: form.values.key.trim(), fileId: picked!.id }
          : { key: form.values.key.trim(), file: await fileToBase64(upload!) };
      await emailTemplatesApi.createFile(templateId, body);
      revalidateTemplate();
      notifications.show({
        color: "pine",
        title: t`File attached`,
        message: form.values.key.trim(),
      });
      close();
    } catch (err) {
      notifications.show({
        color: "red",
        title: t`Could not attach file`,
        message: toRequestError(err).message,
      });
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal opened={opened} onClose={close} title={t`Attach a file`} size="md">
      <Stack>
        <TextInput
          label={t`Reference key`}
          withAsterisk
          description={t`How the template refers to this file, e.g. logo.`}
          placeholder="logo"
          {...form.getInputProps("key")}
        />
        <SegmentedControl
          fullWidth
          value={source}
          onChange={(v) => setSource(v as "library" | "upload")}
          data={[
            { value: "library", label: t`From library` },
            { value: "upload", label: t`Upload` },
          ]}
        />
        {source === "library" ? (
          <Group justify="space-between">
            <Text size="sm" c={picked ? undefined : "dimmed"}>
              {picked ? localizedLabel(picked.label) || picked.id : t`No file selected`}
            </Text>
            <Button variant="default" onClick={() => setPickerOpen(true)}>
              <Trans>Choose file</Trans>
            </Button>
          </Group>
        ) : (
          <Group justify="space-between">
            <Text size="sm" c={upload ? undefined : "dimmed"}>
              {upload ? upload.name : t`No file selected`}
            </Text>
            <FileButton onChange={setUpload} accept="image/*,font/*,.ttf">
              {(props) => (
                <Button
                  variant="default"
                  leftSection={<IconUpload size={16} />}
                  {...props}
                >
                  <Trans>Select file</Trans>
                </Button>
              )}
            </FileButton>
          </Group>
        )}
        <Group justify="flex-end" mt="sm">
          <Button variant="default" onClick={close}>
            <Trans>Cancel</Trans>
          </Button>
          <Button loading={saving} onClick={() => void onSubmit()}>
            <Trans>Attach file</Trans>
          </Button>
        </Group>
      </Stack>

      <FilePickerModal
        opened={pickerOpen}
        onClose={() => setPickerOpen(false)}
        onPick={setPicked}
        type="image"
        title={t`Pick a file`}
      />
    </Modal>
  );
}

/** Inline modal to rename a file's reference key. */
function useRenameKey(templateId: string) {
  const { t } = useLingui();
  const { revalidateTemplate } = useEmailTemplateMutations(templateId);

  return (file: EmailTemplateFile) => {
    let next = file.key ?? "";
    modals.openConfirmModal({
      title: t`Rename reference key`,
      children: (
        <TextInput
          label={t`Reference key`}
          defaultValue={file.key ?? ""}
          onChange={(e) => (next = e.currentTarget.value)}
          data-autofocus
        />
      ),
      labels: { confirm: t`Save`, cancel: t`Cancel` },
      onConfirm: async () => {
        try {
          await emailTemplatesApi.updateFile(templateId, file.id, {
            key: next.trim(),
          });
          revalidateTemplate();
          notifications.show({
            color: "pine",
            title: t`Key updated`,
            message: next.trim(),
          });
        } catch (err) {
          notifications.show({
            color: "red",
            title: t`Could not update key`,
            message: toRequestError(err).message,
          });
        }
      },
    });
  };
}

export function EmailTemplateFilesTable({
  templateId,
  files,
}: {
  templateId: string;
  files: EmailTemplateFile[];
}) {
  const { t } = useLingui();
  const { revalidateTemplate } = useEmailTemplateMutations(templateId);
  const { openFile, openingId } = useOpenFile();
  const [addOpen, setAddOpen] = useState(false);
  const renameKey = useRenameKey(templateId);

  const onRemove = (file: EmailTemplateFile) =>
    modals.openConfirmModal({
      title: t`Remove file`,
      children: (
        <Text size="sm">
          <Trans>
            Remove the reference "{file.key ?? file.id}" from this template? The
            underlying file in the library is not deleted.
          </Trans>
        </Text>
      ),
      labels: { confirm: t`Remove`, cancel: t`Cancel` },
      confirmProps: { color: "red" },
      onConfirm: async () => {
        try {
          await emailTemplatesApi.removeFile(templateId, file.id);
          revalidateTemplate();
          notifications.show({
            color: "pine",
            title: t`File removed`,
            message: file.key ?? file.id,
          });
        } catch (err) {
          notifications.show({
            color: "red",
            title: t`Could not remove file`,
            message: toRequestError(err).message,
          });
        }
      },
    });

  return (
    <Stack>
      <Group justify="space-between">
        <Text size="sm" c="dimmed">
          <Trans>
            Images and fonts the template can reference by key in its HTML.
          </Trans>
        </Text>
        <Button
          size="xs"
          leftSection={<IconPlus size={14} />}
          onClick={() => setAddOpen(true)}
        >
          <Trans>Attach file</Trans>
        </Button>
      </Group>

      {files.length === 0 ? (
        <Text size="sm" c="dimmed">
          <Trans>No files attached to this template.</Trans>
        </Text>
      ) : (
        <Table.ScrollContainer minWidth={640}>
          <Table verticalSpacing="sm" highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>
                  <Trans>Key</Trans>
                </Table.Th>
                <Table.Th>
                  <Trans>Type</Trans>
                </Table.Th>
                <Table.Th>
                  <Trans>Font</Trans>
                </Table.Th>
                <Table.Th />
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {files.map((f) => (
                <Table.Tr key={f.id}>
                  <Table.Td>
                    <Code>
                      {`{{ ${f.type === "font" ? "font" : "images"}.${f.key ?? "?"} }}`}
                    </Code>
                  </Table.Td>
                  <Table.Td>
                    <TypeBadge type={f.type} />
                  </Table.Td>
                  <Table.Td>
                    {f.type === "font" ? (
                      <Text size="sm">
                        {f.fontName ?? "—"}
                        {f.fontWeight ? ` · ${f.fontWeight}` : ""}
                      </Text>
                    ) : (
                      <Text size="sm" c="dimmed">
                        —
                      </Text>
                    )}
                  </Table.Td>
                  <Table.Td>
                    <Group gap={4} justify="flex-end" wrap="nowrap">
                      <Tooltip label={t`Rename key`}>
                        <ActionIcon
                          variant="subtle"
                          onClick={() => renameKey(f)}
                          aria-label={t`Rename key`}
                        >
                          <IconPencil size={16} />
                        </ActionIcon>
                      </Tooltip>
                      {f.fileId && (
                        <Tooltip label={t`Open file`}>
                          <ActionIcon
                            variant="subtle"
                            loading={openingId === f.fileId}
                            onClick={() => void openFile(f.fileId)}
                            aria-label={t`Open file`}
                          >
                            <IconExternalLink size={16} />
                          </ActionIcon>
                        </Tooltip>
                      )}
                      <Tooltip label={t`Remove`}>
                        <ActionIcon
                          variant="subtle"
                          color="red"
                          onClick={() => onRemove(f)}
                          aria-label={t`Remove`}
                        >
                          <IconTrash size={16} />
                        </ActionIcon>
                      </Tooltip>
                    </Group>
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Table.ScrollContainer>
      )}

      <AddFileModal
        templateId={templateId}
        opened={addOpen}
        onClose={() => setAddOpen(false)}
      />
    </Stack>
  );
}
