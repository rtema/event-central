import { Trans, useLingui } from "@lingui/react/macro";
import {
  Badge,
  Button,
  Checkbox,
  Chip,
  Group,
  Stack,
  Table,
  Text,
  TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconDeviceFloppy, IconSearch } from "@tabler/icons-react";
import { Fragment, useEffect, useMemo, useState } from "react";
import { toRequestError } from "../../api/client";
import type { MultiLanguageLabel } from "../../api/types";
import { usersApi } from "../../api/users";
import { QueryState } from "../ui/QueryState";
import { useScopes, useUserScopes } from "./userHooks";

type ScopeRow = {
  scope: string;
  label: string | null; // human-readable label, null when identical to the scope id
};

type QualifierRow = {
  qualifier: string | null; // e.g. "all", "own", "{eventId}", or null (no qualifier)
  cells: Map<string, ScopeRow>; // action -> scope
  scopes: string[];
};

type ResourceGroup = {
  resource: string; // e.g. "invoices"
  qualifiers: QualifierRow[];
  scopes: string[]; // every scope across all qualifiers
};

// Scope ids look like `resource:action[:qualifier]`, e.g. `invoices:read:own`
// or `backend:read`. The ACTION is always the second segment (a column); the
// resource groups the section and the optional qualifier identifies the row.
function parseScope(scope: string) {
  const parts = scope.split(":");
  if (parts.length < 2) return null; // no action segment -> ungrouped
  const [resource, action, ...rest] = parts;
  if (!resource || !action) return null;
  return { resource, action, qualifier: rest.join(":") || null };
}

// Column order for the familiar actions; anything unknown sorts after them.
const ACTION_ORDER = ["read", "list", "write", "create", "update", "delete", "manage", "admin"];
// Qualifier row order within a resource.
const QUALIFIER_ORDER = ["all", "own"];

function actionRank(a: string) {
  const i = ACTION_ORDER.indexOf(a);
  return i === -1 ? ACTION_ORDER.length : i;
}
function qualRank(q: string | null) {
  if (q === null) return -1; // bare (no qualifier) first
  const i = QUALIFIER_ORDER.indexOf(q);
  return i === -1 ? QUALIFIER_ORDER.length : i; // templated ids last
}

// Color-code the qualifier so scanning a resource block is fast.
function qualifierBadge(q: string): { color: string; label: string } {
  if (q.includes("{")) return { color: "orange", label: q }; // templated, e.g. {eventId}
  if (q === "all") return { color: "blue", label: q };
  if (q === "own") return { color: "grape", label: q };
  return { color: "cyan", label: q };
}

export function UserScopesTab({
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
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [query, setQuery] = useState("");

  // Active scopes are those that have not been revoked (no deletedAt).
  const active = useMemo(
    () => (userScopes.data ?? []).filter((s) => !s.deletedAt).map((s) => s.scope),
    [userScopes.data],
  );

  useEffect(() => {
    setSelected(new Set(active));
    setDirty(false);
  }, [active]);

  const locale = i18n.locale;
  const rows = useMemo<ScopeRow[]>(() => {
    const map = new Map<string, string | null>();
    for (const s of catalog.data ?? []) {
      const label =
        (s.label && s.label[locale as keyof MultiLanguageLabel]) ??
        s.label?.en ??
        s.scope;
      map.set(s.scope, label === s.scope ? null : label);
    }
    // Make sure currently-granted scopes are always listed, even if the
    // catalog doesn't include them.
    for (const s of active) if (!map.has(s)) map.set(s, null);
    return Array.from(map, ([scope, label]) => ({ scope, label }));
  }, [catalog.data, active, locale]);

  // Pivot into resource -> qualifier rows -> action cells, plus an ungrouped bucket.
  const { resources, actions, ungrouped } = useMemo(() => {
    const byResource = new Map<string, Map<string | null, QualifierRow>>();
    const actionSet = new Set<string>();
    const ungroupedRows: ScopeRow[] = [];

    for (const row of rows) {
      const p = parseScope(row.scope);
      if (!p) {
        ungroupedRows.push(row);
        continue;
      }
      actionSet.add(p.action);
      let qualifiers = byResource.get(p.resource);
      if (!qualifiers) {
        qualifiers = new Map();
        byResource.set(p.resource, qualifiers);
      }
      let qr = qualifiers.get(p.qualifier);
      if (!qr) {
        qr = { qualifier: p.qualifier, cells: new Map(), scopes: [] };
        qualifiers.set(p.qualifier, qr);
      }
      qr.cells.set(p.action, row);
      qr.scopes.push(row.scope);
    }

    const sortedActions = Array.from(actionSet).sort(
      (a, b) => actionRank(a) - actionRank(b) || a.localeCompare(b),
    );

    const sortedResources: ResourceGroup[] = Array.from(byResource, ([resource, qualifiers]) => {
      const qualRows = Array.from(qualifiers.values()).sort(
        (a, b) =>
          qualRank(a.qualifier) - qualRank(b.qualifier) ||
          (a.qualifier ?? "").localeCompare(b.qualifier ?? ""),
      );
      return {
        resource,
        qualifiers: qualRows,
        scopes: qualRows.flatMap((q) => q.scopes),
      };
    }).sort((a, b) => a.resource.localeCompare(b.resource));

    return {
      resources: sortedResources,
      actions: sortedActions,
      ungrouped: ungroupedRows.sort((a, b) => a.scope.localeCompare(b.scope)),
    };
  }, [rows]);

  const q = query.trim().toLowerCase();
  const visibleResources = useMemo(() => {
    if (!q) return resources;
    return resources
      .map((rg) => {
        if (rg.resource.toLowerCase().includes(q)) return rg; // whole resource matches
        const qualifiers = rg.qualifiers.filter(
          (ql) =>
            ql.scopes.some((s) => s.toLowerCase().includes(q)) ||
            Array.from(ql.cells.values()).some((c) =>
              c.label?.toLowerCase().includes(q),
            ),
        );
        return { ...rg, qualifiers: qualifiers, scopes: qualifiers.flatMap((x) => x.scopes) };
      })
      .filter((rg) => rg.qualifiers.length > 0);
  }, [resources, q]);

  const visibleUngrouped = useMemo(
    () =>
      !q
        ? ungrouped
        : ungrouped.filter(
          (r) =>
            r.scope.toLowerCase().includes(q) ||
            (r.label?.toLowerCase().includes(q) ?? false),
        ),
    [ungrouped, q],
  );

  const toggle = (scope: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(scope)) next.delete(scope);
      else next.add(scope);
      return next;
    });
    setDirty(true);
  };

  // Toggle a set of scopes at once (a resource, a qualifier row, or an action
  // column): if all are already on, turn them all off, otherwise turn them on.
  const toggleScopes = (scopes: string[]) => {
    if (scopes.length === 0) return;
    setSelected((prev) => {
      const next = new Set(prev);
      const allOn = scopes.every((s) => next.has(s));
      for (const s of scopes) allOn ? next.delete(s) : next.add(s);
      return next;
    });
    setDirty(true);
  };

  // Aggregate checkbox state for any set of scopes.
  const aggregate = (scopes: string[]) => {
    const on = scopes.filter((s) => selected.has(s)).length;
    return {
      checked: scopes.length > 0 && on === scopes.length,
      indeterminate: on > 0 && on < scopes.length,
      empty: scopes.length === 0,
    };
  };

  const columnState = (action: string) => {
    const scopes = visibleResources.flatMap((rg) =>
      rg.qualifiers
        .map((ql) => ql.cells.get(action)?.scope)
        .filter((s): s is string => Boolean(s)),
    );
    return { scopes, ...aggregate(scopes) };
  };

  const onSave = async () => {
    setSaving(true);
    try {
      await usersApi.setScopes(userId, Array.from(selected));
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

  // One action cell, shared between inline (bare) rows and qualifier rows.
  const actionCell = (action: string, cell: ScopeRow | undefined) => {
    if (!cell) {
      return (
        <Table.Td key={action} style={{ textAlign: "center" }}>
          <Text size="sm" c="dimmed">
            —
          </Text>
        </Table.Td>
      );
    }
    const checked = selected.has(cell.scope);
    return (
      <Table.Td
        key={action}
        onClick={() => !disabled && toggle(cell.scope)}
        title={cell.label ?? cell.scope}
        style={{
          cursor: disabled ? "default" : "pointer",
          backgroundColor: checked
            ? "var(--mantine-color-green-light)"
            : undefined,
        }}
      >
        <Group justify="center" gap={0}>
          <Checkbox
            size="sm"
            color="green"
            aria-label={cell.label ? `${cell.scope} — ${cell.label}` : cell.scope}
            checked={checked}
            disabled={disabled}
            onChange={() => toggle(cell.scope)}
            onClick={(e) => e.stopPropagation()}
          />
        </Group>
      </Table.Td>
    );
  };

  const nothingToShow =
    visibleResources.length === 0 && visibleUngrouped.length === 0;

  return (
    <QueryState isLoading={userScopes.isLoading} error={userScopes.error}>
      <Stack maw={760}>
        <Text size="sm" c="dimmed">
          <Trans>
            Select every scope this user should have. Green cells are granted;
            removing a scope here revokes it. The change history is kept on the
            server.
          </Trans>
        </Text>

        <TextInput
          placeholder={t`Search scopes`}
          leftSection={<IconSearch size={16} />}
          value={query}
          onChange={(e) => setQuery(e.currentTarget.value)}
          disabled={disabled}
        />

        {visibleResources.length > 0 && (
          <Table highlightOnHover withTableBorder withColumnBorders verticalSpacing="xs">
            <Table.Thead>
              <Table.Tr>
                <Table.Th>
                  <Trans>Resource</Trans>
                </Table.Th>
                {actions.map((action) => {
                  const st = columnState(action);
                  return (
                    <Table.Th key={action} w={110} style={{ textAlign: "center" }}>
                      <Stack gap={4} align="center">
                        <Text size="sm" fw={600} tt="capitalize">
                          {action}
                        </Text>
                        <Checkbox
                          size="xs"
                          color="green"
                          aria-label={t`Toggle all ${action} scopes`}
                          checked={st.checked}
                          indeterminate={st.indeterminate}
                          disabled={disabled || st.empty}
                          onChange={() => toggleScopes(st.scopes)}
                        />
                      </Stack>
                    </Table.Th>
                  );
                })}
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {visibleResources.map((rg) => {
                const agg = aggregate(rg.scopes);
                // Collapse a resource that has a single bare (no-qualifier) row —
                // e.g. `backend` -> put its read/write cells on the header row.
                const inline =
                  rg.qualifiers.length === 1 && rg.qualifiers[0].qualifier === null;

                const header = (
                  <Table.Tr
                    key={`${rg.resource}:header`}
                    style={{ backgroundColor: "var(--mantine-color-gray-light)" }}
                  >
                    <Table.Td
                      onClick={() => !disabled && toggleScopes(rg.scopes)}
                      style={{ cursor: disabled ? "default" : "pointer" }}
                      title={t`Toggle all ${rg.resource} scopes`}
                    >
                      <Group gap="xs" wrap="nowrap">
                        <Checkbox
                          size="sm"
                          color="green"
                          aria-label={t`Toggle all ${rg.resource} scopes`}
                          checked={agg.checked}
                          indeterminate={agg.indeterminate}
                          disabled={disabled}
                          onChange={() => toggleScopes(rg.scopes)}
                          onClick={(e) => e.stopPropagation()}
                        />
                        <Text size="sm" fw={700} ff="monospace" tt="uppercase">
                          {rg.resource}
                        </Text>
                      </Group>
                    </Table.Td>
                    {inline
                      ? actions.map((action) =>
                        actionCell(action, rg.qualifiers[0].cells.get(action)),
                      )
                      : // spacer so the header stretches across the action columns
                      actions.map((action) => (
                        <Table.Td key={action} />
                      ))}
                  </Table.Tr>
                );

                if (inline) return header;

                return (
                  <Fragment key={rg.resource}>
                    {header}
                    {rg.qualifiers.map((ql) => {
                      const meta = ql.qualifier
                        ? qualifierBadge(ql.qualifier)
                        : null;
                      return (
                        <Table.Tr key={`${rg.resource}:${ql.qualifier}`}>
                          <Table.Td
                            onClick={() => !disabled && toggleScopes(ql.scopes)}
                            style={{
                              cursor: disabled ? "default" : "pointer",
                              paddingLeft: "2.25rem", // indent under the resource
                            }}
                            title={t`Toggle all ${rg.resource} ${ql.qualifier ?? ""
                              } scopes`}
                          >
                            {meta ? (
                              <Badge
                                size="lg"
                                radius="sm"
                                variant="light"
                                color={meta.color}
                                style={{ textTransform: "none" }}
                              >
                                {meta.label}
                              </Badge>
                            ) : (
                              <Text size="sm" c="dimmed">
                                —
                              </Text>
                            )}
                          </Table.Td>
                          {actions.map((action) =>
                            actionCell(action, ql.cells.get(action)),
                          )}
                        </Table.Tr>
                      );
                    })}
                  </Fragment>
                );
              })}
            </Table.Tbody>
          </Table>
        )}

        {visibleUngrouped.length > 0 && (
          <Stack gap="xs">
            <Text size="sm" fw={600}>
              <Trans>Other scopes</Trans>
            </Text>
            <Group gap="xs">
              {visibleUngrouped.map((r) => (
                <Chip
                  key={r.scope}
                  color="green"
                  checked={selected.has(r.scope)}
                  disabled={disabled}
                  onChange={() => toggle(r.scope)}
                  title={r.label ?? r.scope}
                >
                  {r.label ? `${r.scope} — ${r.label}` : r.scope}
                </Chip>
              ))}
            </Group>
          </Stack>
        )}

        {nothingToShow && (
          <Text size="sm" c="dimmed" ta="center" py="sm">
            <Trans>No matching scope</Trans>
          </Text>
        )}

        <Group justify="space-between">
          <Text size="sm" c="dimmed">
            <Trans>{selected.size} selected</Trans>
          </Text>
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