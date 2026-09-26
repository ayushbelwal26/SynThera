# Frontend walkthrough — UI refinement pass

This document covers the SynThera frontend visual refinement: same product, quieter presentation. **No routes, APIs, model behavior, or features were added or removed.**

---

## Goal

Make the UI feel like a deliberate computational-biology research tool — dense, calm, information-first — instead of a generic “AI dashboard” template.

| Kept | Changed |
|------|---------|
| Routes (`/discover`, `/analysis`, `/evidence`, `/knowledge-graph`) | Typography hierarchy |
| API calls | Spacing / density |
| Graph logic & data | Cards → hairline rules |
| Color palette & IBM Plex fonts | Pills / badges / uppercase chrome |
| All existing interactions | Microcopy tone (where it sounded generated) |

---

## Design system (`src/index.css`)

Shared primitives drive consistency across pages:

| Class | Role |
|-------|------|
| `.page-kicker` | Small context label above a title |
| `.page-title` | Serif page heading |
| `.page-lede` | Short supporting description |
| `.section-title` | Serif section heading |
| `.bench-label` | Sans field/section label (sentence case, no tracking) |
| `.bench-input` / `.bench-btn` | Underline inputs + square ink buttons |
| `.meta-text` | Secondary copy |
| `.id-text` | Mono for IDs, PMIDs, technical identifiers |
| `.metric-value` | Mono for numerical outputs |

**Rules of thumb**

- Mono only for IDs, metrics, system identifiers — not body UI copy
- No stretched letter-spacing; labels are sentence case, not ALL CAPS
- Prefer borders / dividers over nested rounded cards

---

## Layout

### Sidebar (`layouts/Navigation.tsx`, `AppLayout.tsx`)

- Numbered research nav (01–04 style) kept
- Tighter spacing, clearer active state
- Model info strip retained at the bottom
- Less main-area padding so content feels denser

### Page headers (all pages)

Compact stack instead of “eyebrow + huge title + long paragraph + empty space”:

```
kicker
title
one short lede
```

---

## Page-by-page

### 1. Discover (`pages/DiscoverPage.tsx`)

**Bench + Indication search**

- Result rows use a left color rule + serif pair name + mono IDs
- Rank shown as compact padded numbers (`01`, `02`…), not oversized mono display type
- Metrics (`P(syn)`, `V`, tox) use `.metric-value` / `.bench-label`
- Search method shown as plain text (`beam`), not shouted uppercase

**Why not** — see component section below.

### 2. Analysis / Result inspector (`pages/AnalysisPage.tsx`)

Logical reading order (unchanged functionally, clearer visually):

1. What was analyzed (pair header)
2. What was predicted (class + probabilities)
3. Why (pathway / graph evidence)
4. Can it be verified (faithfulness)
5. External evidence (literature)
6. Toxicity / ranking
7. Assistant (side panel)

Empty state: compact “no active pair” + quick-load reference list (rules, not cards).

### 3. Evidence (`pages/EvidencePage.tsx`)

Literature index feel: title dominant, PMID/journal/year secondary, hairline rows instead of SaaS citation cards.

### 4. Knowledge graph (`pages/KnowledgeGraphPage.tsx`)

- Graph canvas unchanged in structure/logic
- Surrounding chrome quieter: scope note, entity-type filters (categorical chips kept), relation filters as underline toggles
- Entity inspector: label + title + key/value rules (no boxed mono dump)

---

## Components touched in the follow-up pass

These were the last “vibe-coded” surfaces; they now match the shared system.

### `AnalysisChatPanel.tsx`

| Before | After |
|--------|--------|
| Rounded chat bubbles, circular avatars, pill suggestion chips | Flat transcript: role/time labels, left rule for user text |
| Teal “chat widget” header | Compact strip + pair ID |
| Rounded textarea / send | Underline input + `bench-btn` |

Behavior unchanged: resize, tool history, error display, greeting FAB.

### `WhyNotSection.tsx`

| Before | After |
|--------|--------|
| Soft blue/teal cards, status pills, Sparkles icon, teal CTA | Hairline sections, verdict as colored text, `bench-btn` inspect |
| Suggestion chips as filled pills | Underline “Try” links |

Statuses still handled: unsupported / filtered / unknown_drug / scored + PubMed grounding.

### `ToxicityCard.tsx` + `ToxicityBadge.tsx`

| Before | After |
|--------|--------|
| Marketing-scale numbers, many mini-panels, INDEXED pills | Restrained `.metric-value`, gauge bars, text-state DDI labels |
| Boxed source tiles | Expandable source rows (SIDER / PrimeKG / DrugBank) |
| Heavy badge chrome | Icon + sentence-case status text |

Three-state DDI invariant preserved: known / safe / unknown (null never coerced to safe).

### `MetricPill.tsx`

Border-bottom metric cell (label + value), not a rounded shadow pill.

### `NodeDetailModal.tsx`

Flat paper modal; entity/edge fields as rule-separated rows.

### `Badge.tsx`

Dot + colored text; no filled pill backgrounds for ordinary categorical labels.

### `PathwayGraph.tsx` (chrome only)

- Node chrome: less shadow/radius, capitalize type (not UPPERCASE badges)
- Legend / column guides / edge-label toggle quieter
- Mechanistic text as left-rule block, not italic marketing callout
- **Graph layout, edges, and click handlers unchanged**

### `FaithfulnessCard.tsx`

Verdict + sufficiency/necessity as experiment-style metrics (not “Trusted AI” marketing).

---

## Visual language checklist (what we removed)

Across the frontend, these patterns were reduced or removed:

- Excessive rounded cards / nested boxes
- Pill chips for ordinary metadata
- ALL-CAPS chrome labels and stretched tracking
- Monospace on normal sentences
- Oversized “dashboard” numbers
- Decorative teal CTAs and suggestion pills
- Chat-bubble SaaS assistant chrome

**Kept on purpose:** entity-type chips on the graph page (drug / protein / pathway / disease), toxicity/DDI state indicators, graph containers, loading spinners where they signal real work.

---

## What did *not* change

- Backend, checkpoints, scoring, search algorithms
- React Router paths and page structure
- `api.ts` endpoint contracts (live FastAPI backend via `VITE_API_BASE_URL`)
- Prediction, faithfulness, literature, why-not payloads
- Feature set (assistant, why-not, toxicity breakdown, pathway map, KG explorer)

---

## How to review locally

```bash
cd SynThera/drug-combo-discovery/frontend
npm install          # if needed
npm run dev
```

Suggested click-path:

1. **Discover** — run indication search (e.g. glioblastoma / T98G) → scan result density
2. **Inspect** a pair → Analysis: header → probabilities → pathway → faithfulness → literature → toxicity
3. Open **assistant** FAB → ask a sample question
4. On Discover, scroll to **Why not** → try “Why not Temozolomide?”
5. **Evidence** and **Knowledge graph** → confirm chrome matches density without breaking the graph

Typecheck:

```bash
npx tsc -b
```

---

## File map (primary)

```
frontend/src/
  index.css                          # tokens + shared primitives
  layouts/AppLayout.tsx
  layouts/Navigation.tsx
  pages/DiscoverPage.tsx
  pages/AnalysisPage.tsx
  pages/EvidencePage.tsx
  pages/KnowledgeGraphPage.tsx
  components/
    analysis/AnalysisChatPanel.tsx
    analysis/ToxicityCard.tsx
    analysis/PathwayGraph.tsx
    analysis/NodeDetailModal.tsx
    analysis/FaithfulnessCard.tsx
    analysis/LiteratureSection.tsx
    analysis/PredictionHeader.tsx
    analysis/ProbabilityVector.tsx
    discover/WhyNotSection.tsx
    common/Badge.tsx
    common/MetricPill.tsx
    common/ToxicityBadge.tsx
```

---

## Design principle (one line)

Quieter chrome, denser information, real data as the visual language — not a redesign of SynThera’s scientific product.
