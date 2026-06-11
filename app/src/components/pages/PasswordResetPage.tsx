import { Trans, useLingui } from "@lingui/react/macro";
import {
  Anchor,
  Button,
  Card,
  Center,
  PasswordInput,
  Stack,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { useForm } from "@mantine/form";
import { notifications } from "@mantine/notifications";
import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router";
import { confirmPasswordReset, startPasswordReset } from "../../api/auth";
import { toRequestError } from "../../api/client";

export function PasswordResetPage() {
  const { t } = useLingui();
  const { i18n } = useLingui();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const code = params.get("code") ?? "";
  const phase: "start" | "confirm" = code ? "confirm" : "start";
  const [submitting, setSubmitting] = useState(false);

  const form = useForm({
    initialValues: {
      email: params.get("email") ?? "",
      password: "",
      confirm: "",
    },
    validate: {
      email: (v) => (/^\S+@\S+$/.test(v) ? null : t`Enter a valid email`),
      password: (v) =>
        phase === "confirm" && v.length < 8
          ? t`Use at least 8 characters`
          : null,
      confirm: (v, values) =>
        phase === "confirm" && v !== values.password
          ? t`Passwords do not match`
          : null,
    },
  });

  const fail = (err: unknown) =>
    notifications.show({
      color: "red",
      title: t`Could not complete request`,
      message: toRequestError(err).message,
    });

  const onStart = async () => {
    if (form.validateField("email").hasError) return;
    setSubmitting(true);
    try {
      await startPasswordReset({
        email: form.values.email,
        redirectUri: `${window.location.origin}/reset`,
        locale: i18n.locale as "de" | "en",
      });
      notifications.show({
        color: "pine",
        title: t`Check your inbox`,
        message: t`If the address exists, a reset link is on its way.`,
      });
    } catch (err) {
      fail(err);
    } finally {
      setSubmitting(false);
    }
  };

  const onConfirm = async () => {
    if (form.validate().hasErrors) return;
    setSubmitting(true);
    try {
      await confirmPasswordReset({
        email: form.values.email,
        code,
        password: form.values.password,
      });
      notifications.show({
        color: "pine",
        title: t`Password updated`,
        message: t`You can now sign in with your new password.`,
      });
      navigate("/login", { replace: true });
    } catch (err) {
      fail(err);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Center mih="100dvh" p="md">
      <Card withBorder radius="lg" p="xl" w="100%" maw={400} shadow="sm">
        <Stack gap="lg">
          <div>
            <Title order={2}>
              {phase === "start" ? (
                <Trans>Reset password</Trans>
              ) : (
                <Trans>Choose a new password</Trans>
              )}
            </Title>
            <Text size="sm" c="dimmed">
              {phase === "start" ? (
                <Trans>We'll email you a link to reset it.</Trans>
              ) : (
                <Trans>Set a new password for your account.</Trans>
              )}
            </Text>
          </div>

          <TextInput
            label={t`Email`}
            placeholder="name@tema.de"
            disabled={phase === "confirm" && Boolean(params.get("email"))}
            {...form.getInputProps("email")}
          />

          {phase === "confirm" && (
            <>
              <PasswordInput
                label={t`New password`}
                autoComplete="new-password"
                {...form.getInputProps("password")}
              />
              <PasswordInput
                label={t`Confirm password`}
                autoComplete="new-password"
                {...form.getInputProps("confirm")}
              />
            </>
          )}

          <Button
            loading={submitting}
            onClick={() => void (phase === "start" ? onStart() : onConfirm())}
          >
            {phase === "start" ? (
              <Trans>Send reset link</Trans>
            ) : (
              <Trans>Update password</Trans>
            )}
          </Button>

          <Anchor component={Link} to="/login" size="sm" ta="center">
            <Trans>Back to sign in</Trans>
          </Anchor>
        </Stack>
      </Card>
    </Center>
  );
}
