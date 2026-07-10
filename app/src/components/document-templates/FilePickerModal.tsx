import { Trans, useLingui } from "@lingui/react/macro";
import {
  Badge,
  Group,
  Image,
  Modal,
  Paper,
  ScrollArea,
  Stack,
  Text,
  TextInput,
  ThemeIcon,
  UnstyledButton,
} from "@mantine/core";
import { IconFile, IconPhoto, IconSearch, IconTypography } from "@tabler/icons-react";
import { useMemo, useState } from "react";
import type { File, FileSearchParams, FileType } from "../../api/types";
import { useFileSearch } from "../../api/hooks";
import { QueryState } from "../ui/QueryState";
import { formatBytes, localizedLabel } from "../utils/format";

interface FilePickerModalProps {
  opened: boolean;
  onClose: () => void;
  onPick: (file: File) => void;
  type: FileType;
  title?: string;
}

function fileName(file: File): string {
  const label = localizedLabel(file.label);
  return label !== "—" ? label : file.id;
}


/** Read the structured filters out of the address bar. */
export function paramsFromState({ q, type, offset }: { q: string, type: FileType, offset: string }): FileSearchParams {
  return {
    q,
    type: [type],
    basePath: [""],
    offset,
  };
}

/**
 * Browse the file library and pick one existing file. The caller receives the
 * chosen {@link StoredFile} and references it by `fileId` in the template's
 * images/fonts arrays — which is how the API attaches an existing file.
 */
export function FilePickerModal({
  opened,
  onClose,
  onPick,
  type,
  title,
}: FilePickerModalProps) {
  const { t } = useLingui();

  const [q, setQ] = useState("");

  const params = useMemo(
    () => paramsFromState({ q, type: type, offset: "0" }),
    [q],
  );

  const { data, error, isLoading } = useFileSearch({ ...params, limit: 100 });
  const files = data?.data ?? [];

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title={title ?? t`Pick a file`}
      size="lg"
    >
      <Stack>
        <TextInput
          placeholder={t`Search files`}
          leftSection={<IconSearch size={16} />}
          value={q}
          onChange={(e) => setQ(e.currentTarget.value)}
        />
        <QueryState
          isLoading={isLoading}
          error={error}
          isEmpty={files.length === 0}
          empty={
            <Text size="sm" c="dimmed">
              <Trans>No matching files.</Trans>
            </Text>
          }
        >
          <ScrollArea.Autosize mah={340}>
            <Stack gap="xs" pr="sm">
              {files.map((file) => {
                const isImage =
                  file.mime?.startsWith("image/") || file.type === "image";
                return (
                  <UnstyledButton
                    key={file.id}
                    onClick={() => {
                      onPick(file);
                      onClose();
                    }}
                  >
                    <Paper withBorder p="xs" radius="md">
                      <Group wrap="nowrap" gap="sm">
                        {file.preview ? (
                          <Image
                            src={`data:image/*;base64,${file.preview}`}
                            w={40}
                            h={40}
                            radius="sm"
                            fit="cover"
                            alt=""
                          />
                        ) : (
                          <ThemeIcon
                            variant="light"
                            size={40}
                            radius="sm"
                            color="gray"
                          >
                            {isImage ? (
                              <IconPhoto size={20} />
                            ) : file.mime?.includes("font") ? (
                              <IconTypography size={20} />
                            ) : (
                              <IconFile size={20} />
                            )}
                          </ThemeIcon>
                        )}
                        <Stack gap={0} style={{ flex: 1, minWidth: 0 }}>
                          <Text size="sm" fw={500} truncate>
                            {fileName(file)}
                          </Text>
                          <Text size="xs" c="dimmed" truncate>
                            {[
                              file.extension?.toUpperCase(),
                              file.mime,
                              formatBytes(file.size),
                            ]
                              .filter(Boolean)
                              .join(" · ")}
                          </Text>
                        </Stack>
                        {file.published && (
                          <Badge size="xs" variant="light" color="pine">
                            <Trans>Public</Trans>
                          </Badge>
                        )}
                      </Group>
                    </Paper>
                  </UnstyledButton>
                );
              })}
            </Stack>
          </ScrollArea.Autosize>
        </QueryState>
      </Stack>
    </Modal>
  );
}
