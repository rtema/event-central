import { Trans, useLingui } from "@lingui/react/macro";
import { ActionIcon, Badge, Code, Table, Text, Tooltip } from "@mantine/core";
import { IconExternalLink, IconPhoto, IconTypography } from "@tabler/icons-react";
import type { DocumentTemplateFile } from "../../api/types";
import { formatDateTime } from "../utils/datetime";
import { useOpenFile } from "../files/useFileActions";

interface TemplateFilesTableProps {
  files: DocumentTemplateFile[];
  /** Show the owning template column (used in the global list). */
  showTemplate?: boolean;
}

function TypeBadge({ type }: { type?: DocumentTemplateFile["type"] }) {
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

export function DocumentTemplateFilesTable({ files, showTemplate }: TemplateFilesTableProps) {
  const { t } = useLingui();
  const { openFile, openingId } = useOpenFile();

  return (
    <Table.ScrollContainer minWidth={showTemplate ? 760 : 620}>
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
            {showTemplate && (
              <Table.Th>
                <Trans>Template</Trans>
              </Table.Th>
            )}
            <Table.Th>
              <Trans>Created</Trans>
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
              {showTemplate && (
                <Table.Td>
                  <Text size="xs" c="dimmed" ff="monospace" truncate maw={180}>
                    {f.documentTemplateId ?? "—"}
                  </Text>
                </Table.Td>
              )}
              <Table.Td>
                <Text size="sm">{formatDateTime(f.createdAt)}</Text>
              </Table.Td>
              <Table.Td>
                {f.fileId && (
                  <Tooltip label={t`Open file`}>
                    <ActionIcon
                      variant="subtle"
                      loading={openingId === f.fileId}
                      onClick={() => void openFile(f.fileId!)}
                      aria-label={t`Open file`}
                    >
                      <IconExternalLink size={16} />
                    </ActionIcon>
                  </Tooltip>
                )}
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </Table.ScrollContainer>
  );
}
