# XQT5 UI Stil- & Layout-Leitfaden

Dieser Leitfaden dokumentiert das Designsystem, das in allen XQT5-Projekten verwendet wird (view-invoices, insAIghts, xqt5-ai-platform, stammdatenmanagement, resourcemgmt). Diese Muster sind genau einzuhalten, um visuelle Konsistenz zu gewährleisten.

---

## Designphilosophie

- **Klarheit vor Dekoration** — jedes visuelle Element hat seinen Platz verdient
- **Konsistente Hierarchie** — Navy für Struktur, Orange für Aktion, Weiß für Inhalt
- **Effizienz** — dicht, aber nicht beengt; Benutzer erfassen Daten auf einen Blick
- **Professionalität** — Corporate Navy + energetisches Orange vermitteln Vertrauen und Kompetenz

---

## 1. Design-Tokens (CSS Custom Properties)

Diese werden in `:root` am Anfang der `index.css` jedes Projekts deklariert. Farben dürfen außerhalb dieses Blocks niemals hartcodiert werden.

```css
:root {
  /* Marke */
  --color-primary:      #ee7f00;
  --color-primary-dark: #d97200;
  --color-dark:         #213452;
  --color-dark-hover:   #3a5279;
  --color-white:        #ffffff;

  /* Grautöne */
  --color-bg:           #f5f5f5;
  --color-gray:         #e0e0e0;
  --color-text:         #333333;
  --color-text-light:   #666666;

  /* Semantisch */
  --color-success:      #28a745;
  --color-error:        #dc3545;
  --color-warning:      #ffc107;

  /* Rahmen & Schatten */
  --color-border:       #e0e0e0;
  --shadow-sm:          0 2px 4px rgba(0, 0, 0, 0.08);
  --shadow-md:          0 4px 12px rgba(0, 0, 0, 0.2);
  --shadow-lg:          0 16px 40px rgba(0, 0, 0, 0.3);

  /* Übergänge */
  --transition:         0.15s ease;
}
```

---

## 2. Typografie

**Schriftarten-Stack** — nur Systemschriften, keine externen Abhängigkeiten:

```css
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
  font-size: 1rem;
  color: var(--color-text);
  text-rendering: optimizeLegibility;
  -webkit-font-smoothing: antialiased;
}
```

**Größen- & Gewichtsskala:**

| Rolle | Größe | Gewicht |
|------|------|--------|
| App-Titel (h1) | `1.5rem` | 700 |
| Abschnittsüberschrift (h2/h3) | `1.1rem` | 600 |
| Card / Panel Header | `1rem` | 600 |
| Fließtext | `0.875rem` | 400 |
| Form Label | `0.875rem` | 500 |
| Table Header | `0.8rem` | 600 |
| Badge / kleines Tag | `0.75rem` | 600 |
| Metadaten / Zeitstempel | `0.75rem` | 400 |

**Table Headers verwenden immer Großbuchstaben + Buchstabenabstand:**

```css
th {
  font-size: 0.8rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--color-text-light);
}
```

---

## 3. Abstände

Basiseinheit ist `1rem`. Die folgende Skala ist zu verwenden — keine Zwischenwerte erfinden:

```
0.25rem  0.35rem  0.5rem  0.65rem  0.75rem
1rem  1.25rem  1.5rem  2rem  2.5rem  3rem
```

**Häufige Anwendung:**

| Position | Wert |
|----------|-------|
| Seiten-Innenabstand | `1.5rem` |
| Card Body Padding | `1.25rem` |
| Card Header Padding | `0.85rem 1.25rem` |
| Form Input Padding | `0.6rem 0.75rem` |
| List Item Padding | `0.75rem 1rem` |
| Tabellenzellen-Innenabstand | `0.65rem 0.85rem` |
| Button (Standard) | `0.5rem 1rem` |
| Button (sm) | `0.3rem 0.65rem` |
| Button (xs) | `0.2rem 0.5rem` |
| Abstand zwischen Panels | `1.5rem` |
| Formulargruppe-Unterabstand | `1rem` |
| Label → Input-Abstand | `0.35rem` |

---

## 4. Layout-Muster

### 4a. App Shell

Alle Apps teilen diese Shell: fixierter Navy-Header oben, scrollbarer Inhalt darunter.

```css
body { margin: 0; background: var(--color-bg); }

.app { display: flex; flex-direction: column; height: 100vh; }

.header {
  background: var(--color-dark);
  color: var(--color-white);
  padding: 0 2rem;
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
}

.header h1 { font-size: 1.5rem; font-weight: 700; margin: 0; }

.header-user {
  display: flex;
  align-items: center;
  gap: 1rem;
  font-size: 0.875rem;
}

.header-username { color: var(--color-primary); font-weight: 600; }
```

### 4b. Split Panel (Liste + Detail)

Verwendet in: view-invoices, stammdatenmanagement, resourcemgmt (Detailansichten).

```css
.main-content {
  display: flex;
  gap: 1.5rem;
  padding: 1.5rem;
  flex: 1;
  overflow: hidden;
}

.panel-left {
  width: 380px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.panel-right {
  flex: 1;
  min-width: 0;
  overflow-y: auto;
}
```

### 4c. Sidebar + Chat

Verwendet in: xqt5-ai-platform.

```css
.app-body { display: flex; flex: 1; overflow: hidden; }

.sidebar {
  width: 260px;
  flex-shrink: 0;
  background: var(--color-dark);
  display: flex;
  flex-direction: column;
  padding: 16px;
  overflow-y: auto;
}

.chat-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
```

### 4d. Header Nav Tabs

Verwendet in: resourcemgmt (mehrteilige Apps).

```css
.nav-tabs {
  display: flex;
  gap: 0.25rem;
  margin-left: 2rem;
}

.nav-tab {
  padding: 0.35rem 0.85rem;
  background: none;
  border: none;
  color: rgba(255, 255, 255, 0.7);
  font-size: 0.875rem;
  font-family: inherit;
  cursor: pointer;
  border-radius: 4px;
  transition: var(--transition);
}

.nav-tab:hover    { color: var(--color-white); background: rgba(255,255,255,0.1); }
.nav-tab.active   { color: var(--color-white); background: rgba(255,255,255,0.15); }
```

---

## 5. Card

Der primäre Inhalts-Container. Header ist immer Navy; Body ist weiß.

```css
.card {
  background: var(--color-white);
  border-radius: 8px;
  box-shadow: var(--shadow-sm);
  overflow: hidden;
}

.card-header {
  background: var(--color-dark);
  color: var(--color-white);
  padding: 0.85rem 1.25rem;
  font-size: 1rem;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.card-body { padding: 1.25rem; }
```

---

## 6. Buttons

```css
.btn {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.5rem 1rem;
  border: 1px solid transparent;
  border-radius: 4px;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: var(--transition);
  white-space: nowrap;
}

.btn:disabled { opacity: 0.6; cursor: not-allowed; }

/* Varianten */
.btn-primary   { background: var(--color-primary); color: var(--color-white); }
.btn-secondary { background: var(--color-gray);    color: var(--color-text); }
.btn-outline   { background: transparent; border-color: var(--color-primary); color: var(--color-primary); }
.btn-danger    { background: var(--color-error);   color: var(--color-white); }

/* Hover */
.btn-primary:hover:not(:disabled)   { background: var(--color-primary-dark); }
.btn-secondary:hover:not(:disabled) { background: #d0d0d0; }
.btn-outline:hover:not(:disabled)   { background: var(--color-primary); color: var(--color-white); }
.btn-danger:hover:not(:disabled)    { background: #c82333; }

/* Helle Variante (für dunkle Hintergründe) */
.btn-outline-light { background: transparent; border-color: rgba(255,255,255,0.6); color: var(--color-white); }
.btn-outline-light:hover:not(:disabled) { background: rgba(255,255,255,0.15); border-color: var(--color-white); }

/* Größen */
.btn-sm { padding: 0.3rem 0.65rem; font-size: 0.8rem; }
.btn-xs { padding: 0.2rem 0.5rem;  font-size: 0.75rem; }
```

---

## 7. Formulare

```css
.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.35rem;
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--color-text);
}

input[type="text"],
input[type="email"],
input[type="password"],
input[type="number"],
textarea,
select {
  width: 100%;
  padding: 0.6rem 0.75rem;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  font-size: 0.875rem;
  font-family: inherit;
  color: var(--color-text);
  background: var(--color-white);
  box-sizing: border-box;
  transition: border-color var(--transition), box-shadow var(--transition);
}

input:focus,
textarea:focus,
select:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 2px rgba(238, 127, 0, 0.2);
}

input:disabled,
textarea:disabled,
select:disabled {
  background: var(--color-bg);
  opacity: 0.7;
  cursor: not-allowed;
}

.form-error { color: var(--color-error); font-size: 0.8rem; margin-top: 0.35rem; }
.form-hint  { color: var(--color-text-light); font-size: 0.8rem; margin-top: 0.35rem; }
```

### Tabs (innerhalb von Formularen oder Panels)

```css
.tabs {
  display: flex;
  border-bottom: 2px solid var(--color-gray);
  margin-bottom: 1.5rem;
}

.tab {
  flex: 1;
  padding: 0.75rem;
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;
  font-size: 0.875rem;
  font-family: inherit;
  color: var(--color-text-light);
  cursor: pointer;
  transition: var(--transition);
}

.tab:hover  { color: var(--color-text); }
.tab.active { color: var(--color-primary); border-bottom-color: var(--color-primary); }
```

---

## 8. Tabellen

```css
.table {
  width: 100%;
  border-collapse: collapse;
}

.table th {
  background: var(--color-bg);
  padding: 0.65rem 0.85rem;
  text-align: left;
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--color-text-light);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  border-bottom: 1px solid var(--color-border);
}

.table td {
  padding: 0.65rem 0.85rem;
  font-size: 0.875rem;
  border-bottom: 1px solid var(--color-border);
}

.table tbody tr:hover { background: rgba(238, 127, 0, 0.04); }

/* Zellen-Ausrichtungshilfen */
.table .num    { text-align: right; }
.table .center { text-align: center; }

/* Abweichungs- / Fehlerzelle */
.table .cell-mismatch {
  background: rgba(220, 53, 69, 0.08);
  border-left: 3px solid var(--color-error);
}
```

---

## 9. List Items (Auswählbar)

Verwendet in Sidebar- / Baumlisten — dem linken Panel jedes Split Layouts.

```css
.list-item {
  padding: 0.75rem 1rem;
  border-bottom: 1px solid var(--color-border);
  cursor: pointer;
  transition: background-color var(--transition);
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.5rem;
}

.list-item:hover    { background: var(--color-bg); }

.list-item.selected {
  background: rgba(238, 127, 0, 0.08);
  border-left: 3px solid var(--color-primary);
}

.list-item-title {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--color-dark);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.list-item-sub {
  font-size: 0.78rem;
  color: var(--color-text-light);
  margin-top: 0.1rem;
}
```

---

## 10. Badges & Statusindikatoren

```css
.badge {
  display: inline-flex;
  align-items: center;
  padding: 0.15rem 0.55rem;
  border-radius: 10px;
  font-size: 0.75rem;
  font-weight: 600;
  white-space: nowrap;
}

/* Semantische Varianten */
.badge-primary  { background: rgba(238, 127, 0, 0.12); color: var(--color-primary); }
.badge-dark     { background: var(--color-dark);        color: var(--color-white); }
.badge-success  { background: rgba(40, 167, 69, 0.12);  color: var(--color-success); }
.badge-error    { background: rgba(220, 53, 69, 0.1);   color: var(--color-error); }
.badge-warning  { background: rgba(255, 193, 7, 0.15);  color: #856404; }
.badge-neutral  { background: var(--color-bg);          color: var(--color-text-light); }
```

---

## 11. Filter Bar (Pill Buttons)

Der Status-/Kategorie-Filterstreifen oberhalb von Listen.

```css
.filter-bar {
  display: flex;
  gap: 0.5rem;
  padding: 0.6rem 1rem;
  border-bottom: 1px solid var(--color-border);
  flex-wrap: wrap;
  align-items: center;
}

.filter-btn {
  padding: 0.25rem 0.75rem;
  border: 1px solid var(--color-gray);
  border-radius: 20px;
  background: none;
  font-size: 0.8rem;
  font-family: inherit;
  color: var(--color-text-light);
  cursor: pointer;
  transition: var(--transition);
}

.filter-btn:hover:not(.active) { border-color: var(--color-dark); color: var(--color-dark); }
.filter-btn.active             { background: var(--color-dark); color: var(--color-white); border-color: var(--color-dark); }
```

---

## 12. Modals

```css
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 500;
  padding: 1rem;
}

.modal {
  background: var(--color-white);
  border-radius: 10px;
  box-shadow: var(--shadow-lg);
  width: 100%;
  max-width: 540px;
  max-height: 90vh;
  overflow-y: auto;
}

.modal-header {
  background: var(--color-dark);
  color: var(--color-white);
  padding: 1rem 1.5rem;
  border-radius: 10px 10px 0 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 1rem;
  font-weight: 600;
}

.modal-body { padding: 1.5rem; }

.modal-footer {
  padding: 1rem 1.5rem;
  border-top: 1px solid var(--color-border);
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
}
```

---

## 13. Loading States

```css
.loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  padding: 3rem;
  color: var(--color-text-light);
  font-size: 0.875rem;
}

.loading-spinner {
  width: 24px;
  height: 24px;
  border: 3px solid var(--color-gray);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  flex-shrink: 0;
}

@keyframes spin { to { transform: rotate(360deg); } }

.loading-spinner-sm {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.4);
  border-top-color: var(--color-white);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  flex-shrink: 0;
}
```

`.loading-spinner-sm` ersetzt den Button-Text bei inline-Loading-States — weißer Spinner auf dem farbigen Button-Hintergrund.

---

## 14. Toast Notifications

Fixiert unten rechts. Verwendet als Rückmeldung bei Speichern-/Löschen-/Export-Aktionen.

```css
.toast-container {
  position: fixed;
  bottom: 1.5rem;
  right: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  z-index: 1000;
}

.toast {
  padding: 0.75rem 1.25rem;
  border-radius: 6px;
  color: var(--color-white);
  font-size: 0.875rem;
  font-weight: 500;
  box-shadow: var(--shadow-md);
  animation: toast-in 0.2s ease;
}

.toast.success { background: var(--color-success); }
.toast.error   { background: var(--color-error); }
.toast.warning { background: #856404; }

@keyframes toast-in {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}
```

---

## 15. Login-Seite

Zentrierte Card, maximal 400px breit, Tabs für Login/Registrierung.

```css
.login-page {
  min-height: 100vh;
  background: var(--color-bg);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem;
}

.login-box {
  background: var(--color-white);
  border-radius: 10px;
  box-shadow: var(--shadow-md);
  padding: 2rem;
  width: 100%;
  max-width: 400px;
}

.login-logo {
  text-align: center;
  margin-bottom: 1.5rem;
}

.login-logo h1 {
  color: var(--color-dark);
  font-size: 1.5rem;
  margin: 0.5rem 0 0;
}

.login-logo span { color: var(--color-primary); }
```

---

## 16. Stat Cards (Dashboard)

```css
.stats-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.stat-card {
  background: var(--color-white);
  border-radius: 8px;
  padding: 1rem 1.25rem;
  box-shadow: var(--shadow-sm);
}

.stat-card-label {
  font-size: 0.75rem;
  color: var(--color-text-light);
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 0.35rem;
}

.stat-card-value {
  font-size: 1.75rem;
  font-weight: 700;
  color: var(--color-dark);
}

.stat-card-value.primary { color: var(--color-primary); }
.stat-card-value.success { color: var(--color-success); }
.stat-card-value.error   { color: var(--color-error); }
```

---

## 17. CSS-Benennungskonventionen

Verwende **kebab-case**, strukturiert als `component` → `component-element` → `component-element modifier-class`.

```
.card                     Block
.card-header              Element
.card-header.sticky       Modifier via extra class
.btn                      Block
.btn-primary              Variant modifier
.btn-sm                   Size modifier
.badge-success            Semantic variant
.list-item.selected       State via extra class
.list-item.active         State via extra class
```

**Nicht** camelCase oder Unterstriche in Klassennamen verwenden.

**State-Klassen** direkt angewendet (nicht verschachtelt):

```css
.selected  .active  .disabled  .loading  .expanded  .mismatch  .error
```

---

## 18. Projektspezifische Erweiterungen

Diese Muster existieren in bestimmten Projekten und sollen wiederverwendet werden, wenn ähnliche Funktionen anderswo hinzugefügt werden.

### Abweichungshervorhebung (view-invoices)

Beim Vergleich zweier Datensätze werden abweichende Felder mit einem roten linken Rahmen und Icon markiert:

```css
.detail-field.mismatch {
  background: rgba(220, 53, 69, 0.06);
  border-left: 3px solid var(--color-error);
  padding-left: 0.65rem;
}

.mismatch-icon { color: var(--color-error); margin-left: 0.3rem; }
```

### Chat-Nachrichten (xqt5-ai-platform)

```css
.message.user      { background: #fff3e0; border-left: 3px solid var(--color-primary); }
.message.assistant { background: var(--color-bg); }
```

### Ähnlichkeitsbalken (stammdatenmanagement)

```css
.similarity-bar {
  height: 6px;
  background: var(--color-gray);
  border-radius: 3px;
}
.similarity-bar-fill {
  height: 100%;
  background: var(--color-primary);
  border-radius: 3px;
}
```

### Dreispaltiges Layout (insAIghts)

```css
.three-col {
  display: grid;
  grid-template-columns: minmax(260px, 28%) minmax(380px, 40%) minmax(360px, 32%);
  flex: 1;
  overflow: hidden;
}
```

---

## 19. Empfehlungen und Verbote

**Empfohlen:**
- CSS-Variablen für jede Farbe und jeden Schatten verwenden
- Die definierte Abstandsskala verwenden
- Navy-Header auf Cards, Panels und Modals
- Orange für primäre Aktionen, Focus-Ringe, ausgewählte Zustände und aktive Indikatoren
- System-Schriftarten-Stack — keine Google Fonts oder Icon-Fonts
- `transition: var(--transition)` auf interaktiven Elementen
- `cursor: not-allowed` + `opacity: 0.6` für deaktivierte Elemente

**Verboten:**
- Neue Farben außerhalb der Palette erfinden
- Inline-Styles verwenden, außer für tatsächlich dynamische Werte (Breiten aus JS)
- Schlagschatten schwerer als `var(--shadow-lg)` hinzufügen
- `border-radius` größer als `10px` (Cards/Modals) oder kleiner als `4px` (Inputs/Buttons) verwenden
- Fließtext in datenintensiven Ansichten zentrieren
- Mehr als drei Schriftgrößen innerhalb einer einzigen Komponente verwenden
- Externe CSS-Frameworks hinzufügen (kein Bootstrap, Tailwind, Material UI)

---

## 20. Mögliche zukünftige Änderungen

Kritische Beobachtungen, die bei der Überprüfung identifiziert wurden. Nichts davon wurde bisher umgesetzt — dies sind Kandidaten für eine zukünftige Überarbeitungsrunde.

### Token-System

- **`--color-gray` und `--color-border` sind identisch (`#e0e0e0`)** — einer ist redundant. Entweder differenzieren (Rahmen etwas dunkler, Grau für Füllungen) oder einen entfernen und nur `--color-border` durchgängig verwenden.
- **Hartcodierte RGBA-Werte tauchen im gesamten Leitfaden auf** — `rgba(238, 127, 0, 0.08)`, `rgba(238, 127, 0, 0.12)`, `rgba(238, 127, 0, 0.2)`, `#fff3e0` kodieren alle die Primärfarbe ohne Token. In Betracht ziehen: `--color-primary-tint-weak`, `--color-primary-tint`, `--color-primary-focus` etc.
- **`#856404` (Warntext/Bernstein) erscheint an zwei Stellen** (badge-warning, toast.warning) als hartcodierter Hex-Wert ohne Token. Sollte `--color-warning-text` oder ähnlich sein.
- **`#c82333` und `#d0d0d0`** werden als Hover-Farben für Danger- bzw. Secondary-Buttons verwendet, haben aber keine Tokens. Die Regel "Farben niemals hartcodieren" wird vom Leitfaden selbst verletzt.
- **Keine border-radius-Tokens** — der Leitfaden listet 4px, 6px, 8px, 10px als erlaubte Radien (im Verboten-Abschnitt), definiert aber keine Variablen dafür. Ein `--radius-sm: 4px`, `--radius-md: 8px`, `--radius-lg: 10px`-System würde die Regel durchsetzbar machen.
- **Die `.btn-success`-Variante** wird durch das Vorhandensein von `--color-success` und die Verwendung in Stat-Card-Farbmodifikatoren impliziert, aber kein `.btn-success`-CSS ist tatsächlich in Abschnitt 6 definiert.

### Widerspruch in der Abstandsskala

- **Die dokumentierte Skala und die tatsächlichen Komponentenspezifikationen stimmen nicht überein.** Die Skala listet `0.25 0.35 0.5 0.65 0.75 1 1.25 1.5 2 2.5 3rem` und besagt "keine Zwischenwerte erfinden" — aber dann verwendet Abschnitt 7 `0.6rem` (Input-Padding), Abschnitt 8 `0.85rem` (Tabellenzellen), Abschnitt 9 `0.78rem` (list-item-sub), alles außerhalb der Skala. Entweder sollte die Skala um diese Werte erweitert werden, oder die Komponentenspezifikationen müssen an die Skala angepasst werden.

### Typografie

- **`line-height` ist nirgends definiert.** Für dichte Datentabellen und lange Textfelder ist dies erheblich relevant. Ein Basiswert von `line-height: 1.5` für Fließtext und `1.2` für Überschriften sollte festgelegt werden.
- **Die Größentabelle in Abschnitt 2 ist unvollständig.** Später im Leitfaden verwendete Größen — `0.78rem` (List-Sub), `0.9rem` (List-Titel), `1.75rem` (Stat-Wert) — erscheinen nicht in der Tabelle. Die Tabelle sollte entweder zur verbindlichen Referenz werden oder entfernt werden.

### Benennungskonvention

- **Die Konventionsbeschreibung verwendet `component-element--modifier`** (mit doppelten Bindestrichen, BEM-Stil), aber jedes Beispiel verwendet einfache Bindestriche (`btn-primary`, `badge-success`). Beschreibung und Beispiele widersprechen sich. Eines auswählen und explizit benennen.
- **State-Klassen (`.selected`, `.active`, `.error`) haben kein Präfix** und können kollidieren. `.error` birgt insbesondere das Risiko eines Konflikts zwischen dem Fehlerzustand eines Form-Felds und dem einer Tabellenzeile. Ein komponentengebundener Ansatz (`.list-item.is-selected`, `.form-field.has-error`) wäre robuster.

### Fehlende Muster

- **Z-Index-Skala** — der Leitfaden verwendet `z-index: 500` (Modals) und `z-index: 1000` (Toasts), stellt aber kein dokumentiertes Ebenensystem bereit. Dropdowns, fixierte Header, Tooltips und Overlays benötigen alle definierte Slots.
- **Leerzustände** — kein Muster dafür, was angezeigt werden soll, wenn eine Liste oder Tabelle keine Daten enthält. Derzeit löst jedes Projekt dies unterschiedlich.
- **Responsives Verhalten des Split Panels** — das linke Panel ist auf `380px` hartcodiert, ohne Hinweise auf das Einklappverhalten bei schmaleren Viewports. Die einzige Erwähnung von Responsivität im Leitfaden ist in Abschnitt 18 (insAIghts dreispaltig), was Split Panels unspezifiziert lässt.
- **Checkbox- und Radio-Inputs** — nicht in Abschnitt 7 behandelt, obwohl sie in Filter-Formularen und Einstellungen über mehrere Projekte hinweg verwendet werden.
- **Modal-Close-Button** — der Modal-Header verwendet `justify-content: space-between`, was einen Close-Button rechts impliziert, aber kein Stil für diesen Button ist definiert.
- **`textarea`-Größenänderung** — keine Angabe, ob resize auf `vertical`, `none` gesetzt oder dem Browser-Standard überlassen werden soll.

### Gemischte Einheiten

- **Abschnitt 4c (Sidebar) verwendet `padding: 16px`** (Pixel), während der gesamte Rest des Leitfadens `rem` verwendet. Zur Konsistenz sollte `1rem` verwendet werden.
