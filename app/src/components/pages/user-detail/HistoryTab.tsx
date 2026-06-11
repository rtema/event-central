import { Group, Stack, Text, Timeline } from "@mantine/core";
import { IconPencil, IconUserPlus } from "@tabler/icons-react";
import { Trans, useLingui } from "@lingui/react/macro";
import { useUserHistory } from "../../users/userHooks";
import { QueryState } from "../../ui/QueryState";
import { formatDateTime } from "../../utils/datetime";
import type { UserHistoryItem } from "../../../api/types";

const FIELD_KEYS: (keyof UserHistoryItem["newState"])[] = [
  "salutation",
  "title",
  "firstName",
  "lastName",
  "email",
];

export function HistoryTab({ userId }: { userId: string }) {
  const { t } = useLingui();
  const { data, error, isLoading } = useUserHistory(userId);

  const labels: Record<string, string> = {
    salutation: t`Salutation`,
    title: t`Title`,
    firstName: t`First name`,
    lastName: t`Last name`,
    email: t`Email`,
  };

  // Server returns history ordered; the last item is the earliest change.
  const items = data ?? [];

  return (
    <QueryState isLoading={isLoading} error={error} isEmpty={items.length === 0}>
      <Timeline active={items.length} bulletSize={26} lineWidth={2}>
        {items.map((item, idx) => {
          const isCreation = idx === items.length - 1;
          return (
            <Timeline.Item
              key={item.id}
              bullet={
                isCreation ? (
                  <IconUserPlus size={14} />
                ) : (
                  <IconPencil size={14} />
                )
              }
              title={
                <Group gap="xs">
                  <Text size="sm" fw={600}>
                    {isCreation ? (
                      <Trans>User created</Trans>
                    ) : (
                      <Trans>Profile updated</Trans>
                    )}
                  </Text>
                </Group>
              }
            >
              <Text size="xs" c="dimmed" mb={6}>
                {formatDateTime(item.createdAt)}
                {item.changedBy ? ` · ${item.changedBy}` : ""}
              </Text>
              <Stack gap={2}>
                {FIELD_KEYS.filter((k) => item.newState[k] != null).map((k) => (
                  <Text size="sm" key={k}>
                    <Text span c="dimmed">
                      {labels[k]}:
                    </Text>{" "}
                    {item.newState[k]}
                  </Text>
                ))}
              </Stack>
            </Timeline.Item>
          );
        })}
      </Timeline>
    </QueryState>
  );
}
