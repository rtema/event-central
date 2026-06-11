import { useEffect } from "react";
import { loadCatalog, SUPPORTED_LOCALES } from "./i18n";

export const useTranslations = () => {
  useEffect(() => {
    const segments = window.location.pathname.split("/").filter(Boolean);

    let lang = "en";
    if (segments.length > 0 && SUPPORTED_LOCALES.includes(segments[0])) {
      lang = segments[0];
    }
    loadCatalog(lang);
  }, []);
};
