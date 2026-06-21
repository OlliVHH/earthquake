// Human: i18next bootstrap — DE/EN bundles, persisted language preference.
// Agent: READS localStorage earthquake_lang; WRITES i18n instance; CALLS i18next.init.
import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import de from "./de.json";
import en from "./en.json";

// Human: Restore last chosen language; default German when unset.
// Agent: READS localStorage earthquake_lang; env default "de".
const saved = localStorage.getItem("earthquake_lang") ?? "de";

void i18n.use(initReactI18next).init({
  resources: {
    de: { translation: de },
    en: { translation: en },
  },
  lng: saved,
  fallbackLng: "en",
  interpolation: { escapeValue: false },
});

export default i18n;
