# CORE — Clinical Impression & ICD-11 Diagnosis
<!-- core module: applies to all assessment types -->
<!-- ui-hint: auto-suggest ICD-11 pathway based on duration, mechanism, and pain type classification already entered -->
<!-- ui-hint: present suggestion with reasoning — clinician confirms or overrides -->

---

## ICD-11 Diagnosis Pathway Selection
<!-- reference: Nicholas et al 2019, Schug et al 2019, Perrot et al 2019, Scholz et al 2019 -->
<!-- ui-hint: show only the one or two most likely pathways based on prior data entry -->
<!-- ui-hint: greyed options shown collapsed with "why not selected" rationale -->

### Criteria met for pathway selection:
- Duration >3 months:: [ ] Yes [ ] No
- Mechanism::
  - [ ] No clear tissue cause → Chronic Primary Pain pathway
  - [ ] Developed after surgical procedure → Chronic Post-Surgical Pain pathway
  - [ ] Developed after traumatic tissue injury → Chronic Post-Traumatic Pain pathway
  - [ ] Due to underlying disease/pathology → Chronic Secondary MSK Pain pathway
  - [ ] Somatosensory nervous system lesion/disease → Chronic Neuropathic Pain pathway
  - [ ] Mixed / unable to determine dominant → Mixed pathway

---

### Chronic Primary Pain
<!-- reference: Nicholas et al 2019 -->
<!-- trigger: duration >3 months + significant distress OR functional limitation + not better accounted for by another diagnosis -->
- Significant emotional distress or functional limitation:: [ ] Yes [ ] No
- Not better accounted for by another diagnosis:: [ ] Confirmed
- Subtype::
  - [ ] Widespread pain / fibromyalgia
  - [ ] Complex regional pain syndrome type I
  - [ ] Chronic primary headache — migraine
  - [ ] Chronic primary headache — tension type
  - [ ] Chronic primary MSK — cervical
  - [ ] Chronic primary MSK — thoracic
  - [ ] Chronic primary MSK — lumbar
  - [ ] Chronic primary MSK — limb
- Severity:: [ ] Mild [ ] Moderate [ ] Marked

<!-- report-template: "On assessment [Preferred name] had a symptom duration of >3 months, associated significant emotional distress/significant activity limitation with the symptoms not better accounted for by another diagnosis (Nicholas et al 2019). The ICD-11 diagnosis is therefore chronic primary pain ([subtype]) of [severity] severity." -->

---

### Chronic Post-Surgical Pain
<!-- reference: Schug et al 2019 -->
- Surgical procedure::
- Subtype::
  - [ ] After amputation
  - [ ] After spinal surgery
  - [ ] After thoracotomy
  - [ ] After breast surgery
  - [ ] After herniotomy
  - [ ] After hysterectomy
  - [ ] After arthroplasty
- Most likely specific source::
- Severity:: [ ] Mild [ ] Moderate [ ] Marked

<!-- report-template: "On assessment [Preferred name] had a symptom duration of >3 months, that developed or increased in intensity after a surgical procedure (Schug et al 2019). The ICD-11 diagnosis is therefore chronic post-surgical pain ([subtype]) of [severity] severity. The specific source of symptoms is most likely [source]." -->

---

### Chronic Post-Traumatic Pain
<!-- reference: Schug et al 2019 -->
- Traumatic event::
- Subtype::
  - [ ] After burns injury
  - [ ] After peripheral nerve injury
  - [ ] After spinal cord injury
  - [ ] After brain injury
  - [ ] After whiplash injury
  - [ ] After musculoskeletal injury
- Most likely specific source::
- Severity:: [ ] Mild [ ] Moderate [ ] Marked

<!-- report-template: "On assessment [Preferred name] had a symptom duration of >3 months, that developed or increased in intensity after a traumatic tissue injury (Schug et al 2019). The ICD-11 diagnosis is therefore chronic post-traumatic pain ([subtype]) of [severity] severity. The specific source of symptoms is most likely [source]." -->

---

### Chronic Secondary MSK Pain
<!-- reference: Perrot et al 2019 -->
- Underlying disease/pathology::
- Subtype::
  - [ ] Osteoarthritis
  - [ ] Spondylosis
  - [ ] Musculoskeletal injury
- Most likely specific source::
- Severity:: [ ] Mild [ ] Moderate [ ] Marked

<!-- report-template: "On assessment [Preferred name] had a symptom duration of >3 months likely to be due to an underlying disease/pathology and resultant nociceptive stimulus (Perrot et al 2019). The ICD-11 diagnosis is therefore chronic secondary musculoskeletal pain associated with structural changes ([subtype]) of [severity] severity. The specific source of symptoms is most likely [source]." -->

---

### Chronic Neuropathic Pain
<!-- reference: Scholz et al 2019 -->
- Causative lesion/disease::
- Subtype::
  - [ ] Peripheral nerve injury
  - [ ] Painful radiculopathy
- Severity:: [ ] Mild [ ] Moderate [ ] Marked

<!-- report-template: "On assessment [Preferred name] had a symptom duration of >3 months likely to be caused by a lesion or disease of the somatosensory nervous system (Scholz et al 2019). The ICD-11 diagnosis is therefore chronic neuropathic pain associated with [subtype] of [severity] severity." -->

---

### Mixed / Indeterminate
- Dominant type if determinable:: [ ] Nociceptive [ ] Neuropathic [ ] Nociplastic [ ] Indeterminate
- Reasoning::

<!-- report-template (determinable): "[Preferred name] appeared to have a mix of pain types, with features of [types]. However, assessment suggests a dominant pain type of [dominant] based on the clinical features described above." -->
<!-- report-template (indeterminate): "Due to the complexity of [Preferred name]'s condition it was not possible to determine a dominant pain type on initial assessment. In the preparation phase of the program this will be determined based on further assessment and response to specific treatment strategies." -->

---

## SMART Goals
<!-- ui-hint: goals entered here feed into the treatment plan and follow-up sections -->

Following completion of the assessment, the following potentially meaningful goals were confirmed:

1.
2.
3.
4.
