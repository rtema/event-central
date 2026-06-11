import { SimpleGrid, Stack, Text } from "@mantine/core";
import type { ReactNode } from "react";

export interface Field {
  label: ReactNode;
  value: ReactNode;
  /** Span the full width of the grid. */
  full?: boolean;
}

/** Render a list of label/value pairs as a tidy, responsive definition grid. */
export function FieldGrid({
  fields,
  cols = { base: 1, sm: 2 },
}: {
  fields: Field[];
  cols?: Record<string, number> | number;
}) {
  const visible = fields.filter((f) => f.value != null && f.value !== "");
  if (visible.length === 0) return null;
  return (
    <SimpleGrid cols={cols} spacing="md" verticalSpacing="md">
      {visible.map((f, i) => (
        <Stack key={i} gap={2} style={f.full ? { gridColumn: "1 / -1" } : undefined}>
          <Text size="xs" tt="uppercase" fw={600} c="dimmed">
            {f.label}
          </Text>
          <Text size="sm">{f.value}</Text>
        </Stack>
      ))}
    </SimpleGrid>
  );
}
