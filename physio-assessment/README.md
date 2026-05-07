# PhysioChart Assessment System — Architecture Specification
<!-- This file is the entry point for Claude Code when building the assessment UI -->

---

## Overview

This is a specialist physiotherapy assessment and report generation system.
It is NOT a simple form. It has three simultaneous layers:

1. **Data capture** — fields filled during or after assessment
2. **Clinical reasoning scaffold** — embedded criteria, checklists, decision logic
3. **Report generation** — pre-written narrative sentences auto-populated with entered values

The markdown files in this directory ARE the data schema. Every `::` field,
`[ ]` checkbox, table row, `<!-- report-template: -->` comment, and
`<!-- ui-hint: -->` comment is a specification instruction for the UI layer.

---

## File Structure

```
physio-assessment/
├── README.md                          ← this file
├── core/
│   ├── 01_consent_setup.md            ← consent, ICE+ patient perspective
│   ├── 02_subjective.md               ← history, work, sleep, function, psychosocial
│   ├── 03_medical_screening.md        ← red flags, comorbidities, medications
│   ├── 04_pain_classification.md      ← Smart et al criteria (full text), CS, pain type
│   ├── 05_outcome_measures.md         ← PSFS, BPI, DASS21, PCS, PSEQ, PCL5, ISI, PBAS
│   ├── 06_diagnosis_goals.md          ← ICD-11 pathways, SMART goals
│   └── 07_barriers_treatment.md       ← barriers checklist → auto-table, treatment plan
└── regions/
    ├── lumbar_physical_examination.md ← lumbar-specific physical exam (current)
    ├── cervical_physical_examination.md ← future
    ├── shoulder_physical_examination.md ← future
    └── knee_physical_examination.md    ← future
```

A session loads: all `core/` modules + one or more `region/` modules.

---

## Markup Conventions

These are parsed by the UI builder:

| Convention | Meaning |
|---|---|
| `- Field::` | Structured input field (text input in UI) |
| `[ ]` | Checkbox (toggle in UI) |
| `<!-- ui-hint: -->` | UI behaviour instruction |
| `<!-- report-template: -->` | Report narrative template with [placeholders] |
| `<!-- reference: -->` | Clinical reference — show as citation in UI |
| `<!-- prompt: -->` | Scripted communication prompt — show as collapsible reminder |
| `<!-- trigger: -->` | Logic condition — UI behaviour when condition met |
| Table rows | Structured data entry — render as interactive table |

---

## Key UI Behaviours Required

### Alerts
- Any red flag checkbox ticked → mandatory acknowledgement popup
- Cauda equina / cord compression → URGENT alert, document action
- CSI ≥ 40 → alert "Suggestive of central sensitisation"
- PCL-5 ≥ 33 → alert "PTSD likely — document action"
- ISI ≥ 10 → alert "Clinically significant insomnia"
- PCS total ≥ 30 → alert "High catastrophising — consider psychology referral"

### Auto-calculations
- BMI from height + weight
- Inflammatory pain score tally (0–4)
- Pain type feature tallies (subjective + examination separate)

### Auto-suggestions
- ICD-11 pathway: suggest based on duration, mechanism, pain type already entered
- Barriers checklist: suggest likely barriers based on outcome measure scores and pain type

### Report generation
- Each `<!-- report-template: -->` comment defines a paragraph in the output report
- [Preferred name] → replaced with entered name throughout
- [placeholders] → replaced with selected/entered values
- Report preview updates in real time

### Body chart integration
- Body chart (existing GTK4 canvas) links to:
  - Symptom location field in subjective
  - Dermatome field in neurological
  - Allodynia/hyperalgesia distribution in sensory testing

### Session structure
- Assessment is a single session object with:
  - patient_id
  - date
  - region (lumbar / cervical / etc.)
  - all field values
  - selected barriers (ordered list)
  - generated report text

---

## Data Model (for SQLite / JSON)

```json
{
  "session": {
    "id": "uuid",
    "date": "ISO8601",
    "patient_id": "string",
    "preferred_name": "string",
    "region": ["lumbar"],
    "modules_loaded": ["core/01", "core/02", "core/03", "core/04", "core/05", "core/06", "core/07", "regions/lumbar"],
    "fields": {},
    "checkboxes": {},
    "tables": {},
    "barriers_selected": [],
    "barriers_priority_order": [],
    "pain_type": {
      "dominant": "",
      "contributing": [],
      "icd11_pathway": "",
      "icd11_subtype": "",
      "icd11_severity": ""
    },
    "report_generated": "",
    "report_confirmed": false
  }
}
```

---

## Build Priority Order (for Claude Code)

1. Parse markdown schema → data model (field extraction)
2. Build session storage (SQLite)
3. Build core UI shell with section navigation
4. Implement field rendering (text inputs, checkboxes, tables)
5. Implement alert system (red flags, score thresholds)
6. Implement auto-calculations (BMI, score tallies)
7. Implement barriers tick → auto-table
8. Implement report template population
9. Implement report preview panel
10. Integrate with body chart (GTK4 canvas link)
11. Implement ICD-11 auto-suggestion logic
12. Implement outcome measure score → barrier suggestion logic
