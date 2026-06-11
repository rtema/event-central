import { Trans } from "@lingui/react/macro";
import {
  Center,
  Stack,
  Text,
  Title
} from "@mantine/core";

export function PageHome() {

  return (
    <Center mih="60dvh">
      <Stack align="center" gap="xs">
        <Text fw={700} fz={48} c="dimmed">
          Tema Technologie Marketing AG
        </Text>
        <Title order={2}>
          <Trans>Event Central</Trans>
        </Title>
        <Text c="dimmed" size="sm">
          <Trans>Please use the sidebar to navigate to your desired topic.</Trans>
        </Text>
      </Stack>
    </Center>
  );
}
