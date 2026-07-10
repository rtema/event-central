import { Trans, useLingui } from "@lingui/react/macro";
import {
  Anchor,
  Badge,
  Button,
  Code,
  CopyButton,
  Group,
  Image,
  Paper,
  Stack,
  ThemeIcon,
  Title,
} from "@mantine/core";
import {
  IconArrowLeft,
  IconCheck,
  IconCopy,
  IconExternalLink,
  IconFile,
  IconPhoto,
  IconTypography,
} from "@tabler/icons-react";
import { Link, useParams } from "react-router";
import { listLinkWithFilters } from "../utils/listQuery";
import { FieldGrid } from "../ui/FieldGrid";
import { QueryState } from "../ui/QueryState";
import { formatDateTime } from "../utils/datetime";
import { formatBytes, localizedLabel } from "../utils/format";
import { useFile } from "../../api/hooks";
import { useOpenFile } from "./useFileActions";

function HashValue({ value }: { value: string }) {
  return (
    <Group gap={4} wrap="nowrap">
      <Code style={{ wordBreak: "break-all" }}>{value}</Code>
      <CopyButton value={value}>
        {({ copied, copy }) => (
          <Button
            size="compact-xs"
            variant="subtle"
            color={copied ? "pine" : "gray"}
            onClick={copy}
            leftSection={
              copied ? <IconCheck size={12} /> : <IconCopy size={12} />
            }
          >
            {copied ? <Trans>Copied</Trans> : <Trans>Copy</Trans>}
          </Button>
        )}
      </CopyButton>
    </Group>
  );
}

export function FileDetail() {
  const { t, i18n } = useLingui();
  const { fileId = "" } = useParams();
  const { data: file, error, isLoading } = useFile(fileId);
  const { openFile, openingId } = useOpenFile();

  const isImage =
    file?.mime?.startsWith("image/") || file?.type === "image";
  const isFont = file?.mime?.includes("font") || file?.type === "font";

  return (
    <Stack maw={960} mx="auto" w="100%">
      <Anchor component={Link} to={listLinkWithFilters(`/${i18n.locale}/files`, "files")} size="sm">
        <Group gap={4}>
          <IconArrowLeft size={14} />
          <Trans>Back to files</Trans>
        </Group>
      </Anchor>

      <QueryState isLoading={isLoading} error={error}>
        {file && (
          <>
            <Paper withBorder p="lg" radius="md">
              <Group justify="space-between" align="flex-start" wrap="nowrap">
                <Group align="flex-start" wrap="nowrap">
                  {file.preview ? (
                    <Image
                      src={`data:image/*;base64,${file.preview}`}
                      w={96}
                      h={96}
                      radius="md"
                      fit="cover"
                      alt=""
                    />
                  ) : (
                    <ThemeIcon variant="light" size={96} radius="md" color="gray">
                      {isImage ? (
                        <IconPhoto size={40} />
                      ) : isFont ? (
                        <IconTypography size={40} />
                      ) : (
                        <IconFile size={40} />
                      )}
                    </ThemeIcon>
                  )}
                  <Stack gap={4}>
                    <Title order={2}>
                      {localizedLabel(file.label) !== "—"
                        ? localizedLabel(file.label)
                        : file.id}
                    </Title>
                    <Group gap="xs">
                      {file.extension && (
                        <Badge variant="light" color="blue">
                          .{file.extension}
                        </Badge>
                      )}
                      {file.type && (
                        <Badge variant="light" color="grape">
                          {file.type}
                        </Badge>
                      )}
                      {file.published ? (
                        <Badge variant="light" color="pine">
                          <Trans>Public</Trans>
                        </Badge>
                      ) : (
                        <Badge variant="light" color="gray">
                          <Trans>Private</Trans>
                        </Badge>
                      )}
                      {file.deletedAt && (
                        <Badge variant="light" color="red">
                          <Trans>Deleted</Trans>
                        </Badge>
                      )}
                    </Group>
                  </Stack>
                </Group>
                <Button
                  leftSection={<IconExternalLink size={16} />}
                  loading={openingId === file.id}
                  onClick={() => void openFile(file.id)}
                >
                  <Trans>Open</Trans>
                </Button>
              </Group>
            </Paper>

            <Paper withBorder p="lg" radius="md">
              <Title order={4} mb="md">
                <Trans>Details</Trans>
              </Title>
              <FieldGrid
                cols={{ base: 1, sm: 2 }}
                fields={[
                  { label: t`ID`, value: <Code>{file.id}</Code> },
                  { label: t`MIME type`, value: file.mime },
                  { label: t`Extension`, value: file.extension },
                  { label: t`Type`, value: file.type },
                  { label: t`Size`, value: formatBytes(file.size) },
                  {
                    label: t`Dimensions`,
                    value:
                      file.width && file.height
                        ? `${file.width} × ${file.height}px`
                        : undefined,
                  },
                  {
                    label: t`Visibility`,
                    value: file.published ? t`Public` : t`Private`,
                  },
                  { label: t`Access key`, value: file.accessKey },
                  { label: t`Base path`, value: file.basePath },
                  { label: t`Label (DE)`, value: file.label?.de },
                  { label: t`Label (EN)`, value: file.label?.en },
                  { label: t`Created`, value: formatDateTime(file.createdAt) },
                  { label: t`Created by`, value: file.createdBy },
                  {
                    label: t`Deleted`,
                    value: file.deletedAt
                      ? formatDateTime(file.deletedAt)
                      : undefined,
                  },
                  { label: t`Deleted by`, value: file.deletedBy ?? undefined },
                  {
                    label: t`SHA-256`,
                    value: file.hash ? <HashValue value={file.hash} /> : undefined,
                    full: true,
                  },
                ]}
              />
            </Paper>

            {file.meta && Object.keys(file.meta).length > 0 && (
              <Paper withBorder p="lg" radius="md">
                <Title order={4} mb="md">
                  <Trans>Metadata</Trans>
                </Title>
                <Code block>{JSON.stringify(file.meta, null, 2)}</Code>
              </Paper>
            )}
          </>
        )}
      </QueryState>
    </Stack>
  );
}
