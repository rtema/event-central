import { useLingui } from "@lingui/react/macro";
import {
  NumberInput,
  Select,
  SimpleGrid,
  Stack,
  TagsInput,
  TextInput,
} from "@mantine/core";
import type { UseFormReturnType } from "@mantine/form";
import type { EmailTemplate, EmailTemplateRequest } from "../../api/types";
import { CodeEditor } from "../ui/CodeEditor";

export interface TemplateFormValues {
  locale: string;
  labelDe: string;
  labelEn: string;
  subject: string;
  previewText: string;
  html: string;
  purposes: string[];
  priority: number | string;
}

export const emptyTemplateValues = (): TemplateFormValues => ({
  locale: "de",
  labelDe: "",
  labelEn: "",
  subject: "",
  previewText: "",
  html: "",
  purposes: [],
  priority: 0,
});

export function valuesFromTemplate(tpl: EmailTemplate): TemplateFormValues {
  return {
    locale: tpl.locale,
    labelDe: tpl.label?.de ?? "",
    labelEn: tpl.label?.en ?? "",
    subject: tpl.subject,
    previewText: tpl.previewText,
    html: tpl.html,
    purposes: tpl.purposes ?? [],
    priority: tpl.priority ?? 0,
  };
}

export function templateToPayload(v: TemplateFormValues): EmailTemplateRequest {
  const label: Record<string, string> = {};
  if (v.labelDe.trim()) label.de = v.labelDe.trim();
  if (v.labelEn.trim()) label.en = v.labelEn.trim();
  return {
    locale: v.locale,
    label,
    subject: v.subject,
    previewText: v.previewText,
    html: v.html,
    purposes: v.purposes,
    priority: Number(v.priority) || 0,
  };
}

interface EmailTemplateFormProps {
  form: UseFormReturnType<TemplateFormValues>;
  /** Report the HTML editor's live syntax validity to the parent. */
  onHtmlValidityChange?: (error: string | null) => void;
}

export function EmailTemplateForm({
  form,
  onHtmlValidityChange,
}: EmailTemplateFormProps) {
  const { t } = useLingui();

  return (
    <Stack>
      <SimpleGrid cols={{ base: 1, sm: 2 }}>
        <TextInput
          label={t`Name (German)`}
          placeholder={t`e.g. Order confirmation`}
          {...form.getInputProps("labelDe")}
        />
        <TextInput
          label={t`Name (English)`}
          placeholder={t`e.g. Order confirmation`}
          {...form.getInputProps("labelEn")}
        />
      </SimpleGrid>

      <SimpleGrid cols={{ base: 1, sm: 2 }}>
        <Select
          label={t`Locale`}
          withAsterisk
          allowDeselect={false}
          data={[
            { value: "de", label: t`German` },
            { value: "en", label: t`English` },
          ]}
          {...form.getInputProps("locale")}
        />
        <TagsInput
          label={t`Purposes`}
          placeholder={t`Add purpose`}
          data={["auth-reset-password", "auth-passwordless"]}
          {...form.getInputProps("purposes")}
        />
      </SimpleGrid>

      <NumberInput
        label={t`Priority`}
        description={t`Higher wins among templates sharing a purpose.`}
        allowDecimal={false}
        {...form.getInputProps("priority")}
      />

      <TextInput
        label={t`Subject`}
        withAsterisk
        description={t`Supports '{{' variables '}}'.`}
        placeholder={t`Your order '{{' order.number '}}'`}
        {...form.getInputProps("subject")}
      />

      <TextInput
        label={t`Preview text`}
        withAsterisk
        description={t`The snippet shown in inbox list views. Supports '{{' variables '}}'.`}
        placeholder={t`Please review your order '{{' order.number '}}'`}
        {...form.getInputProps("previewText")}
      />

      <CodeEditor
        language="html"
        label={t`HTML body`}
        description={t`Reference attached files as '{{' images.key '}}' or '{{' font.key '}}'.`}
        value={form.values.html}
        onChange={(v) => form.setFieldValue("html", v)}
        onValidityChange={onHtmlValidityChange}
        error={form.errors.html}
        minRows={12}
        maxRows={28}
      />
    </Stack>
  );
}
