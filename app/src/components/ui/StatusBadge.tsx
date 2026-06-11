import { Badge } from "@mantine/core";
import { Trans } from "@lingui/react/macro";
import type { InvoiceType, OrderStatus, PaymentType } from "../../api/types";

export function OrderStatusBadge({ status }: { status?: OrderStatus }) {
  if (status === "paid")
    return (
      <Badge color="pine" variant="light">
        <Trans>Paid</Trans>
      </Badge>
    );
  if (status === "cancelled")
    return (
      <Badge color="gray" variant="light">
        <Trans>Cancelled</Trans>
      </Badge>
    );
  return (
    <Badge color="yellow" variant="light">
      <Trans>Open</Trans>
    </Badge>
  );
}

export function InvoiceTypeBadge({ type }: { type?: InvoiceType }) {
  if (type === "cancellation")
    return (
      <Badge color="grape" variant="light">
        <Trans>Cancellation</Trans>
      </Badge>
    );
  return (
    <Badge color="pine" variant="light">
      <Trans>Invoice</Trans>
    </Badge>
  );
}

export function PaymentTypeBadge({ type }: { type?: PaymentType }) {
  if (type === "refund")
    return (
      <Badge color="orange" variant="light">
        <Trans>Refund</Trans>
      </Badge>
    );
  return (
    <Badge color="pine" variant="light">
      <Trans>Payment</Trans>
    </Badge>
  );
}
