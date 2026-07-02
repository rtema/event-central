import { Trans, useLingui } from "@lingui/react/macro";
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
  Title,
  UnstyledButton,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import {
  IconCalendarEvent,
  IconCash,
  IconFileInvoice,
  IconLogout,
  IconPercentage,
  IconShoppingCart,
  IconTemplate,
  IconUsers,
} from "@tabler/icons-react";
import { Outlet, NavLink as RouterNavLink, useLocation, useNavigate } from "react-router";
import { useAuth } from "../auth/useAuth";
import { ColorSchemeToggle } from "./ColorSchemeToggle";
import { LanguageSwitcher } from "./LanguageSwitcher";
import { TemaLogo } from "./TemaLogo";

export function AppLayout() {

  const [opened, { toggle, close }] = useDisclosure();
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const { t } = useLingui();
  const { i18n } = useLingui();

  const handleLogout = async () => {
    await logout();
    navigate(`/${i18n.locale}/login`, { replace: true });
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
            <TemaLogo height={32} />
            <Box>
              <Title order={4} lh={1} fw={650}>
                Event Central
              </Title>
              <Text size="xs" c="dimmed" lh={1}>
                <Trans>E-invoicing console</Trans>
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
                    <Avatar color="tema" radius="xl" size={32}>
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
            to={`/${i18n.locale}/invoices`}
            label={<Trans>Invoices</Trans>}
            leftSection={<IconFileInvoice size={18} />}
            active={location.pathname.startsWith(`/${i18n.locale}/invoices`)}
            onClick={close}
          />
          <NavLink
            component={RouterNavLink}
            to={`/${i18n.locale}/orders`}
            label={<Trans>Orders</Trans>}
            leftSection={<IconShoppingCart size={18} />}
            active={location.pathname.startsWith(`/${i18n.locale}/orders`)}
            onClick={close}
          />
          <NavLink
            component={RouterNavLink}
            to={`/${i18n.locale}/events`}
            label={<Trans>Events</Trans>}
            leftSection={<IconCalendarEvent size={18} />}
            active={location.pathname.startsWith(`/${i18n.locale}/events`)}
            onClick={close}
          />
          <NavLink
            component={RouterNavLink}
            to={`/${i18n.locale}/payments`}
            label={<Trans>Payments</Trans>}
            leftSection={<IconCash size={18} />}
            active={location.pathname.startsWith(`/${i18n.locale}/payments`)}
            onClick={close}
          />
          <NavLink
            component={RouterNavLink}
            to={`/${i18n.locale}/document-templates`}
            label={<Trans>Templates</Trans>}
            leftSection={<IconTemplate size={18} />}
            active={location.pathname.startsWith(`/${i18n.locale}/templates`)}
            onClick={close}
          />
          <NavLink
            component={RouterNavLink}
            to={`/${i18n.locale}/taxes`}
            label={<Trans>Tax rates</Trans>}
            leftSection={<IconPercentage size={18} />}
            active={location.pathname.startsWith(`/${i18n.locale}/taxes`)}
            onClick={close}
          />
          <NavLink
            component={RouterNavLink}
            to={`/${i18n.locale}/users`}
            label={<Trans>Users</Trans>}
            leftSection={<IconUsers size={18} />}
            active={location.pathname.startsWith(`/${i18n.locale}/users`)}
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
