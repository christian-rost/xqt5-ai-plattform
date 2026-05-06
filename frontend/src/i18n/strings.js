// Minimal i18n helper. German is the default and only fully-populated locale.
// Add new locales by adding a key to STRINGS. Components should import { t }
// and call t('admin.rag.contextual.title') instead of hardcoding strings.
//
// Existing hardcoded German in older components is not a regression to chase,
// but every new user-facing string must go through here.

const STRINGS = {
  de: {
    'admin.rag.section.context_assembly': 'Kontextzusammenstellung',
    'admin.rag.neighbor.label': 'Nachbar-Chunks aktiviert',
    'admin.rag.neighbor.hint':
      'Ergänzt ±1 Nachbar-Chunk für die Top-3-Treffer (verbessert Kontext an Chunk-Grenzen)',
    'admin.rag.max_tokens.label': 'Max. Kontext-Token',
    'admin.rag.max_tokens.hint': 'Token-Budget für RAG-Kontext im Prompt (Standard: 6000)',

    'admin.rag.section.contextual_retrieval': 'Kontextuelles Retrieval',
    'admin.rag.contextual.description':
      'Stellt jedem Chunk beim Upload einen LLM-generierten Kontextsatz voran. ' +
      'Verbessert die Abrufqualität erheblich, verursacht aber zusätzliche LLM-Kosten beim Hochladen. ' +
      'Nur für neu hochgeladene Dokumente aktiv — bestehende Dokumente müssen neu gechunkt werden.',
    'admin.rag.contextual.enabled.label': 'Kontextuelles Retrieval aktiviert',
    'admin.rag.contextual.model.label': 'Modell für Kontextgenerierung',
    'admin.rag.contextual.model.hint':
      'Günstigstes verfügbares Modell empfohlen (z.B. Haiku, Mistral-Small)',
  },
  en: {
    // Placeholder for future English translations. Until populated, t() falls
    // back to the German string for any missing key.
  },
}

let currentLocale = 'de'

export function setLocale(locale) {
  if (STRINGS[locale]) currentLocale = locale
}

export function getLocale() {
  return currentLocale
}

export function t(key) {
  const localeStrings = STRINGS[currentLocale] || {}
  if (key in localeStrings) return localeStrings[key]
  const fallback = STRINGS.de[key]
  if (fallback !== undefined) return fallback
  return key
}
