import { Trans, useLingui } from "@lingui/react/macro";
import {
  Button,
  Group,
  SimpleGrid,
  Stack,
  TextInput,
} from "@mantine/core";
import { useForm } from "@mantine/form";
import { notifications } from "@mantine/notifications";
import { IconDeviceFloppy } from "@tabler/icons-react";
import { useEffect, useState } from "react";
import { toRequestError } from "../../../api/client";
import type { User } from "../../../api/types";
import { usersApi } from "../../../api/users";
import { useUserMutations } from "../../users/userHooks";

export function ProfileTab({ user }: { user: User }) {
  const { t } = useLingui();
  const { revalidateUser } = useUserMutations(user.id);
  const [saving, setSaving] = useState(false);
  const disabled = Boolean(user.deletedAt);

  const form = useForm({
    initialValues: {
      email: user.email ?? "",
      title: user.title ?? "",
      salutation: user.salutation ?? "",
      firstName: user.firstName ?? "",
      lastName: user.lastName ?? "",
    },
    validate: {
      email: (v) => (/^\S+@\S+$/.test(v) ? null : t`Enter a valid email`),
      firstName: (v) => (v.trim() ? null : t`First name is required`),
      lastName: (v) => (v.trim() ? null : t`Last name is required`),
    },
  });

  // Re-sync the form if the underlying user changes (e.g. cross-tab edit).
  useEffect(() => {
    form.setValues({
      email: user.email ?? "",
      title: user.title ?? "",
      salutation: user.salutation ?? "",
      firstName: user.firstName ?? "",
      lastName: user.lastName ?? "",
    });
    form.resetDirty();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user.id, user.email, user.title, user.salutation, user.firstName, user.lastName]);

  const onSubmit = async () => {
    if (form.validate().hasErrors) return;
    setSaving(true);
    try {
      await usersApi.update(user.id, {
        email: form.values.email,
        title: form.values.title || undefined,
        salutation: form.values.salutation || undefined,
        firstName: form.values.firstName,
        lastName: form.values.lastName,
      });
      revalidateUser();
      form.resetDirty();
      notifications.show({
        color: "pine",
        title: t`Saved`,
        message: t`Profile updated successfully.`,
      });
    } catch (err) {
      notifications.show({
        color: "red",
        title: t`Could not save`,
        message: toRequestError(err).message,
      });
    } finally {
      setSaving(false);
    }
  };

  return (
    <Stack maw={620}>
      <SimpleGrid cols={{ base: 1, sm: 2 }}>
        <TextInput
          label={t`Salutation`}
          placeholder={t`e.g. Mr, Ms`}
          disabled={disabled}
          {...form.getInputProps("salutation")}
        />
        <TextInput
          label={t`Title`}
          placeholder={t`e.g. Dr.`}
          disabled={disabled}
          {...form.getInputProps("title")}
        />
        <TextInput
          label={t`First name`}
          withAsterisk
          disabled={disabled}
          {...form.getInputProps("firstName")}
        />
        <TextInput
          label={t`Last name`}
          withAsterisk
          disabled={disabled}
          {...form.getInputProps("lastName")}
        />
      </SimpleGrid>
      <TextInput
        label={t`Email`}
        withAsterisk
        disabled={disabled}
        {...form.getInputProps("email")}
      />
      <Group justify="flex-end">
        <Button
          leftSection={<IconDeviceFloppy size={16} />}
          loading={saving}
          disabled={disabled || !form.isDirty()}
          onClick={() => void onSubmit()}
        >
          <Trans>Save changes</Trans>
        </Button>
      </Group>
    </Stack>
  );
}
