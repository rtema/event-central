import { Trans, useLingui } from "@lingui/react/macro";
import {
  Anchor,
  Button,
  Grid,
  Group,
  Paper,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import { useForm } from "@mantine/form";
import { notifications } from "@mantine/notifications";
import { IconArrowLeft, IconDeviceFloppy } from "@tabler/icons-react";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router";
import { useSWRConfig } from "swr";
import { toRequestError } from "../../api/client";
import { documentTemplatesApi } from "../../api/documentTemplates";
import {
  assetsToPayload,
  emptyFont,
  emptyImage,
  TemplateAssetsFields,
  type TemplateAssetsValues,
} from "../invoices/TemplateAssetsFields";
import {
  invKeys,
  useDocumentTemplate,
  useDocumentTemplateFiles,
  usePublicDocumentTemplate,
} from "../invoices/invoicingHooks";
import { QueryState } from "../ui/QueryState";
import { localizedLabel } from "../utils/format";
import { DocumentTemplateFilesTable } from "./DocumentTemplateFilesTable";
import { DocumentTemplatePreview } from "./DocumentTemplatePreview";

export function PublicDocumentTemplateEditor() {
  const { t, i18n } = useLingui();
  const { templateId = "" } = useParams();
  const { mutate } = useSWRConfig();
  const { data: tpl, error, isLoading } = usePublicDocumentTemplate(templateId);
  // Pull the current body from the rendered template it points at, if any.
  const { data: rendered } = useDocumentTemplate(tpl?.documentTemplateId);
  const { data: files, isLoading: filesLoading, error: filesError } =
    useDocumentTemplateFiles(tpl?.documentTemplateId);
  const [saving, setSaving] = useState(false);

  const form = useForm<TemplateAssetsValues>({
    initialValues: {
      locale: "",
      label: {
        "de": "",
        "en": ""
      },
      html: "",
      css: "",
      images: [],
      fonts: []
    },
  });

  useEffect(() => {
    if (!rendered) return;
    form.setValues({
      html: rendered.html ?? "",
      css: rendered.css ?? "",
      // The immutable response keys images by `name`; the request keys them by
      // `key`. Bridge name → key on load (see API-REVIEW.md).
      images: (files ?? []).filter(itm => itm.type === "image").map((i) => ({
        ...emptyImage(),
        key: i.key ?? "",
        fileId: i.fileId,
      })),
      fonts: (files ?? []).filter(itm => itm.type === "font").map((f) => ({
        ...emptyFont(),
        name: f.fontName ?? "",
        weight: f.fontWeight ?? "",
      })),
    });
    form.resetDirty();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rendered?.id, files]);

  const onSubmit = async () => {
    setSaving(true);
    try {
      await documentTemplatesApi.updatePublic(templateId, assetsToPayload(form.values));
      void mutate(invKeys.publicDocumentTemplate(templateId));
      void mutate(invKeys.publicDocumentTemplates());
      void mutate(invKeys.documentTemplates());
      notifications.show({
        color: "pine",
        title: t`Template updated`,
        message: templateId,
      });
    } catch (err) {
      notifications.show({
        color: "red",
        title: t`Could not update template`,
        message: toRequestError(err).message,
      });
    } finally {
      setSaving(false);
    }
  };

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
              <Title order={2}>{tpl.id}</Title>
              <Text size="sm" c="dimmed">
                {localizedLabel(tpl.label)}
              </Text>
            </Paper>

            <Grid gutter="md" align="stretch">
              <Grid.Col span={{ base: 12, lg: 7 }}>
                <Paper withBorder p="lg" radius="md">
                  <Text size="sm" c="dimmed" mb="md">
                    <Trans>
                      Saving publishes a new rendered version for this public
                      template. Reference library files by picking them, or
                      upload inline — inline uploads are only re-sent if you
                      attach them again.
                    </Trans>
                  </Text>
                  <TemplateAssetsFields form={form} />
                  <Group justify="flex-end" mt="lg">
                    <Button
                      leftSection={<IconDeviceFloppy size={16} />}
                      loading={saving}
                      onClick={() => void onSubmit()}
                    >
                      <Trans>Save template</Trans>
                    </Button>
                  </Group>
                </Paper>
              </Grid.Col>
              <Grid.Col span={{ base: 12, lg: 5 }}>
                {tpl.documentTemplateId ? (
                  <DocumentTemplatePreview templateId={tpl.documentTemplateId} />
                ) : (
                  <Paper withBorder p="lg" radius="md" h="100%">
                    <Text size="sm" c="dimmed">
                      <Trans>
                        Save the template to generate a preview of the published
                        version.
                      </Trans>
                    </Text>
                  </Paper>
                )}
              </Grid.Col>
            </Grid>


            <Paper withBorder p="lg" radius="md">
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
