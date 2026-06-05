import { en, type TranslationKey, type TranslationPack } from "./locales/en";
import { vi } from "./locales/vi";

const translations = {
  en,
  vi,
} satisfies Record<"en" | "vi", TranslationPack>;

export type { TranslationKey };
export default translations;
