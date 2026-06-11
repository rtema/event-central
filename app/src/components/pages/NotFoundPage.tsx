import { Trans } from "@lingui/react/macro";
import { Button, Center, Stack, Text, Title } from "@mantine/core";
import { Link } from "react-router";

export function NotFoundPage() {
  return (
    <Center mih="60dvh">
      <Stack align="center" gap="xs">
        <Text fw={700} fz={48} c="dimmed">
          404
        </Text>
        <Title order={2}>
          <Trans>Page not found</Trans>
        </Title>
        <Text c="dimmed" size="sm">
          <Trans>The page you are looking for doesn't exist.</Trans>
        </Text>
        <Button component={Link} to={"/"} mt="sm">
          <Trans>Go to home page</Trans>
        </Button>
      </Stack>
    </Center>
  );
}
