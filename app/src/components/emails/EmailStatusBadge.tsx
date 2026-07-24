import { Trans } from "@lingui/react/macro";
import { Badge, type MantineColor } from "@mantine/core";
import type { EmailStatus } from "../../api/types";

const COLORS: Record<EmailStatus, MantineColor> = {
  scheduled: "cyan",
  "in-progress": "blue",
  delivered: "pine",
  retry: "yellow",
  failed: "red",
  cancelled: "gray",
};

function label(status: string) {
  switch (status) {
    case "scheduled":
      return <Trans>Scheduled</Trans>;
    case "in-progress":
      return <Trans>Sending</Trans>;
    case "delivered":
      return <Trans>Delivered</Trans>;
    case "retry":
      return <Trans>Retrying</Trans>;
    case "failed":
      return <Trans>Failed</Trans>;
    case "cancelled":
      return <Trans>Cancelled</Trans>;
    default:
      return status;
  }
}

export function EmailStatusBadge({ status }: { status?: string }) {
  const color = (status && COLORS[status as EmailStatus]) || "gray";
  return (
    <Badge color={color} variant="light">
      {status ? label(status) : "—"}
    </Badge>
  );
}
