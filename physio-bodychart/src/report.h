#pragma once
#include <gtk/gtk.h>
typedef struct _AppState AppState;

#define REPORT_SECTION_LEN    8192
#define REPORT_NOTE_FIELD_LEN  512
#define REPORT_MAX_NOTES        10   /* keep in sync with MAX_NOTES in stroke.h */
#define SUBJ_FIELD_COUNT         4   /* History, Aggs, Ease, 24hr Pattern */

typedef struct {
    char fields[SUBJ_FIELD_COUNT][REPORT_NOTE_FIELD_LEN];
} NoteSubjFields;

typedef struct {
    char          history[REPORT_SECTION_LEN];
    char          agg_factors[REPORT_NOTE_FIELD_LEN];
    char          ease_factors[REPORT_NOTE_FIELD_LEN];
    char          behaviour_24hr[REPORT_NOTE_FIELD_LEN];
    char          assessment[REPORT_SECTION_LEN];
    char          plan[REPORT_SECTION_LEN];
    char          clinical_notes[REPORT_SECTION_LEN];
    NoteSubjFields note_subj[REPORT_MAX_NOTES];
} ReportData;

GtkWidget *report_view_new(AppState *app);
void       report_activate(AppState *app);
void       report_deactivate(AppState *app);
void       report_save_md(AppState *app);
void       report_copy_all(AppState *app);
