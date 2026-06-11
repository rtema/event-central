import {
  Anchor,
  Badge,
  Button,
  Group,
  Paper,
  Stack,
  Tabs,
  Text,
  Title,
} from "@mantine/core";
import { modals } from "@mantine/modals";
import { notifications } from "@mantine/notifications";
import {
  IconArrowLeft,
  IconClockHour4,
  IconDatabaseCog,
  IconKey,
  IconRestore,
  IconShieldLock,
  IconTrash,
  IconUser,
} from "@tabler/icons-react";
import { Trans, useLingui } from "@lingui/react/macro";
import { Link, useParams } from "react-router";
import { usersApi } from "../../api/users";
import { toRequestError } from "../../api/client";
import { useUser, useUserMutations } from "../users/userHooks";
import { QueryState } from "../ui/QueryState";
import { formatDateTime } from "../utils/datetime";
import { ProfileTab } from "./user-detail/ProfileTab";
import { AuthMethodsTab } from "./user-detail/AuthMethodsTab";
import { ScopesTab } from "./user-detail/ScopesTab";
import { DataTab } from "./user-detail/DataTab";
import { HistoryTab } from "./user-detail/HistoryTab";

export function UserDetailPage() {
  const { t } = useLingui();
  const { userId = "" } = useParams();
  const { data: user, error, isLoading } = useUser(userId);
  const { revalidateUser } = useUserMutations(userId);

  const fullName = user
    ? [user.title, user.firstName, user.lastName].filter(Boolean).join(" ")
    : "";
  const deleted = Boolean(user?.deletedAt);

  const onDelete = () =>
    modals.openConfirmModal({
      title: t`Delete user`,
      children: (
        <Text size="sm">
          <Trans>
            This soft-deletes {fullName || user?.email}. They can be restored
            later.
          </Trans>
        </Text>
      ),
      labels: { confirm: t`Delete`, cancel: t`Cancel` },
      confirmProps: { color: "red" },
      onConfirm: async () => {
        try {
          await usersApi.remove(userId);
          revalidateUser();
          notifications.show({
            color: "pine",
            title: t`User deleted`,
            message: fullName || user?.email,
          });
        } catch (err) {
          notifications.show({
            color: "red",
            title: t`Could not delete`,
            message: toRequestError(err).message,
          });
        }
      },
    });

  const onRestore = async () => {
    try {
      await usersApi.restore(userId);
      revalidateUser();
      notifications.show({
        color: "pine",
        title: t`User restored`,
        message: fullName || user?.email,
      });
    } catch (err) {
      notifications.show({
        color: "red",
        title: t`Could not restore`,
        message: toRequestError(err).message,
      });
    }
  };

  return (
    <Stack>
      <Anchor component={Link} to="/users" size="sm">
        <Group gap={4}>
          <IconArrowLeft size={14} />
          <Trans>Back to users</Trans>
        </Group>
      </Anchor>

      <QueryState isLoading={isLoading} error={error}>
        {user && (
          <>
            <Paper withBorder p="lg" radius="md">
              <Group justify="space-between" align="flex-start">
                <Stack gap={4}>
                  <Group gap="sm">
                    <Title order={2}>{fullName || user.email}</Title>
                    {deleted ? (
                      <Badge color="gray" variant="light">
                        <Trans>Deleted</Trans>
                      </Badge>
                    ) : (
                      <Badge color="pine" variant="light">
                        <Trans>Active</Trans>
                      </Badge>
                    )}
                  </Group>
                  <Text size="sm" c="dimmed">
                    {user.email}
                  </Text>
                  <Text size="xs" c="dimmed">
                    <Trans>Created</Trans> {formatDateTime(user.createdAt)}
                    {deleted && (
                      <>
                        {" · "}
                        <Trans>Deleted</Trans> {formatDateTime(user.deletedAt)}
                      </>
                    )}
                  </Text>
                </Stack>
                {deleted ? (
                  <Button
                    variant="light"
                    leftSection={<IconRestore size={16} />}
                    onClick={() => void onRestore()}
                  >
                    <Trans>Restore</Trans>
                  </Button>
                ) : (
                  <Button
                    variant="light"
                    color="red"
                    leftSection={<IconTrash size={16} />}
                    onClick={onDelete}
                  >
                    <Trans>Delete</Trans>
                  </Button>
                )}
              </Group>
            </Paper>

            <Tabs defaultValue="profile" keepMounted={false}>
              <Tabs.List>
                <Tabs.Tab value="profile" leftSection={<IconUser size={16} />}>
                  <Trans>Profile</Trans>
                </Tabs.Tab>
                <Tabs.Tab value="auth" leftSection={<IconKey size={16} />}>
                  <Trans>Auth methods</Trans>
                </Tabs.Tab>
                <Tabs.Tab
                  value="scopes"
                  leftSection={<IconShieldLock size={16} />}
                >
                  <Trans>Scopes</Trans>
                </Tabs.Tab>
                <Tabs.Tab
                  value="data"
                  leftSection={<IconDatabaseCog size={16} />}
                >
                  <Trans>Data</Trans>
                </Tabs.Tab>
                <Tabs.Tab
                  value="history"
                  leftSection={<IconClockHour4 size={16} />}
                >
                  <Trans>History</Trans>
                </Tabs.Tab>
              </Tabs.List>

              <Tabs.Panel value="profile" pt="lg">
                <ProfileTab user={user} />
              </Tabs.Panel>
              <Tabs.Panel value="auth" pt="lg">
                <AuthMethodsTab userId={userId} />
              </Tabs.Panel>
              <Tabs.Panel value="scopes" pt="lg">
                <ScopesTab userId={userId} disabled={deleted} />
              </Tabs.Panel>
              <Tabs.Panel value="data" pt="lg">
                <DataTab userId={userId} disabled={deleted} />
              </Tabs.Panel>
              <Tabs.Panel value="history" pt="lg">
                <HistoryTab userId={userId} />
              </Tabs.Panel>
            </Tabs>
          </>
        )}
      </QueryState>
    </Stack>
  );
}
