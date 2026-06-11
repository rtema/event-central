import { Alert, Center, Loader, Stack, Text } from "@mantine/core";
import { IconAlertTriangle, IconInbox } from "@tabler/icons-react";
import { Trans } from "@lingui/react/macro";
import type { ReactNode } from "react";
import { toRequestError } from "../../api/client";

interface QueryStateProps {
  isLoading: boolean;
  error: unknown;
  isEmpty?: boolean;
  empty?: ReactNode;
  children: ReactNode;
  minHeight?: number;
}

export function QueryState({
  isLoading,
  error,
  isEmpty,
  empty,
  children,
  minHeight = 160,
}: QueryStateProps) {
  if (isLoading) {
    return (
      <Center mih={minHeight}>
        <Loader />
      </Center>
    );
  }

  if (error) {
    const e = toRequestError(error);
    return (
      <Alert
        color="red"
        icon={<IconAlertTriangle size={18} />}
        title={<Trans>Something went wrong</Trans>}
      >
        <Stack gap={4}>
          <Text size="sm">{e.message}</Text>
          {e.correlationId && (
            <Text size="xs" c="dimmed">
              <Trans>Correlation ID</Trans>: {e.correlationId}
            </Text>
          )}
        </Stack>
      </Alert>
    );
  }

  if (isEmpty) {
    return (
      <Center mih={minHeight}>
        {empty ?? (
          <Stack align="center" gap="xs" c="dimmed">
            <IconInbox size={32} />
            <Text size="sm">
              <Trans>Nothing here yet</Trans>
            </Text>
          </Stack>
        )}
      </Center>
    );
  }

  return <>{children}</>;
}
