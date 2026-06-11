import { Trans, useLingui } from "@lingui/react/macro";
import {
  Button,
  Group,
  MultiSelect,
  Stack,
  Text,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconDeviceFloppy } from "@tabler/icons-react";
import { useEffect, useMemo, useState } from "react";
import { toRequestError } from "../../../api/client";
import type { MultiLanguageLabel } from "../../../api/types";
import { usersApi } from "../../../api/users";
import { QueryState } from "../../ui/QueryState";
import { useScopes, useUserScopes } from "../../users/userHooks";

export function ScopesTab({
  userId,
  disabled,
}: {
  userId: string;
  disabled?: boolean;
}) {
  const { t } = useLingui();
  const { i18n } = useLingui();
  const userScopes = useUserScopes(userId);
  const catalog = useScopes();
  const [selected, setSelected] = useState<string[]>([]);
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);

  // Active scopes are those that have not been revoked (no deletedAt).
  const active = useMemo(
    () => (userScopes.data ?? []).filter((s) => !s.deletedAt).map((s) => s.scope),
    [userScopes.data],
  );

  useEffect(() => {
    setSelected(active);
    setDirty(false);
  }, [active]);

  const locale = i18n.locale;
  const options = useMemo(() => {
    const map = new Map<string, string>();
    for (const s of catalog.data ?? []) {
      const label = s.label && s.label[locale as keyof MultiLanguageLabel] ?? s.label?.en ?? s.scope;
      map.set(s.scope, label === s.scope ? s.scope : `${s.scope} — ${label}`);
    }
    // Make sure currently-granted scopes are always selectable, even if the
    // catalog doesn't list them (e.g. templated event scopes).
    for (const s of active) if (!map.has(s)) map.set(s, s);
    return Array.from(map, ([value, label]) => ({ value, label }));
  }, [catalog.data, active, locale]);

  const onSave = async () => {
    setSaving(true);
    try {
      await usersApi.setScopes(userId, selected);
      await userScopes.mutate();
      setDirty(false);
      notifications.show({
        color: "pine",
        title: t`Scopes updated`,
        message: t`Access has been updated for this user.`,
      });
    } catch (err) {
      notifications.show({
        color: "red",
        title: t`Could not update scopes`,
        message: toRequestError(err).message,
      });
    } finally {
      setSaving(false);
    }
  };

  return (
    <QueryState isLoading={userScopes.isLoading} error={userScopes.error}>
      <Stack maw={620}>
        <Text size="sm" c="dimmed">
          <Trans>
            Select every scope this user should have. Removing a scope here
            revokes it; the change history is kept on the server.
          </Trans>
        </Text>
        <MultiSelect
          label={t`Granted scopes`}
          placeholder={selected.length === 0 ? t`No scopes granted` : undefined}
          data={options}
          value={selected}
          searchable
          clearable
          disabled={disabled}
          nothingFoundMessage={t`No matching scope`}
          onChange={(v) => {
            setSelected(v);
            setDirty(true);
          }}
        />
        <Group justify="flex-end">
          <Button
            leftSection={<IconDeviceFloppy size={16} />}
            loading={saving}
            disabled={disabled || !dirty}
            onClick={() => void onSave()}
          >
            <Trans>Save scopes</Trans>
          </Button>
        </Group>
      </Stack>
    </QueryState>
  );
}
