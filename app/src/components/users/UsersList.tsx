import { Trans, useLingui } from "@lingui/react/macro";
import {
  Badge,
  Button,
  Group,
  Modal,
  MultiSelect,
  Paper,
  SimpleGrid,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { useForm } from "@mantine/form";
import { useDebouncedValue } from "@mantine/hooks";
import { notifications } from "@mantine/notifications";
import { IconPlus, IconSearch, IconUserPlus, IconX } from "@tabler/icons-react";
import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router";
import { toRequestError } from "../../api/client";
import type {
  User,
  UserSalutation,
  UserSearchParams,
  UserTitle,
} from "../../api/types";
import { usersApi } from "../../api/users";
import { Pager } from "../ui/Pager";
import { QueryState } from "../ui/QueryState";
import { formatDate } from "../utils/datetime";
import { saveListQuery } from "../utils/listQuery";
import { useUserMutations, useUserSearch } from "./userHooks";
import { hasActiveFilters, paramsFromUrl, paramsToUrl } from "./userSearchParams";

const LIMIT = 100;

function displayName(u: User): string {
  return (
    [u.title, u.firstName, u.lastName].filter(Boolean).join(" ") || u.email
  );
}

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
  const { t, i18n } = useLingui();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [open, setOpen] = useState(false);

  // The address bar is the source of truth for all filters.
  const params = useMemo(() => paramsFromUrl(searchParams), [searchParams]);

  // Mirror the canonical query into localStorage so the "Back to users" link on
  // detail pages can return to this exact filtered view.
  useEffect(() => {
    saveListQuery("users", paramsToUrl(params));
  }, [params]);

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
  const { data, error, isLoading } = useUserSearch({ ...params, limit: LIMIT });
  const users = data?.data ?? [];

  // Any change resets pagination unless an explicit offset is supplied.
  function commit(next: UserSearchParams) {
    setSearchParams(paramsToUrl(next), { replace: true });
  }

  const activeFilters = hasActiveFilters(params);

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
        <Group align="flex-end" wrap="wrap" gap="sm">
          <TextInput
            label={t`Search`}
            placeholder={t`Name or email…`}
            leftSection={<IconSearch size={16} />}
            value={qInput}
            onChange={(e) => setQInput(e.currentTarget.value)}
            style={{ flex: "1 1 240px" }}
          />
          <MultiSelect
            label={t`Title`}
            placeholder={params.title?.length ? undefined : t`Any`}
            data={[
              { value: "dr", label: t`Dr.` },
              { value: "dr-ing", label: t`Dr.-Ing.` },
              { value: "prof", label: t`Prof.` },
              { value: "prof-dr", label: t`Prof. Dr.` },
              { value: "prof-dr-ing", label: t`Prof. Dr.-Ing.` },
              { value: "phd", label: t`PhD` },
            ]}
            value={params.title ?? []}
            onChange={(v) =>
              commit({ ...params, title: v as UserTitle[], offset: undefined })
            }
            clearable
            style={{ flex: "1 1 200px" }}
          />
          <MultiSelect
            label={t`Salutation`}
            placeholder={params.salutation?.length ? undefined : t`Any`}
            data={[
              { value: "mr", label: t`Mr` },
              { value: "ms", label: t`Ms` },
              { value: "mx", label: t`Mx` },
            ]}
            value={params.salutation ?? []}
            onChange={(v) =>
              commit({
                ...params,
                salutation: v as UserSalutation[],
                offset: undefined,
              })
            }
            clearable
            style={{ flex: "1 1 160px" }}
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
      </Paper>

      <Paper withBorder radius="md" p="md">
        <QueryState
          isLoading={isLoading}
          error={error}
          isEmpty={users.length === 0}
          empty={
            <Stack align="center" gap="xs" c="dimmed">
              <IconUserPlus size={32} />
              <Text size="sm">
                {activeFilters ? (
                  <Trans>No users match these filters.</Trans>
                ) : (
                  <Trans>No users yet. Create the first one.</Trans>
                )}
              </Text>
            </Stack>
          }
        >
          <Pager
            limit={LIMIT}
            offset={offset}
            count={users.length}
            pagination={data?.pagination}
            onChange={(next) =>
              commit({ ...params, offset: next ? String(next) : undefined })
            }
          />
          <Table.ScrollContainer minWidth={640}>
            <Table verticalSpacing="sm" highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>
                    <Trans>Name</Trans>
                  </Table.Th>
                  <Table.Th>
                    <Trans>Email</Trans>
                  </Table.Th>
                  <Table.Th>
                    <Trans>Created</Trans>
                  </Table.Th>
                  <Table.Th>
                    <Trans>Status</Trans>
                  </Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {users.map((user) => (
                  <Table.Tr
                    key={user.id}
                    style={{ cursor: "pointer" }}
                    onClick={() => navigate(`/${i18n.locale}/users/${user.id}`)}
                  >
                    <Table.Td>
                      <Text size="sm" fw={500}>
                        {displayName(user)}
                      </Text>
                    </Table.Td>
                    <Table.Td>
                      <Text size="sm" c="dimmed">
                        {user.email}
                      </Text>
                    </Table.Td>
                    <Table.Td>
                      <Text size="sm">{formatDate(user.createdAt)}</Text>
                    </Table.Td>
                    <Table.Td>
                      {user.deletedAt ? (
                        <Badge color="gray" variant="light">
                          <Trans>Deleted</Trans>
                        </Badge>
                      ) : (
                        <Badge color="pine" variant="light">
                          <Trans>Active</Trans>
                        </Badge>
                      )}
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Table.ScrollContainer>
        </QueryState>
      </Paper>

      <CreateUserModal opened={open} onClose={() => setOpen(false)} />
    </Stack>
  );
}
