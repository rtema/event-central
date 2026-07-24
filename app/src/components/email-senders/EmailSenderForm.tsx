import { Trans, useLingui } from "@lingui/react/macro";
import {
  Group,
  NumberInput,
  PasswordInput,
  Radio,
  Select,
  SimpleGrid,
  Stack,
  TagsInput,
  Text,
  TextInput,
} from "@mantine/core";
import type { UseFormReturnType } from "@mantine/form";
import type { EmailSenderRequest, SmtpSecurity } from "../../api/types";

/** How the password field behaves when editing an existing sender. */
export type PasswordMode = "keep" | "set" | "clear";

export interface SenderFormValues {
  labelDe: string;
  labelEn: string;
  fromEmail: string;
  fromName: string;
  replyTo: string;
  host: string;
  port: number | string;
  security: SmtpSecurity;
  username: string;
  password: string;
  passwordMode: PasswordMode;
  purposes: string[];
  priority: number | string;
}

export const emptySenderValues = (): SenderFormValues => ({
  labelDe: "",
  labelEn: "",
  fromEmail: "",
  fromName: "",
  replyTo: "",
  host: "",
  port: 587,
  security: "starttls",
  username: "",
  password: "",
  passwordMode: "keep",
  purposes: [],
  priority: 0,
});

/** Build the API payload from form values, honouring the password mode. */
export function senderToPayload(
  v: SenderFormValues,
  mode: "create" | "edit",
): EmailSenderRequest {
  const label: Record<string, string> = {};
  if (v.labelDe.trim()) label.de = v.labelDe.trim();
  if (v.labelEn.trim()) label.en = v.labelEn.trim();

  const payload: EmailSenderRequest = {
    label,
    fromEmail: v.fromEmail.trim(),
    fromName: v.fromName.trim() || null,
    replyTo: v.replyTo.trim() || null,
    host: v.host.trim(),
    port: Number(v.port) || 587,
    security: v.security,
    username: v.username.trim() || null,
    purposes: v.purposes,
    priority: Number(v.priority) || 0,
  };

  if (mode === "create") {
    payload.password = v.password ? v.password : '******';
  } else if (v.passwordMode === "set") {
    payload.password = v.password;
  } else if (v.passwordMode === "clear") {
    payload.password = null;
  } else if (v.passwordMode === "keep") {
    // use the masked value to signify no change happened
    payload.password = '******';
  }


  return payload;
}

interface EmailSenderFormProps {
  form: UseFormReturnType<SenderFormValues>;
  mode: "create" | "edit";
  /** Whether the sender being edited currently has a password stored. */
  hasPassword?: boolean;
}

export function EmailSenderForm({ form, mode, hasPassword }: EmailSenderFormProps) {
  const { t } = useLingui();

  return (
    <Stack>
      <SimpleGrid cols={{ base: 1, sm: 2 }}>
        <TextInput
          label={t`Name (German)`}
          placeholder={t`e.g. Tickets`}
          {...form.getInputProps("labelDe")}
        />
        <TextInput
          label={t`Name (English)`}
          placeholder={t`e.g. Tickets`}
          {...form.getInputProps("labelEn")}
        />
      </SimpleGrid>

      <SimpleGrid cols={{ base: 1, sm: 2 }}>
        <TextInput
          label={t`From address`}
          withAsterisk
          placeholder="tickets@example.com"
          {...form.getInputProps("fromEmail")}
        />
        <TextInput
          label={t`From name`}
          placeholder={t`Shown as the sender`}
          {...form.getInputProps("fromName")}
        />
      </SimpleGrid>

      <TextInput
        label={t`Reply-to address`}
        placeholder="support@example.com"
        {...form.getInputProps("replyTo")}
      />

      <SimpleGrid cols={{ base: 1, sm: 3 }}>
        <TextInput
          label={t`SMTP host`}
          withAsterisk
          placeholder="smtp.example.com"
          {...form.getInputProps("host")}
          style={{ gridColumn: "span 2" }}
        />
        <NumberInput
          label={t`Port`}
          min={1}
          max={65535}
          allowDecimal={false}
          {...form.getInputProps("port")}
        />
      </SimpleGrid>

      <Select
        label={t`Security`}
        allowDeselect={false}
        data={[
          { value: "starttls", label: t`STARTTLS` },
          { value: "ssl", label: t`SSL / TLS` },
          { value: "plain", label: t`None (plain)` },
        ]}
        {...form.getInputProps("security")}
      />

      <SimpleGrid cols={{ base: 1, sm: 2 }}>
        <TextInput
          label={t`Username`}
          placeholder={t`Optional`}
          autoComplete="off"
          {...form.getInputProps("username")}
        />
        {mode === "create" ? (
          <PasswordInput
            label={t`Password`}
            placeholder={t`Optional`}
            autoComplete="new-password"
            {...form.getInputProps("password")}
          />
        ) : (
          <div />
        )}
      </SimpleGrid>

      {mode === "edit" && (
        <Stack gap="xs">
          <Radio.Group
            label={t`Password`}
            value={form.values.passwordMode}
            onChange={(v) =>
              form.setFieldValue("passwordMode", v as PasswordMode)
            }
          >
            <Group mt={4} gap="lg">
              <Radio
                value="keep"
                label={
                  hasPassword ? (
                    <Trans>Keep current</Trans>
                  ) : (
                    <Trans>Leave unset</Trans>
                  )
                }
              />
              <Radio value="set" label={<Trans>Set new password</Trans>} />
              <Radio
                value="clear"
                label={<Trans>Clear password</Trans>}
                disabled={!hasPassword}
              />
            </Group>
          </Radio.Group>
          {form.values.passwordMode === "set" && (
            <PasswordInput
              placeholder={t`New password`}
              autoComplete="new-password"
              {...form.getInputProps("password")}
            />
          )}
          {form.values.passwordMode === "clear" && (
            <Text size="xs" c="dimmed">
              <Trans>The stored password will be removed on save.</Trans>
            </Text>
          )}
        </Stack>
      )}

      <SimpleGrid cols={{ base: 1, sm: 2 }}>
        <TagsInput
          label={t`Purposes`}
          description={t`Which mail this sender may deliver, e.g. auth or default.`}
          placeholder={t`Add purpose`}
          data={["default", "auth"]}
          {...form.getInputProps("purposes")}
        />
        <NumberInput
          label={t`Priority`}
          description={t`Higher wins among senders sharing a purpose.`}
          allowDecimal={false}
          {...form.getInputProps("priority")}
        />
      </SimpleGrid>
    </Stack>
  );
}
