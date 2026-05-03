#include "stroke.h"
#include <stdlib.h>
#include <string.h>

/* Symptom visual definitions — colour + pattern */
const SymptomDef SYMPTOM_DEFS[SYMPTOM_COUNT] = {
    [SYMPTOM_PAIN_CONSTANT]     = { "Pain (constant)",     0.89f, 0.29f, 0.29f, FILL_SOLID       },
    [SYMPTOM_PAIN_INTERMITTENT] = { "Pain (intermittent)", 0.91f, 0.45f, 0.60f, FILL_DASHED      },
    [SYMPTOM_PARAESTHESIA]      = { "Pins & needles",      0.12f, 0.68f, 0.28f, FILL_DOTS_SPACED },
    [SYMPTOM_ANAESTHESIA]       = { "Anaesthesia",         0.22f, 0.54f, 0.87f, FILL_H_STROKES   },
    [SYMPTOM_DEEP_ACHE]         = { "Paraesthesia",        0.94f, 0.62f, 0.15f, FILL_XMARKS      },
    [SYMPTOM_TICK]              = { "Tick (clear)",        0.15f, 0.70f, 0.25f, FILL_TICK        },
};

/* ── Stroke ─────────────────────────────────────────────────────────────── */
Stroke *stroke_new(SymptomType type, int view)
{
    Stroke *s   = calloc(1, sizeof *s);
    s->cap       = 64;
    s->pts       = malloc(s->cap * sizeof(StrokePoint));
    s->type      = type;
    s->view      = view;
    s->wide_mode = 0;
    return s;
}

void stroke_add_point(Stroke *s, float x, float y, float pressure)
{
    if (s->n_pts >= s->cap) {
        s->cap *= 2;
        s->pts  = realloc(s->pts, s->cap * sizeof(StrokePoint));
    }
    s->pts[s->n_pts++] = (StrokePoint){ x, y, pressure };
}

void stroke_free(Stroke *s)
{
    if (!s) return;
    free(s->pts);
    free(s);
}

/* ── StrokeList (undo stack) ────────────────────────────────────────────── */
StrokeList *stroke_list_new(void)
{
    StrokeList *sl = calloc(1, sizeof *sl);
    sl->cap        = 32;
    sl->strokes    = malloc(sl->cap * sizeof(Stroke *));
    return sl;
}

void stroke_list_push(StrokeList *sl, Stroke *s)
{
    if (sl->n >= sl->cap) {
        sl->cap   *= 2;
        sl->strokes = realloc(sl->strokes, sl->cap * sizeof(Stroke *));
    }
    sl->strokes[sl->n++] = s;
}

Stroke *stroke_list_pop(StrokeList *sl)
{
    if (sl->n == 0) return NULL;
    return sl->strokes[--sl->n];
}

void stroke_list_clear(StrokeList *sl)
{
    for (int i = 0; i < sl->n; i++)
        stroke_free(sl->strokes[i]);
    sl->n = 0;
}

void stroke_list_free(StrokeList *sl)
{
    stroke_list_clear(sl);
    free(sl->strokes);
    free(sl);
}
