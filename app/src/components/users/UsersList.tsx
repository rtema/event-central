import { Trans, useLingui } from "@lingui/react/macro";
import {
  Button,
  Group,
  Modal,
  Paper,
  SimpleGrid,
  Stack,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { useForm } from "@mantine/form";
import { notifications } from "@mantine/notifications";
import { IconPlus, IconUserPlus } from "@tabler/icons-react";
import { useState } from "react";
import { useNavigate } from "react-router";
import { toRequestError } from "../../api/client";
import { usersApi } from "../../api/users";
import { QueryState } from "../ui/QueryState";
import { useUserMutations, useUsers } from "../users/userHooks";
import { UsersTable } from "../users/UsersTable";

function CreateUserModal({
  opened,
  onClose,
}: {
  opened: boolean;
  onClose: () => void;
}) {
  const { t, i18n } = useLingui();
  const navigate = useNavigate();
  const { revalidateUser } = useUserMutations("");
  const [saving, setSaving] = useState(false);

  const form = useForm({
    initialValues: {
      email: "",
      salutation: "",
      title: "",
      firstName: "",
      lastName: "",
    },
    validate: {
      email: (v) => (/^\S+@\S+$/.test(v) ? null : t`Enter a valid email`),
      firstName: (v) => (v.trim() ? null : t`First name is required`),
      lastName: (v) => (v.trim() ? null : t`Last name is required`),
    },
  });

  const onSubmit = async () => {
    if (form.validate().hasErrors) return;
    setSaving(true);
    try {
      const created = await usersApi.create({
        email: form.values.email,
        salutation: form.values.salutation || undefined,
        title: form.values.title || undefined,
        firstName: form.values.firstName,
        lastName: form.values.lastName,
      });
      revalidateUser();
      notifications.show({
        color: "pine",
        title: t`User created`,
        message: `${created.firstName} ${created.lastName}`,
      });
      form.reset();
      onClose();
      navigate(`/${i18n.locale}/users/${created.id}`);
    } catch (err) {
      notifications.show({
        color: "red",
        title: t`Could not create user`,
        message: toRequestError(err).message,
      });
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal opened={opened} onClose={onClose} title={t`New user`} centered>
      <Stack>
        <SimpleGrid cols={{ base: 1, sm: 2 }}>
          <TextInput
            label={t`Salutation`}
            placeholder={t`e.g. Mr, Ms`}
            {...form.getInputProps("salutation")}
          />
          <TextInput
            label={t`Title`}
            placeholder={t`e.g. Dr.`}
            {...form.getInputProps("title")}
          />
          <TextInput
            label={t`First name`}
            withAsterisk
            {...form.getInputProps("firstName")}
          />
          <TextInput
            label={t`Last name`}
            withAsterisk
            {...form.getInputProps("lastName")}
          />
        </SimpleGrid>
        <TextInput
          label={t`Email`}
          withAsterisk
          placeholder="name@tema.de"
          {...form.getInputProps("email")}
        />
        <Group justify="flex-end" mt="sm">
          <Button variant="default" onClick={onClose}>
            <Trans>Cancel</Trans>
          </Button>
          <Button loading={saving} onClick={() => void onSubmit()}>
            <Trans>Create user</Trans>
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}

export function UsersList() {
  const { data, error, isLoading } = useUsers();
  const [open, setOpen] = useState(false);

  return (
    <Stack>
      <Group justify="space-between" align="flex-end">
        <Stack gap={2}>
          <Title order={1}>
            <Trans>Users</Trans>
          </Title>
          <Text size="sm" c="dimmed">
            <Trans>Manage accounts, sign-in methods and access.</Trans>
          </Text>
        </Stack>
        <Button leftSection={<IconPlus size={16} />} onClick={() => setOpen(true)}>
          <Trans>New user</Trans>
        </Button>
      </Group>

      <Paper withBorder radius="md" p="md">
        <QueryState
          isLoading={isLoading}
          error={error}
          isEmpty={(data?.length ?? 0) === 0}
          empty={
            <Stack align="center" gap="xs" c="dimmed">
              <IconUserPlus size={32} />
              <Text size="sm">
                <Trans>No users yet. Create the first one.</Trans>
              </Text>
            </Stack>
          }
        >
          <UsersTable users={data ?? []} />
        </QueryState>
      </Paper>

      <CreateUserModal opened={open} onClose={() => setOpen(false)} />
    </Stack>
  );
}
