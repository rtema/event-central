import {
  AppShell,
  Avatar,
  Box,
  Burger,
  Group,
  Menu,
  NavLink,
  ScrollArea,
  Text,
  ThemeIcon,
  Title,
  UnstyledButton,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import {
  IconLogout,
  IconReceipt2,
  IconUsers,
} from "@tabler/icons-react";
import { Trans, useLingui } from "@lingui/react/macro";
import { NavLink as RouterNavLink, Outlet, useLocation, useNavigate } from "react-router";
import { useAuth } from "../auth/useAuth";
import { ColorSchemeToggle } from "./ColorSchemeToggle";
import { LanguageSwitcher } from "./LanguageSwitcher";

export function AppLayout() {
  const [opened, { toggle, close }] = useDisclosure();
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const { t } = useLingui();

  const handleLogout = async () => {
    await logout();
    navigate("/login", { replace: true });
  };

  const initials =
    (user?.name ?? user?.email ?? "?")
      .split(/\s+/)
      .map((p: string) => p[0])
      .slice(0, 2)
      .join("")
      .toUpperCase() || "?";

  return (
    <AppShell
      header={{ height: 60 }}
      navbar={{ width: 248, breakpoint: "sm", collapsed: { mobile: !opened } }}
      padding="lg"
    >
      <AppShell.Header>
        <Group h="100%" px="md" justify="space-between">
          <Group gap="sm">
            <Burger opened={opened} onClick={toggle} hiddenFrom="sm" size="sm" />
            <ThemeIcon variant="light" size={34} radius="md">
              <IconReceipt2 size={20} />
            </ThemeIcon>
            <Box>
              <Title order={3} lh={1}>
                Event Central
              </Title>
              <Text size="xs" c="dimmed" lh={1}>
                <Trans>User administration</Trans>
              </Text>
            </Box>
          </Group>

          <Group gap="xs">
            <LanguageSwitcher />
            <ColorSchemeToggle />
            <Menu position="bottom-end" withinPortal>
              <Menu.Target>
                <UnstyledButton aria-label={t`Account menu`}>
                  <Group gap="xs">
                    <Avatar color="pine" radius="xl" size={32}>
                      {initials}
                    </Avatar>
                  </Group>
                </UnstyledButton>
              </Menu.Target>
              <Menu.Dropdown>
                <Menu.Label>
                  {user?.name ?? user?.email ?? t`Signed in`}
                </Menu.Label>
                {user?.email && user?.name && (
                  <Menu.Label fw={400}>{user.email}</Menu.Label>
                )}
                <Menu.Divider />
                <Menu.Item
                  color="red"
                  leftSection={<IconLogout size={16} />}
                  onClick={() => void handleLogout()}
                >
                  <Trans>Sign out</Trans>
                </Menu.Item>
              </Menu.Dropdown>
            </Menu>
          </Group>
        </Group>
      </AppShell.Header>

      <AppShell.Navbar p="sm">
        <AppShell.Section grow component={ScrollArea}>
          <NavLink
            component={RouterNavLink}
            to="/users"
            label={<Trans>Users</Trans>}
            leftSection={<IconUsers size={18} />}
            active={location.pathname.startsWith("/users")}
            onClick={close}
          />
        </AppShell.Section>
        <AppShell.Section>
          <Text size="xs" c="dimmed" ta="center">
            Event Central · v1.0.0
          </Text>
        </AppShell.Section>
      </AppShell.Navbar>

      <AppShell.Main>
        <Outlet />
      </AppShell.Main>
    </AppShell>
  );
}
