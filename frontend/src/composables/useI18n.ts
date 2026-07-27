/**
 * Lightweight internationalization (i18n) composable.
 * Loads the messages for the `it`/`en` locale, exposes the current locale
 * (`locale`) and the `t(key)` function for nested key resolution,
 * plus `setLocale` which persists the choice in localStorage.
 */
import { ref, computed } from "vue";

interface LocaleMessages {
  [key: string]: string | LocaleMessages;
}

const _itMessages: LocaleMessages = {};
const _enMessages: LocaleMessages = {};

async function loadMessages(locale: string): Promise<LocaleMessages> {
  if (locale === "it") {
    const mod = await import("../locales/it.json");
    return mod.default || mod;
  }
  const mod = await import("../locales/en.json");
  return mod.default || mod;
}

const locale = ref(
  localStorage.getItem("bikemaster_locale") ||
    (navigator.language?.startsWith("it") ? "it" : "en"),
);
const messages = ref<LocaleMessages>({});

function t(key: string): string {
  const parts = key.split(".");
  let current: LocaleMessages | string = messages.value;
  for (const part of parts) {
    if (typeof current === "string" || !current) return key;
    current = current[part] as LocaleMessages;
  }
  return typeof current === "string" ? current : key;
}

async function setLocale(newLocale: string) {
  locale.value = newLocale;
  localStorage.setItem("bikemaster_locale", newLocale);
  messages.value = await loadMessages(newLocale);
}

const currentLocale = computed(() => locale.value);

export function useI18n() {
  return {
    locale: currentLocale,
    t,
    setLocale,
  };
}
