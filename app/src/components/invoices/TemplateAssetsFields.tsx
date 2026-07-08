import { Trans, useLingui } from "@lingui/react/macro";
import {
  ActionIcon,
  Badge,
  Button,
  FileButton,
  Grid,
  Group,
  NumberInput,
  Paper,
  Stack,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import type { UseFormReturnType } from "@mantine/form";
import {
  IconLibraryPhoto,
  IconPlus,
  IconTrash,
  IconUpload,
} from "@tabler/icons-react";
import { useState } from "react";
import type { File, FileType, MultiLanguageLabel } from "../../api/types";
import { FilePickerModal } from "../document-templates/FilePickerModal";
import { CodeEditor } from "../ui/CodeEditor";
import { fileToBase64, localizedLabel } from "../utils/format";

export interface TemplateImageForm {
  /** Jinja reference key: {{ image.<key> }}. */
  key: string;
  link: string;
  /** Base64 upload (send-once). */
  file: string;
  /** Reference to an existing stored file. */
  fileId: string;
  /** Display-only: chosen library file's name. */
  fileLabel: string;
}
export interface TemplateFontForm {
  name: string;
  weight: number | "";
  file: string;
  fileId: string;
  fileLabel: string;
}
export interface TemplateAssetsValues {
  locale: string;
  label: MultiLanguageLabel;
  html: string;
  css: string;
  images: TemplateImageForm[];
  fonts: TemplateFontForm[];
}

export function emptyImage(): TemplateImageForm {
  return { key: "", link: "", file: "", fileId: "", fileLabel: "" };
}
export function emptyFont(): TemplateFontForm {
  return { name: "", weight: 400, file: "", fileId: "", fileLabel: "" };
}

/**
 * Shared editing surface for a document template body: the WeasyPrint HTML/CSS
 * plus repeatable image and font assets. Each asset may be supplied three ways:
 * referenced from the file library (`fileId`), uploaded as base64 (`file`), or —
 * for images — pointed at by an https `link`.
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

  // Which asset row currently has the file picker open, e.g. "images.0".
  const [picking, setPicking] = useState<
    { type: FileType; idx: number } | null
  >(null);

  const pickInto = (file: File) => {
    if (!picking) return;
    const label = localizedLabel(file.label);
    const shown = label !== "—" ? label : file.id;
    form.setFieldValue(`${picking.type}s.${picking.idx}.fileId` as never, file.id as never);
    form.setFieldValue(
      `${picking.type}s.${picking.idx}.fileLabel` as never,
      shown as never,
    );
    // A referenced file supersedes an inline upload / link.
    form.setFieldValue(`${picking.type}s.${picking.idx}.file` as never, "" as never);
    if (picking.type === "image") {
      form.setFieldValue(`images.${picking.idx}.link` as never, "" as never);
    }
  };

  const clearRef = (kind: "image" | "font", idx: number) => {
    form.setFieldValue(`${kind}s.${idx}.fileId` as never, "" as never);
    form.setFieldValue(`${kind}s.${idx}.fileLabel` as never, "" as never);
  };

  return (
    <Stack>
      <CodeEditor
        language="html"
        label={t`HTML template`}
        description={t`Rendered with WeasyPrint; use {{ }} for Jinja variables.`}
        minRows={6}
        maxRows={18}
        value={values.html}
        onChange={(v) => form.setFieldValue("html" as never, v as never)}
        error={form.errors.html}
      />
      <CodeEditor
        language="css"
        label={t`CSS`}
        minRows={4}
        maxRows={14}
        value={values.css}
        onChange={(v) => form.setFieldValue("css" as never, v as never)}
        error={form.errors.css}
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
                  label={t`Key`}
                  description="{{ images.key }}"
                  {...form.getInputProps(`images.${idx}.key`)}
                />
              </Grid.Col>
              <Grid.Col span={{ base: 12, sm: 5 }}>
                {img.fileId ? (
                  <Group gap="xs">
                    <Badge
                      variant="light"
                      color="pine"
                      style={{ maxWidth: "100%" }}
                    >
                      {img.fileLabel || img.fileId}
                    </Badge>
                    <Button
                      variant="subtle"
                      size="compact-xs"
                      onClick={() => clearRef("image", idx)}
                    >
                      <Trans>Clear</Trans>
                    </Button>
                  </Group>
                ) : (
                  <Group gap="xs" wrap="nowrap">
                    <Button
                      variant="default"
                      size="sm"
                      leftSection={<IconLibraryPhoto size={14} />}
                      onClick={() => setPicking({ type: "image", idx })}
                    >
                      <Trans>Library</Trans>
                    </Button>
                    {!img.fileId && (
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
                          <ActionIcon
                            {...props}
                            variant="default"
                            size="lg"
                            aria-label={img.file ? t`Replace upload` : t`Upload`}
                          >
                            <IconUpload size={16} />
                          </ActionIcon>
                        )}
                      </FileButton>
                    )}
                  </Group>
                )}
              </Grid.Col>
              <Grid.Col span={{ base: 6, sm: 3 }}>

              </Grid.Col>
              <Grid.Col span={{ base: 6, sm: 1 }}>
                <ActionIcon
                  variant="subtle"
                  color="red"
                  onClick={() => form.removeListItem("images", idx)}
                  aria-label={t`Remove image`}
                >
                  <IconTrash size={16} />
                </ActionIcon>
              </Grid.Col>
              {img.file && !img.fileId && (
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
            onClick={() => form.insertListItem("images", emptyImage())}
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
              <Grid.Col span={{ base: 12, sm: 5 }}>
                <TextInput
                  label={t`Font name (as used in CSS)`}
                  {...form.getInputProps(`fonts.${idx}.name`)}
                />
              </Grid.Col>
              <Grid.Col span={{ base: 6, sm: 2 }}>
                <NumberInput
                  label={t`Weight`}
                  min={100}
                  max={900}
                  step={100}
                  {...form.getInputProps(`fonts.${idx}.weight`)}
                />
              </Grid.Col>
              <Grid.Col span={{ base: 6, sm: 4 }}>
                {font.fileId ? (
                  <Group gap="xs">
                    <Badge variant="light" color="pine">
                      {font.fileLabel || font.fileId}
                    </Badge>
                    <Button
                      variant="subtle"
                      size="compact-xs"
                      onClick={() => clearRef("font", idx)}
                    >
                      <Trans>Clear</Trans>
                    </Button>
                  </Group>
                ) : (
                  <Group gap={4} wrap="nowrap">
                    <Button
                      variant="default"
                      size="sm"
                      leftSection={<IconLibraryPhoto size={14} />}
                      onClick={() => setPicking({ type: "font", idx })}
                    >
                      <Trans>Library</Trans>
                    </Button>
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
                        <ActionIcon
                          {...props}
                          variant="default"
                          size="lg"
                          aria-label={font.file ? t`Replace upload` : t`Upload`}
                        >
                          <IconUpload size={16} />
                        </ActionIcon>
                      )}
                    </FileButton>
                  </Group>
                )}
              </Grid.Col>
              <Grid.Col span={{ base: 12, sm: 1 }}>
                <ActionIcon
                  variant="subtle"
                  color="red"
                  onClick={() => form.removeListItem("fonts", idx)}
                  aria-label={t`Remove font`}
                >
                  <IconTrash size={16} />
                </ActionIcon>
              </Grid.Col>
              {font.file && !font.fileId && (
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
            onClick={() => form.insertListItem("fonts", emptyFont())}
          >
            <Trans>Add font</Trans>
          </Button>
        </Group>
      </Stack>

      <FilePickerModal
        opened={picking !== null}
        type={picking?.type || "image"}
        onClose={() => setPicking(null)}
        onPick={pickInto}
        title={picking?.type === "font" ? t`Pick a font` : t`Pick an image`}
      />
    </Stack>
  );
}

/** Map the editor's asset arrays to the API request shape. */
export function assetsToPayload(values: TemplateAssetsValues) {
  return {
    locale: values.locale || "",
    label: values.label,
    html: values.html || "",
    css: values.css || "",
    images: values.images
      .filter((i) => i.key && (i.fileId || i.link || i.file))
      .map((i) => ({
        key: i.key,
        ...(i.fileId ? { fileId: i.fileId } : {}),
        ...(i.link ? { link: i.link } : {}),
        ...(i.file ? { file: i.file } : {}),
      })),
    fonts: values.fonts
      .filter((f) => f.name && (f.fileId || f.file))
      .map((f) => ({
        name: f.name,
        ...(f.weight !== "" ? { weight: Number(f.weight) } : {}),
        ...(f.fileId ? { fileId: f.fileId } : {}),
        ...(f.file ? { file: f.file } : {}),
      })),
  };
}
