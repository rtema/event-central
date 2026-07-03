import { Trans, useLingui } from "@lingui/react/macro";
import {
  Anchor,
  Box,
  Button,
  Card,
  Center,
  Group,
  PasswordInput,
  PinInput,
  SegmentedControl,
  Stack,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { useForm } from "@mantine/form";
import { notifications } from "@mantine/notifications";
import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router";
import {
  loginWithOtp,
  loginWithPassword,
  startPasswordless,
} from "../../api/auth";
import { toRequestError } from "../../api/client";
import { useAuth } from "../auth/useAuth";
import { TemaLogo } from "../ui/TemaLogo";

type Mode = "password" | "code";

export function Login() {
  const { t } = useLingui();
  const { i18n } = useLingui();
  const { status } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [mode, setMode] = useState<Mode>("password");
  const [codeSent, setCodeSent] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const from =
    (location.state as { from?: { pathname: string } } | null)?.from?.pathname ??
    "/de/home";

  useEffect(() => {
    if (status === "authenticated") navigate(from, { replace: true });
  }, [status, from, navigate]);

  const form = useForm({
    initialValues: { email: "", password: "", code: "" },
    validate: {
      email: (v) => (/^\S+@\S+$/.test(v) ? null : t`Enter a valid email`),
      password: (v) =>
        mode === "password" && v.length === 0 ? t`Password is required` : null,
      code: (v) =>
        mode === "code" && codeSent && v.length < 4 ? t`Enter the code` : null,
    },
  });

  const fail = (err: unknown) => {
    const e = toRequestError(err);
    notifications.show({
      color: "red",
      title: t`Sign in failed`,
      message: e.message,
    });
  };

  const submitPassword = async () => {
    if (form.validate().hasErrors) return;
    setSubmitting(true);
    try {
      await loginWithPassword({
        username: form.values.email,
        password: form.values.password,
      });
      // AuthProvider picks up the new session and the effect above redirects.
    } catch (err) {
      fail(err);
    } finally {
      setSubmitting(false);
    }
  };

  const sendCode = async () => {
    if (form.validateField("email").hasError) return;
    setSubmitting(true);
    try {
      await startPasswordless({
        connection: "email",
        email: form.values.email,
        send: "code",
        authParams: { scope: __APP_DEFAULT_SCOPE__, locale: i18n.locale as "de" | "en" },
      });
      setCodeSent(true);
      notifications.show({
        color: "pine",
        title: t`Check your inbox`,
        message: t`We sent a one-time code to ${form.values.email}.`,
      });
    } catch (err) {
      fail(err);
    } finally {
      setSubmitting(false);
    }
  };

  const submitCode = async () => {
    if (form.validateField("code").hasError) return;
    setSubmitting(true);
    try {
      await loginWithOtp({ username: form.values.email, otp: form.values.code });
    } catch (err) {
      fail(err);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Box mih="100dvh" style={{ display: "flex" }}>
      <Box
        visibleFrom="md"
        p="xl"
        style={{
          flex: 1,
          background:
            "linear-gradient(155deg, var(--mantine-color-tema-9), var(--mantine-color-tema-6))",
          color: "white",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
        }}
      >
        <Group gap="sm">
          <TemaLogo height={34} variant="mono" monoColor="#ffffff" />
          <Text fw={700} fz="lg">
            Event Central
          </Text>
        </Group>
        <Stack gap="xs" maw={420}>
          <Title order={1} c="white" fz={34}>
            <Trans>User administration</Trans>
          </Title>
          <Text c="white" opacity={0.85}>
            <Trans>
              Manage accounts, sign-in methods and access scopes for the
              e-invoicing platform.
            </Trans>
          </Text>
        </Stack>
        <Text size="xs" c="white" opacity={0.6}>
          © {new Date().getFullYear()} TEMA Technologie Marketing AG
        </Text>
      </Box>

      <Center p="md" style={{ flex: 1 }}>
        <Card withBorder radius="lg" p="xl" w="100%" maw={400} shadow="sm">
          <Stack gap="lg">
            <Box>
              <Title order={2}>
                <Trans>Sign in</Trans>
              </Title>
              <Text size="sm" c="dimmed">
                <Trans>Use your Event Central credentials.</Trans>
              </Text>
            </Box>

            <SegmentedControl
              fullWidth
              value={mode}
              onChange={(v) => {
                setMode(v as Mode);
                setCodeSent(false);
              }}
              data={[
                { value: "password", label: t`Password` },
                { value: "code", label: t`Email code` },
              ]}
            />

            <TextInput
              label={t`Email`}
              placeholder="name@tema.de"
              autoComplete="email"
              {...form.getInputProps("email")}
            />

            {mode === "password" && (
              <>
                <PasswordInput
                  label={t`Password`}
                  autoComplete="current-password"
                  {...form.getInputProps("password")}
                  onKeyDown={(e) => e.key === "Enter" && void submitPassword()}
                />
                <Button loading={submitting} onClick={() => void submitPassword()}>
                  <Trans>Sign in</Trans>
                </Button>
                <Anchor component={Link} to={`/${i18n.locale}/reset`} size="sm" ta="center">
                  <Trans>Forgot your password?</Trans>
                </Anchor>
              </>
            )}

            {mode === "code" && (
              <>
                {!codeSent ? (
                  <Button loading={submitting} onClick={() => void sendCode()}>
                    <Trans>Send code</Trans>
                  </Button>
                ) : (
                  <Stack gap="sm">
                    <Text size="sm">
                      <Trans>Enter the code we emailed you.</Trans>
                    </Text>
                    <Center>
                      <PinInput
                        length={6}
                        oneTimeCode
                        type="number"
                        value={form.values.code}
                        onChange={(v) => form.setFieldValue("code", v)}
                      />
                    </Center>
                    <Button loading={submitting} onClick={() => void submitCode()}>
                      <Trans>Verify and sign in</Trans>
                    </Button>
                    <Anchor size="sm" ta="center" onClick={() => void sendCode()}>
                      <Trans>Resend code</Trans>
                    </Anchor>
                  </Stack>
                )}
              </>
            )}
          </Stack>
        </Card>
      </Center>
    </Box>
  );
}
