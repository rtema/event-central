import { t } from "@lingui/core/macro";
import { useLingui } from "@lingui/react";
import {
  ActionIcon,
  Group,
  Menu,
  Text,
  Tooltip
} from "@mantine/core";
import { IconCheck, IconLanguage } from "@tabler/icons-react";
import { DE, GB } from "country-flag-icons/react/3x2";
import { useState } from "react";
import { useLocation, useNavigate } from "react-router";
import { loadCatalog, SUPPORTED_LOCALES } from "../utils/i18n";
import { sleep } from "../utils/sleep";

const languages = [
  { code: "en", label: "English", Flag: GB },
  { code: "de", label: "Deutsch", Flag: DE },
];

export function LanguageSwitcher() {
  const { i18n } = useLingui();
  const location = useLocation();
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState(false);

  const switchLanguage = async (lang: string) => {
    if (!SUPPORTED_LOCALES.includes(lang)) {
      return;
    }

    // indicate loading
    setIsLoading(true);

    // build new path
    const segments = location.pathname.split("/").filter(Boolean);
    if (segments.length > 0 && SUPPORTED_LOCALES.includes(segments[0])) {
      segments[0] = lang;
    } else {
      segments.unshift(lang);
    }
    const newPath = "/" + segments.join("/") + location.search;

    // load new language catalog
    await loadCatalog(lang);

    // navigate to new path
    await navigate(newPath);

    // sleep to wait for everything to complete
    await sleep(200);

    // indicate success to user
    setIsLoading(false);
  };

  return (
    <Menu position="bottom-end" withinPortal>
      <Menu.Target>
        <Tooltip label={t`Language`}>
          <ActionIcon
            variant="subtle" size="lg" aria-label={t`Change language`}
            loading={isLoading}
          >
            <IconLanguage size={18} />
          </ActionIcon>
        </Tooltip>
      </Menu.Target>

      <Menu.Dropdown>
        {languages.map(({ code, label, Flag }) => {
          const isSelected = code === i18n.locale;
          return (
            <Menu.Item
              key={code}
              onClick={() => switchLanguage(code)}
              rightSection={isSelected ? <IconCheck size={16} /> : null}
              disabled={isLoading}
            >
              <Group wrap="nowrap">
                <Flag width={24} height={18} />
                <Text size="sm">{label}</Text>
              </Group>
            </Menu.Item>
          );
        })}
      </Menu.Dropdown>
    </Menu>
  );
}
