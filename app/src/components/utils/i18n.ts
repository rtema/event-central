import { i18n } from "@lingui/core";

// import dayjs
import dayjs from "dayjs";
import "dayjs/locale/de";
import "dayjs/locale/en";
import advancedFormat from "dayjs/plugin/advancedFormat";
import customParseFormat from "dayjs/plugin/customParseFormat";
import duration from "dayjs/plugin/duration";
import localizedFormat from "dayjs/plugin/localizedFormat";
import relativeTime from "dayjs/plugin/relativeTime";
import timezone from "dayjs/plugin/timezone";
import utc from "dayjs/plugin/utc";

// setup dayjs
dayjs.extend(utc);
dayjs.extend(timezone);
dayjs.extend(relativeTime);
dayjs.extend(customParseFormat);
dayjs.extend(localizedFormat);
dayjs.extend(advancedFormat);
dayjs.extend(duration);

export const SUPPORTED_LOCALES = ["en", "de"];

/**
 * Load messages for requested locale and activate it.
 * This function isn't part of the LinguiJS library because there are
 * many ways how to load messages — from REST API, from file, from cache, etc.
 */
export async function loadCatalog(locale: string) {
  const catalog = await import(`../../locales/${locale}.po`);
  i18n.loadAndActivate({ locale, messages: catalog.messages });
  dayjs.locale(locale);
}

export const localizedTime = dayjs;
