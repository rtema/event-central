import { Trans, useLingui } from "@lingui/react/macro";
import {
  ActionIcon,
  Anchor,
  Badge,
  Group,
  Paper,
  Stack,
  Table,
  Text,
  Title,
  Tooltip,
} from "@mantine/core";
import { IconArrowLeft, IconExternalLink, IconPaperclip } from "@tabler/icons-react";
import { Link, useParams } from "react-router";
import {
  useEmail,
  useEmailAttachments,
  useEmailSender,
  useEmailTemplate,
} from "../../api/hooks";
import { FieldGrid } from "../ui/FieldGrid";
import { QueryState } from "../ui/QueryState";
import { formatDateTime } from "../utils/datetime";
import { localizedLabel } from "../utils/format";
import { listLinkWithFilters } from "../utils/listQuery";
import { useOpenFile } from "../files/useFileActions";
import { EmailStatusBadge } from "./EmailStatusBadge";

function AddressList({ label, values }: { label: React.ReactNode; values?: string[] }) {
  if (!values?.length) return null;
  return (
    <Stack gap={2}>
      <Text size="xs" tt="uppercase" fw={600} c="dimmed">
        {label}
      </Text>
      <Text size="sm">{values.join(", ")}</Text>
    </Stack>
  );
}

export function EmailDetail() {
  const { t, i18n } = useLingui();
  const { emailId = "" } = useParams();
  const { data: email, error, isLoading } = useEmail(emailId);
  const { data: attachments } = useEmailAttachments(emailId);
  const { data: template } = useEmailTemplate(email?.emailTemplateId);
  const { data: sender } = useEmailSender(email?.emailSenderId);
  const { openFile, openingId } = useOpenFile();

  const attachmentList = attachments ?? [];

  return (
    <Stack maw={1280} mx="auto" w="100%">
      <Anchor
        component={Link}
        to={listLinkWithFilters(`/${i18n.locale}/emails`, "emails")}
        size="sm"
      >
        <Group gap={4}>
          <IconArrowLeft size={14} />
          <Trans>Back to emails</Trans>
        </Group>
      </Anchor>

      <QueryState isLoading={isLoading} error={error}>
        {email && (
          <>
            <Paper withBorder p="lg" radius="md">
              <Group justify="space-between" align="flex-start">
                <Stack gap={4}>
                  <Title order={2}>{email.subject || t`(no subject)`}</Title>
                  <Group gap="xs">
                    <EmailStatusBadge status={email.status} />
                    <Badge variant="light" color="gray">
                      {email.locale?.toUpperCase()}
                    </Badge>
                  </Group>
                </Stack>
              </Group>

              <Stack gap="sm" mt="md">
                <AddressList label={t`To`} values={email.to} />
                <AddressList label={t`Cc`} values={email.cc} />
                <AddressList label={t`Bcc`} values={email.bcc} />
              </Stack>
            </Paper>

            <Paper withBorder p="lg" radius="md">
              <Title order={4} mb="md">
                <Trans>Delivery</Trans>
              </Title>
              <FieldGrid
                cols={{ base: 1, sm: 3 }}
                fields={[
                  {
                    label: t`Sender`,
                    value: sender
                      ? sender.fromName
                        ? `${sender.fromName} · ${sender.fromEmail}`
                        : sender.fromEmail
                      : email.sender,
                  },
                  {
                    label: t`Template`,
                    value: template ? (
                      <Anchor
                        component={Link}
                        to={`/${i18n.locale}/email-templates/${email.emailTemplateId}`}
                        size="sm"
                      >
                        {localizedLabel(template.label)}
                      </Anchor>
                    ) : (
                      email.emailTemplateId
                    ),
                  },
                  { label: t`Retries`, value: String(email.retries ?? 0) },
                  {
                    label: t`Scheduled`,
                    value: formatDateTime(email.scheduledAt),
                  },
                  {
                    label: t`Send after`,
                    value: formatDateTime(email.sendAfter),
                  },
                  {
                    label: t`Delivered`,
                    value: formatDateTime(email.deliveredAt),
                  },
                  { label: t`Created`, value: formatDateTime(email.createdAt) },
                  { label: t`Created by`, value: email.createdBy },
                  {
                    label: t`Server response`,
                    value: email.serverResponse,
                    full: true,
                  },
                ]}
              />
            </Paper>

            {attachmentList.length > 0 && (
              <Paper withBorder p="lg" radius="md">
                <Group gap="xs" mb="md">
                  <IconPaperclip size={18} />
                  <Title order={4}>
                    <Trans>Attachments</Trans>
                  </Title>
                </Group>
                <Table verticalSpacing="sm" highlightOnHover>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>
                        <Trans>File</Trans>
                      </Table.Th>
                      <Table.Th />
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {attachmentList.map((a) => (
                      <Table.Tr key={a.id}>
                        <Table.Td>
                          <Text size="sm">{a.fileName}</Text>
                        </Table.Td>
                        <Table.Td>
                          <Group justify="flex-end">
                            <Tooltip label={t`Open file`}>
                              <ActionIcon
                                variant="subtle"
                                loading={openingId === a.fileId}
                                onClick={() => void openFile(a.fileId)}
                                aria-label={t`Open file`}
                              >
                                <IconExternalLink size={16} />
                              </ActionIcon>
                            </Tooltip>
                          </Group>
                        </Table.Td>
                      </Table.Tr>
                    ))}
                  </Table.Tbody>
                </Table>
              </Paper>
            )}

            <Paper withBorder p="sm" radius="md">
              <Text size="sm" fw={500} mb="xs">
                <Trans>Rendered body</Trans>
              </Text>
              <iframe
                title={t`Email body`}
                srcDoc={email.body}
                sandbox=""
                style={{
                  width: "100%",
                  height: 640,
                  border: "1px solid var(--mantine-color-default-border)",
                  borderRadius: 8,
                  background: "#ffffff",
                }}
              />
            </Paper>
          </>
        )}
      </QueryState>
    </Stack>
  );
}
