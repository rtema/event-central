import { Trans, useLingui } from "@lingui/react/macro";
import {
  ActionIcon,
  Button,
  FileButton,
  Grid,
  Group,
  Paper,
  Stack,
  Text,
  Textarea,
  TextInput,
  Title,
} from "@mantine/core";
import { IconPlus, IconTrash, IconUpload } from "@tabler/icons-react";
import type { UseFormReturnType } from "@mantine/form";
import { fileToBase64 } from "../utils/format";

export interface TemplateImageForm {
  name: string;
  link: string;
  file: string;
}
export interface TemplateFontForm {
  name: string;
  file: string;
}
export interface TemplateAssetsValues {
  html: string;
  css: string;
  images: TemplateImageForm[];
  fonts: TemplateFontForm[];
}

/**
 * Shared editing surface for a document template body: the WeasyPrint HTML/CSS
 * plus repeatable image and font assets (uploaded as base64 or, for images,
 * referenced by an https link).
 */
export function TemplateAssetsFields<T extends TemplateAssetsValues>({
  form,
}: {
  form: UseFormReturnType<T>;
}) {
  const { t } = useLingui();
  // The generic form type confuses Mantine's list helpers; the field paths are
  // stable so we read values through a loosely-typed view.
  const values = form.values as TemplateAssetsValues;

  return (
    <Stack>
      <Textarea
        label={t`HTML template`}
        description={t`Rendered with WeasyPrint; use {{ }} for Jinja variables.`}
        autosize
        minRows={6}
        maxRows={18}
        styles={{ input: { fontFamily: "var(--mantine-font-family-monospace)" } }}
        {...form.getInputProps("html")}
      />
      <Textarea
        label={t`CSS`}
        autosize
        minRows={4}
        maxRows={14}
        styles={{ input: { fontFamily: "var(--mantine-font-family-monospace)" } }}
        {...form.getInputProps("css")}
      />

      <Stack gap="xs">
        <Title order={5}>
          <Trans>Images</Trans>
        </Title>
        {values.images.map((img, idx) => (
          <Paper key={idx} withBorder p="sm" radius="md">
            <Grid align="flex-end" gutter="xs">
              <Grid.Col span={{ base: 12, sm: 3 }}>
                <TextInput
                  label={t`Name`}
                  description={t`lowercase`}
                  {...form.getInputProps(`images.${idx}.name`)}
                />
              </Grid.Col>
              <Grid.Col span={{ base: 12, sm: 6 }}>
                <TextInput
                  label={t`Link (https)`}
                  placeholder="https://…"
                  {...form.getInputProps(`images.${idx}.link`)}
                />
              </Grid.Col>
              <Grid.Col span={{ base: 9, sm: 2 }}>
                <FileButton
                  accept="image/*"
                  onChange={async (file) => {
                    if (!file) return;
                    const b64 = await fileToBase64(file);
                    form.setFieldValue(
                      `images.${idx}.file` as never,
                      b64 as never,
                    );
                  }}
                >
                  {(props) => (
                    <Button
                      {...props}
                      variant="default"
                      size="sm"
                      leftSection={<IconUpload size={14} />}
                    >
                      {img.file ? <Trans>Replace</Trans> : <Trans>Upload</Trans>}
                    </Button>
                  )}
                </FileButton>
              </Grid.Col>
              <Grid.Col span={{ base: 3, sm: 1 }}>
                <ActionIcon
                  variant="subtle"
                  color="red"
                  onClick={() => form.removeListItem("images", idx)}
                  aria-label={t`Remove image`}
                >
                  <IconTrash size={16} />
                </ActionIcon>
              </Grid.Col>
              {img.file && (
                <Grid.Col span={12}>
                  <Text size="xs" c="dimmed">
                    <Trans>Embedded upload attached.</Trans>
                  </Text>
                </Grid.Col>
              )}
            </Grid>
          </Paper>
        ))}
        <Group>
          <Button
            variant="light"
            size="xs"
            leftSection={<IconPlus size={14} />}
            onClick={() =>
              form.insertListItem("images", { name: "", link: "", file: "" })
            }
          >
            <Trans>Add image</Trans>
          </Button>
        </Group>
      </Stack>

      <Stack gap="xs">
        <Title order={5}>
          <Trans>Fonts</Trans>
        </Title>
        {values.fonts.map((font, idx) => (
          <Paper key={idx} withBorder p="sm" radius="md">
            <Grid align="flex-end" gutter="xs">
              <Grid.Col span={{ base: 12, sm: 7 }}>
                <TextInput
                  label={t`Font name (as used in CSS)`}
                  {...form.getInputProps(`fonts.${idx}.name`)}
                />
              </Grid.Col>
              <Grid.Col span={{ base: 9, sm: 4 }}>
                <FileButton
                  accept=".woff,.woff2,.ttf,.otf"
                  onChange={async (file) => {
                    if (!file) return;
                    const b64 = await fileToBase64(file);
                    form.setFieldValue(
                      `fonts.${idx}.file` as never,
                      b64 as never,
                    );
                  }}
                >
                  {(props) => (
                    <Button
                      {...props}
                      variant="default"
                      size="sm"
                      leftSection={<IconUpload size={14} />}
                    >
                      {font.file ? <Trans>Replace</Trans> : <Trans>Upload</Trans>}
                    </Button>
                  )}
                </FileButton>
              </Grid.Col>
              <Grid.Col span={{ base: 3, sm: 1 }}>
                <ActionIcon
                  variant="subtle"
                  color="red"
                  onClick={() => form.removeListItem("fonts", idx)}
                  aria-label={t`Remove font`}
                >
                  <IconTrash size={16} />
                </ActionIcon>
              </Grid.Col>
            </Grid>
          </Paper>
        ))}
        <Group>
          <Button
            variant="light"
            size="xs"
            leftSection={<IconPlus size={14} />}
            onClick={() =>
              form.insertListItem("fonts", { name: "", file: "" })
            }
          >
            <Trans>Add font</Trans>
          </Button>
        </Group>
      </Stack>
    </Stack>
  );
}

/** Map the editor's asset arrays to the API request shape. */
export function assetsToPayload(values: TemplateAssetsValues) {
  return {
    html: values.html || undefined,
    css: values.css || undefined,
    images: values.images
      .filter((i) => i.name && (i.link || i.file))
      .map((i) => ({
        name: i.name,
        ...(i.link ? { link: i.link } : {}),
        ...(i.file ? { file: i.file } : {}),
      })),
    fonts: values.fonts
      .filter((f) => f.name && f.file)
      .map((f) => ({ name: f.name, file: f.file })),
  };
}
