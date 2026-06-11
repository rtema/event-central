import { Trans, useLingui } from "@lingui/react/macro";
import { Anchor, Button, Group, Paper, Stack, Text, Title } from "@mantine/core";
import { useForm } from "@mantine/form";
import { notifications } from "@mantine/notifications";
import { IconArrowLeft, IconDeviceFloppy } from "@tabler/icons-react";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router";
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
  useDocumentTemplate,
  usePublicTemplate,
} from "../invoices/invoicingHooks";
import { QueryState } from "../ui/QueryState";
import { localizedLabel } from "../utils/format";

export function PublicDocumentTemplateEditor() {
  const { t, i18n } = useLingui();
  const { templateId = "" } = useParams();
  const { mutate } = useSWRConfig();
  const { data: tpl, error, isLoading } = usePublicTemplate(templateId);
  // Pull the current body from the rendered template it points at, if any.
  const { data: rendered } = useDocumentTemplate(tpl?.documentTemplateId);
  const [saving, setSaving] = useState(false);

  const form = useForm<TemplateAssetsValues>({
    initialValues: { html: "", css: "", images: [], fonts: [] },
  });

  useEffect(() => {
    if (!rendered) return;
    form.setValues({
      html: rendered.html ?? "",
      css: rendered.css ?? "",
      images: (rendered.images ?? []).map((i) => ({
        name: i.name ?? "",
        link: i.link ?? "",
        file: "",
      })),
      fonts: (rendered.fonts ?? []).map((f) => ({
        name: f.name ?? "",
        file: "",
      })),
    });
    form.resetDirty();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rendered?.id]);

  const onSubmit = async () => {
    setSaving(true);
    try {
      await templatesApi.updatePublic(templateId, assetsToPayload(form.values));
      void mutate(invKeys.publicTemplate(templateId));
      void mutate(invKeys.publicTemplates());
      void mutate(invKeys.templates());
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
              <Title order={2}>{tpl.id}</Title>
              <Text size="sm" c="dimmed">
                {localizedLabel(tpl.label)}
              </Text>
            </Paper>

            <Paper withBorder p="lg" radius="md">
              <Text size="sm" c="dimmed" mb="md">
                <Trans>
                  Saving publishes a new rendered version for this public
                  template. Uploaded fonts and images are only re-sent if you
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
          </>
        )}
      </QueryState>
    </Stack>
  );
}
