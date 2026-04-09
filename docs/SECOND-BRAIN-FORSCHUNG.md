# Second Brain / LLM Wiki — Forschungsdokument

> Stand: April 2026  
> Quelle: Andrej Karpathys GitHub Gist vom ~3. April 2026  
> Relevanz: Mögliche Erweiterung der xqt5-ai-platform als Alternative oder Ergänzung zu RAG

---

## 1. Was ist das LLM Wiki / Second Brain?

Andrej Karpathy (Mitgründer OpenAI, ehem. KI-Leiter Tesla) veröffentlichte Anfang April 2026 ein
GitHub Gist mit einer neuen Idee: Statt Dokumente via RAG (Retrieval-Augmented Generation) bei
jeder Anfrage neu zu durchsuchen, lässt man ein LLM eine **persistente, wachsende Wiki**
aus verlinkten Markdown-Dateien aufbauen und pflegen.

Sein Leitsatz: **"Obsidian is the IDE. The LLM is the programmer. The wiki is the codebase."**

Das Konzept lehnt sich an Vannevar Bushs *Memex* (1945) an — eine persönliche, kuratorisch
gepflegte Wissensbasis mit assoziativen Verknüpfungen. Das Maintenance-Problem, das Bushs Vision
scheitern ließ (Menschen vergessen, werden faul, verlieren Überblick), lösen LLMs perfekt.

---

## 2. Architektur — Die drei Schichten

```
raw/          ← Unveränderliche Quellen (PDFs, Artikel, Bilder, Transkripte)
wiki/         ← LLM-generierte & gepflegte Markdown-Dateien
CLAUDE.md     ← Schema: Konventionen, Struktur, Workflows für den LLM-Agenten
```

### Schicht 1: Raw Sources
- Originaldokumente, die der Nutzer kuratiert (lädt rein)
- Das LLM liest sie, verändert sie aber **nie**
- Obsidian Web Clipper konvertiert Web-Inhalte zu `.md` inkl. lokaler Bilder

### Schicht 2: Die Wiki
LLM-generierte Dateien, unterteilt in Kategorien:
- **Zusammenfassungen** (pro Quelle)
- **Entitäten** (Personen, Produkte, Firmen, Konzepte)
- **Vergleiche** (A vs. B)
- **Synthesen** (übergreifende Erkenntnisse)
- **index.md** — Katalog aller Seiten mit Einzeiler-Beschreibungen
- **log.md** — Append-only Chronik aller Ingests, Queries, Lint-Passes

### Schicht 3: Das Schema (CLAUDE.md)
Eine Konfigurationsdatei, die dem LLM-Agenten erklärt:
- Wie die Wiki-Verzeichnisstruktur aufgebaut ist
- Welche Konventionen gelten (Dateinamen, Verlinkungen, Tags)
- Welche Workflows es gibt (Ingest, Query, Lint)

---

## 3. Die drei Kern-Operationen

### 3.1 Ingest (neue Quelle aufnehmen)
1. Nutzer legt neue Quelle in `raw/` ab
2. LLM liest die Quelle durch
3. LLM aktualisiert **10–15 Wiki-Seiten** gleichzeitig:
   - Zusammenfassung der Quelle schreiben
   - Relevante Entitäts-/Konzeptseiten aktualisieren
   - Neue Querverweise anlegen
   - Widersprüche zu bisherigen Einträgen markieren
4. Eintrag in `log.md` schreiben

### 3.2 Query (Frage stellen)
1. Nutzer stellt eine Frage
2. LLM durchsucht seine eigene Wiki (nicht die Roh-Dokumente)
3. Antwort mit Quellenangaben aus der Wiki
4. Wertvolle Analysen können als neue Wiki-Seite abgelegt werden

### 3.3 Lint (Gesundheitscheck)
Periodisch ausgeführt:
- Widersprüche zwischen Seiten finden
- Veraltete Behauptungen markieren
- Verwaiste Seiten (keine eingehenden Links) identifizieren
- Fehlende Querverweise ergänzen
- Wissenslücken auflisten

---

## 4. LLM Wiki vs. RAG — Der entscheidende Unterschied

| Merkmal | RAG (klassisch) | LLM Wiki |
|---|---|---|
| **Wissensaufbau** | Kein — jede Query neu | Kumulativ — wächst mit jeder Quelle |
| **Speicher** | Vektordatenbank (Embeddings) | Markdown-Dateien (menschenlesbar) |
| **Infrastruktur** | Vector DB, Embedding-Modell | Ein Ordner `.md`-Dateien |
| **Multi-Dokument-Synthese** | Schwach (Chunking verliert Kontext) | Stark (wird beim Ingest gebaut) |
| **Transparenz** | Blackbox (Cosine-Similarity) | Vollständig nachvollziehbar |
| **Widerspruchsbehandlung** | Keine | Explizit im Lint-Schritt |
| **Abfragegeschwindigkeit** | Sehr schnell (Vektorsuche) | Langsamer (LLM muss lesen) |
| **Eignung** | Große, heterogene Dokument-Mengen | Bounded Domain, Tiefenforschung |

**Fazit:** RAG ist besser für *"finde relevante Passagen in vielen Dokumenten"*.  
LLM Wiki ist besser für *"baue tiefes Verständnis über eine Domäne auf"*.

---

## 5. Wann welcher Ansatz?

| Anwendungsfall | RAG | LLM Wiki |
|---|---|---|
| Support-Bot über 10.000 Tickets | ✓ | – |
| Wettbewerbsanalyse über 6 Monate | – | ✓ |
| Fachliteratur-Recherche (100 Paper) | ~ | ✓ |
| Meeting-Protokolle durchsuchen | ✓ | – |
| Persönliche Wissensbasis aufbauen | – | ✓ |
| Heterogene Unternehmensdaten | ✓ | – |

---

## 6. Praxisbeispiele aus der Community

- Karpathys eigene Forschungs-Wiki zu einem Thema: ~100 Artikel, 400.000 Wörter
- Entwickler: innerhalb 1 Stunde 56 vernetzte Wiki-Seiten aus Substack-Artikeln generiert
- Implementierungen mit Claude Code + Obsidian, Claude Code + Logseq, lokale LLMs + Obsidian

---

## 7. Integration in die xqt5-ai-platform

### 7.1 Ist-Zustand der Plattform

Die Plattform hat bereits ein ausgereiftes RAG-System (`rag.py`):
- Markdown-aware, token-basiertes Chunking mit Heading-Breadcrumbs
- Tabellen-aware Chunking (Tabellen werden nie zerrissen)
- Kontextuelle Retrieval-Anreicherung
- Nachbar-Chunk-Retrieval für Kontext-Fenster
- XML-strukturierter Kontext-Assembly
- Volltext-Quellenangaben in Antworten
- Dokument-Zusammenfassung beim Upload
- Pools als gemeinsame Wissensräume mit Rollen (owner/admin/editor/viewer)

Das RAG-System ist für die breite Nutzung (viele Nutzer, viele Dokumente) optimiert.

### 7.2 Integrations-Vision: "Wiki-Modus" für Pools

Der natürlichste Integrationspunkt ist das **Pool-Konzept** der Plattform. Ein Pool könnte
optional als "Wiki-Pool" betrieben werden, bei dem das LLM die hochgeladenen Dokumente nicht
nur chunked, sondern zu einer wachsenden Wiki synthetisiert.

#### Neues Konzept: Wiki-Pool

```
Pool (bestehend)
├── Dokumente (Raw Sources) ← unveränderlich, wie bisher
├── Chunks + Embeddings     ← bestehender RAG-Pfad
└── Wiki/ (NEU)
    ├── index.md
    ├── log.md
    ├── entities/
    ├── summaries/
    ├── comparisons/
    └── syntheses/
```

Der Nutzer kann pro Pool wählen: **RAG-Modus** (Standard) oder **Wiki-Modus** (neu).

---

### 7.3 Backend-Änderungen

#### Neues Modul: `wiki.py`

```python
# backend/app/wiki.py

async def ingest_document_to_wiki(pool_id: str, doc_id: str, llm_provider: str):
    """
    Liest ein Dokument und lässt das LLM die Pool-Wiki aktualisieren.
    Läuft asynchron im Hintergrund nach dem Upload.
    """
    # 1. Dokument-Text laden (bereits in DB nach OCR)
    # 2. Wiki-Kontext laden (index.md + relevante bestehende Seiten)
    # 3. LLM-Aufruf: "Ingest dieses Dokument in die Wiki, aktualisiere Seiten"
    # 4. Neue/aktualisierte Seiten in wiki_pages Tabelle speichern
    # 5. log.md updaten

async def query_wiki(pool_id: str, question: str, llm_provider: str) -> str:
    """
    Fragt die Wiki eines Pools. LLM sucht in Wiki-Seiten, nicht in Chunks.
    """
    # 1. index.md laden → LLM entscheidet welche Seiten relevant
    # 2. Relevante Seiten laden
    # 3. LLM generiert Antwort mit Wiki-Seitenangaben als Quellen

async def lint_wiki(pool_id: str, llm_provider: str):
    """
    Gesundheitscheck: Widersprüche, veraltete Infos, fehlende Links.
    Kann als periodischer Job (Celery/FastAPI BackgroundTask) laufen.
    """
```

#### Neue Supabase-Tabellen

```sql
-- Wiki-Seiten je Pool
CREATE TABLE wiki_pages (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pool_id     UUID REFERENCES pool_pools(id) ON DELETE CASCADE,
    slug        TEXT NOT NULL,           -- z.B. "entities/openai"
    title       TEXT NOT NULL,
    content     TEXT NOT NULL,           -- Markdown
    category    TEXT NOT NULL,           -- summary | entity | comparison | synthesis
    source_doc_ids UUID[],               -- welche Raw-Docs haben diese Seite beeinflusst
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (pool_id, slug)
);

-- Wiki-Log
CREATE TABLE wiki_log (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pool_id     UUID REFERENCES pool_pools(id) ON DELETE CASCADE,
    event_type  TEXT NOT NULL,           -- ingest | query | lint
    summary     TEXT NOT NULL,
    affected_pages TEXT[],               -- welche Seiten wurden geändert
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Pool erhält wiki_enabled Flag
ALTER TABLE pool_pools ADD COLUMN wiki_enabled BOOLEAN DEFAULT FALSE;
```

#### Neue API-Endpunkte

```
POST   /pools/{pool_id}/wiki/ingest/{doc_id}   ← nach Upload triggern
GET    /pools/{pool_id}/wiki/pages             ← alle Wiki-Seiten
GET    /pools/{pool_id}/wiki/pages/{slug}      ← einzelne Seite
POST   /pools/{pool_id}/wiki/query             ← Frage an die Wiki
POST   /pools/{pool_id}/wiki/lint              ← Gesundheitscheck starten
GET    /pools/{pool_id}/wiki/log               ← Aktivitätslog
```

---

### 7.4 Frontend-Änderungen

#### Wiki-Ansicht im Pool

Ein neuer Tab "Wiki" neben "Chat" und "Dokumente" in der Pool-Detailansicht.

```
Pool: "Marktanalyse Q2 2026"
├── [Chat]  [Dokumente]  [Wiki]  ← neuer Tab
│
└── Wiki-Tab
    ├── Seitenleiste: Kategorien (Entities / Summaries / Vergleiche / Synthesen)
    ├── index.md Übersicht mit Karte pro Seite
    ├── Seiteneditor (read-only, LLM schreibt)
    ├── Log-Stream: letzte Ingest/Lint-Aktivitäten
    └── "Frage an Wiki stellen" (separater Modus von Pool-Chat)
```

#### Graph-Visualisierung (optional, Phase 2)

Da Wiki-Seiten sich gegenseitig verlinken (`[[entity/openai]]`), lässt sich ein
Obsidian-ähnlicher **Graph-View** mit einer Bibliothek wie `d3-force` oder `vis-network`
bauen, der zeigt, welche Konzepte miteinander verbunden sind.

---

### 7.5 Workflow: Dokument-Upload mit Wiki-Ingest

```
Nutzer lädt PDF hoch
        ↓
OCR (Mistral) → Text extrahiert           [bestehend]
        ↓
Chunking + Embedding → RAG-Index          [bestehend, bleibt]
        ↓
BackgroundTask: wiki.ingest_document()    [NEU]
        ↓
LLM liest Dokument + aktuelle Wiki
        ↓
10-15 Wiki-Seiten werden erstellt/upgedated
        ↓
Nutzer sieht in Wiki-Tab: neue Seiten mit "Quelle: <Dokument>"
```

Die beiden Pfade (RAG + Wiki) laufen **parallel**. Der Chat-Modus kann wählen:
- **RAG-Modus**: schnell, chunk-basiert, gut für spezifische Suchen
- **Wiki-Modus**: langsamer, synthesebasiert, gut für Analyse-Fragen

---

### 7.6 Prompt-Strategie für den Ingest

Der zentrale Ingest-Prompt würde den LLM wie folgt briefen (als System-Prompt):

```
Du bist der Wiki-Kurator für Pool "<name>".

WIKI-SCHEMA:
- categories: entity | summary | comparison | synthesis
- Dateinamen: lowercase-kebab-case, z.B. "entities/openai.md"
- Jede Seite hat: # Titel, ## Abschnitte, [[wiki-interne Links]], Quellangabe am Ende

AKTUELLE WIKI (index.md):
<index_content>

AUFGABE: Ingest des folgenden Dokuments.
1. Schreibe eine Zusammenfassung (summary/<doc-slug>.md)
2. Erstelle/aktualisiere relevante Entity-Seiten
3. Erkenne Widersprüche zu bestehenden Seiten und markiere sie mit ⚠️
4. Schlage neue Vergleichs- oder Synthese-Seiten vor wenn sinnvoll
5. Gib zurück: Liste der geänderten/erstellten Seiten mit ihrem Inhalt

DOKUMENT:
<document_text>
```

---

### 7.7 Aufwandsschätzung

| Komponente | Aufwand |
|---|---|
| `wiki.py` Basismodul (ingest + query) | ~2-3 Tage |
| Supabase-Tabellen + Migration | ~0.5 Tage |
| API-Endpunkte in `main.py` | ~1 Tag |
| Frontend Wiki-Tab (Liste + Seitenansicht) | ~2 Tage |
| Log-Stream im Frontend | ~0.5 Tage |
| Lint-Job (BackgroundTask) | ~1 Tag |
| Graph-View (Phase 2) | ~3-4 Tage |

**Gesamt Phase 1 (ohne Graph):** ca. 7-8 Tage Entwicklung

---

### 7.8 Offene Fragen / Risiken

1. **LLM-Kosten**: Jeder Ingest triggert einen langen LLM-Aufruf. Bei vielen Uploads in einem
   Pool kann das teuer werden. Lösung: Wiki-Ingest nur auf expliziten Nutzer-Klick, nicht
   automatisch.

2. **Konsistenz**: Wenn zwei Dokumente gleichzeitig hochgeladen werden, könnten parallele
   Ingest-Jobs dieselben Wiki-Seiten gleichzeitig schreiben. Lösung: Queue pro Pool,
   Ingest-Jobs seriell verarbeiten.

3. **Wiki-Größe**: Ab ~500 Seiten wird der index.md zu lang für einen Kontext-Fenster.
   Lösung: Hierarchischer Index (Kategorie-Indizes + Haupt-Index).

4. **Modellwahl**: Ingest braucht ein starkes Modell (Claude Sonnet / GPT-4o), da es
   gleichzeitig liest, synthetisiert und schreibt. Billigeres Modell = schlechte Wiki-Qualität.

---

## 8. Quellen

- [llm-wiki — Original GitHub Gist von Andrej Karpathy](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
- [VentureBeat: Karpathy's architecture bypasses RAG](https://venturebeat.com/data/karpathy-shares-llm-knowledge-base-architecture-that-bypasses-rag-with-an)
- [MindStudio: What is Andrej Karpathy's LLM Wiki?](https://www.mindstudio.ai/blog/andrej-karpathy-llm-wiki-knowledge-base-claude-code)
- [Medium (Neural Notions): Karpathy stopped using AI to write code](https://medium.com/neuralnotions/andrej-karpathy-stopped-using-ai-to-write-code-hes-using-it-to-build-a-second-brain-instead-cddceadc5df5)
- [Medium (evoailabs): Why Karpathy's LLM Wiki is the Future of Personal Knowledge](https://evoailabs.medium.com/why-andrej-karpathys-llm-wiki-is-the-future-of-personal-knowledge-7ac398383772)
- [GitHub: second-brain — Community-Implementierung](https://github.com/NicholasSpisak/second-brain)
- [DAIR.AI Academy: LLM Knowledge Bases](https://academy.dair.ai/blog/llm-knowledge-bases-karpathy)
- [Substack (mattpaige68): How to Build an AI Second Brain](https://mattpaige68.substack.com/p/andrej-karpathy-just-showed-us-how)
- [techbuddies.io: Markdown-First Alternative to RAG](https://www.techbuddies.io/2026/04/04/inside-karpathys-llm-knowledge-base-a-markdown-first-alternative-to-rag-for-autonomous-archives/)
- [Substack (mehmetgoekce): I Built Karpathy's LLM Wiki with Claude Code and Logseq](https://mehmetgoekce.substack.com/p/i-built-karpathys-llm-wiki-with-claude)
