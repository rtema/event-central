import { Trans, useLingui } from "@lingui/react/macro";
import {
  ActionIcon,
  Badge,
  Button,
  Group,
  Image,
  MultiSelect,
  Paper,
  Select,
  Stack,
  Table,
  TagsInput,
  Text,
  TextInput,
  ThemeIcon,
  Title,
  Tooltip,
} from "@mantine/core";
import { useDebouncedValue } from "@mantine/hooks";
import {
  IconExternalLink,
  IconFile,
  IconPhoto,
  IconSearch,
  IconX,
} from "@tabler/icons-react";
import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router";
import type {
  FileExtension,
  FileSearchParams,
  FileType,
  File,
} from "../../api/types";
import { Pager } from "../ui/Pager";
import { QueryState } from "../ui/QueryState";
import { formatDateTime } from "../utils/datetime";
import { formatBytes, localizedLabel } from "../utils/format";
import { useFileSearch } from "../invoices/invoicingHooks";
import {
  hasActiveFilters,
  paramsFromUrl,
  paramsToUrl,
} from "./fileSearchParams";
import { useOpenFile } from "./useFileActions";

const LIMIT = 100;

function FileThumb({ file }: { file: File }) {
  const isImage = file.mime?.startsWith("image/") || file.type === "image";
  if (file.preview) {
    return (
      <Image
        src={`data:image/*;base64,${file.preview}`}
        w={44}
        h={44}
        radius="sm"
        fit="cover"
        alt=""
      />
    );
  }
  return (
    <ThemeIcon variant="light" size={44} radius="sm" color="gray">
      {isImage ? <IconPhoto size={22} /> : <IconFile size={22} />}
    </ThemeIcon>
  );
}

export function FilesList() {
  const { t, i18n } = useLingui();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  // The address bar is the source of truth for all filters.
  const params = useMemo(
    () => paramsFromUrl(searchParams),
    [searchParams],
  );

  // Free-text box is debounced before it hits the URL.
  const [qInput, setQInput] = useState(params.q ?? "");
  const [debouncedQ] = useDebouncedValue(qInput, 350);
  useEffect(() => {
    setQInput(params.q ?? "");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params.q]);
  useEffect(() => {
    if ((debouncedQ || "") === (params.q ?? "")) return;
    commit({ ...params, q: debouncedQ || undefined, offset: undefined });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedQ]);

  const offset = Number(params.offset ?? "0");
  const { data, error, isLoading } = useFileSearch({ ...params, limit: LIMIT });
  const files = data?.data ?? [];
  const { openFile, openingId } = useOpenFile();

  // Any change resets pagination unless an explicit offset is supplied.
  function commit(next: FileSearchParams) {
    setSearchParams(paramsToUrl(next), { replace: true });
  }

  const activeFilters = hasActiveFilters(params);

  return (
    <Stack>
      <Stack gap={2}>
        <Title order={1}>
          <Trans>Files</Trans>
        </Title>
        <Text size="sm" c="dimmed">
          <Trans>
            Every file stored on the platform — images, fonts and generated
            documents.
          </Trans>
        </Text>
      </Stack>

      <Paper withBorder radius="md" p="md">
        <Stack gap="sm">
          <Group align="flex-end" wrap="wrap" gap="sm">
            <TextInput
              label={t`Search`}
              placeholder={t`Name, path or hash…`}
              leftSection={<IconSearch size={16} />}
              value={qInput}
              onChange={(e) => setQInput(e.currentTarget.value)}
              style={{ flex: "1 1 220px" }}
            />
            <MultiSelect
              label={t`Type`}
              placeholder={params.type?.length ? undefined : t`Any`}
              data={[
                { value: "image", label: t`Image` },
                { value: "font", label: t`Font` },
              ]}
              value={params.type ?? []}
              onChange={(v) =>
                commit({
                  ...params,
                  type: v as FileType[],
                  offset: undefined,
                })
              }
              clearable
              style={{ flex: "1 1 160px" }}
            />
            <MultiSelect
              label={t`Extension`}
              placeholder={params.extension?.length ? undefined : t`Any`}
              data={["png", "jpg", "ttf"]}
              value={params.extension ?? []}
              onChange={(v) =>
                commit({
                  ...params,
                  extension: v as FileExtension[],
                  offset: undefined,
                })
              }
              clearable
              style={{ flex: "1 1 160px" }}
            />
            <Select
              label={t`Visibility`}
              data={[
                { value: "", label: t`Any` },
                { value: "true", label: t`Public` },
                { value: "false", label: t`Private` },
              ]}
              value={
                params.published?.length === 1
                  ? String(params.published[0])
                  : ""
              }
              onChange={(v) =>
                commit({
                  ...params,
                  published: v ? [v === "true"] : undefined,
                  offset: undefined,
                })
              }
              style={{ flex: "1 1 140px" }}
            />
          </Group>

          <Group align="flex-end" gap="sm">
            <TagsInput
              label={t`Base paths`}
              placeholder={t`Add a path filter`}
              value={params.basePath ?? []}
              onChange={(v) =>
                commit({
                  ...params,
                  basePath: v.length ? v : undefined,
                  offset: undefined,
                })
              }
              style={{ flex: 1 }}
            />
            {activeFilters && (
              <Button
                variant="subtle"
                color="gray"
                leftSection={<IconX size={14} />}
                onClick={() => {
                  setQInput("");
                  commit({});
                }}
              >
                <Trans>Clear filters</Trans>
              </Button>
            )}
          </Group>
        </Stack>
      </Paper>

      <Paper withBorder radius="md" p="md">
        <QueryState
          isLoading={isLoading}
          error={error}
          isEmpty={files.length === 0}
          empty={
            <Stack align="center" gap="xs" c="dimmed">
              <IconFile size={32} />
              <Text size="sm">
                {activeFilters ? (
                  <Trans>No files match these filters.</Trans>
                ) : (
                  <Trans>No files yet.</Trans>
                )}
              </Text>
            </Stack>
          }
        >
          <Table.ScrollContainer minWidth={820}>
            <Table verticalSpacing="sm" highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th w={60} />
                  <Table.Th>
                    <Trans>Name</Trans>
                  </Table.Th>
                  <Table.Th>
                    <Trans>Type</Trans>
                  </Table.Th>
                  <Table.Th>
                    <Trans>Size</Trans>
                  </Table.Th>
                  <Table.Th>
                    <Trans>Dimensions</Trans>
                  </Table.Th>
                  <Table.Th>
                    <Trans>Visibility</Trans>
                  </Table.Th>
                  <Table.Th>
                    <Trans>Created</Trans>
                  </Table.Th>
                  <Table.Th />
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {files.map((file) => {
                  const label = localizedLabel(file.label);
                  const to = `/${i18n.locale}/files/${file.id}`;
                  return (
                    <Table.Tr
                      key={file.id}
                      style={{ cursor: "pointer" }}
                      onClick={() => navigate(to)}
                    >
                      <Table.Td>
                        <FileThumb file={file} />
                      </Table.Td>
                      <Table.Td>
                        <Stack gap={0}>
                          <Text size="sm" fw={500}>
                            {label !== "—" ? label : file.id}
                          </Text>
                          {file.extension && (
                            <Text size="xs" c="dimmed">
                              .{file.extension}
                            </Text>
                          )}
                        </Stack>
                      </Table.Td>
                      <Table.Td>
                        <Text size="sm">{file.mime ?? file.type ?? "—"}</Text>
                      </Table.Td>
                      <Table.Td>
                        <Text size="sm">{formatBytes(file.size)}</Text>
                      </Table.Td>
                      <Table.Td>
                        <Text size="sm">
                          {file.width && file.height
                            ? `${file.width}×${file.height}`
                            : "—"}
                        </Text>
                      </Table.Td>
                      <Table.Td>
                        {file.published ? (
                          <Badge variant="light" color="pine">
                            <Trans>Public</Trans>
                          </Badge>
                        ) : (
                          <Badge variant="light" color="gray">
                            <Trans>Private</Trans>
                          </Badge>
                        )}
                      </Table.Td>
                      <Table.Td>
                        <Text size="sm">{formatDateTime(file.createdAt)}</Text>
                      </Table.Td>
                      <Table.Td onClick={(e) => e.stopPropagation()}>
                        <Group gap={4} wrap="nowrap">
                          <Tooltip label={t`Open file`}>
                            <ActionIcon
                              variant="subtle"
                              loading={openingId === file.id}
                              onClick={() => void openFile(file.id)}
                              aria-label={t`Open file`}
                            >
                              <IconExternalLink size={16} />
                            </ActionIcon>
                          </Tooltip>
                          <Button
                            component={Link}
                            to={to}
                            size="compact-xs"
                            variant="subtle"
                          >
                            <Trans>Details</Trans>
                          </Button>
                        </Group>
                      </Table.Td>
                    </Table.Tr>
                  );
                })}
              </Table.Tbody>
            </Table>
          </Table.ScrollContainer>
          <Pager
            limit={LIMIT}
            offset={offset}
            count={files.length}
            pagination={data?.pagination}
            onChange={(next) =>
              commit({ ...params, offset: next ? String(next) : undefined })
            }
          />
        </QueryState>
      </Paper>
    </Stack>
  );
}
