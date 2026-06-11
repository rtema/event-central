import { Button, Group, Text } from "@mantine/core";
import { IconChevronLeft, IconChevronRight } from "@tabler/icons-react";
import { Trans } from "@lingui/react/macro";
import type { Pagination } from "../../api/types";

interface PagerProps {
  /** Current page size. */
  limit: number;
  /** Current numeric offset. */
  offset: number;
  /** Number of rows actually returned for the current page. */
  count: number;
  pagination?: Pagination;
  onChange: (offset: number) => void;
}

/**
 * Minimal offset/limit pager. The API caps page size and returns optional
 * `pagination` metadata; we use the row count to decide whether a next page is
 * likely to exist when `total` isn't provided.
 */
export function Pager({ limit, offset, count, pagination, onChange }: PagerProps) {
  const total = pagination?.total;
  const hasPrev = offset > 0;
  const hasNext =
    total != null ? offset + limit < total : count >= limit;

  if (!hasPrev && !hasNext) return null;

  const from = count === 0 ? 0 : offset + 1;
  const to = offset + count;

  return (
    <Group justify="space-between" mt="md">
      <Text size="sm" c="dimmed">
        {total != null ? (
          <Trans>
            {from}–{to} of {total}
          </Trans>
        ) : (
          <Trans>
            {from}–{to}
          </Trans>
        )}
      </Text>
      <Group gap="xs">
        <Button
          variant="default"
          size="xs"
          leftSection={<IconChevronLeft size={14} />}
          disabled={!hasPrev}
          onClick={() => onChange(Math.max(0, offset - limit))}
        >
          <Trans>Previous</Trans>
        </Button>
        <Button
          variant="default"
          size="xs"
          rightSection={<IconChevronRight size={14} />}
          disabled={!hasNext}
          onClick={() => onChange(offset + limit)}
        >
          <Trans>Next</Trans>
        </Button>
      </Group>
    </Group>
  );
}
