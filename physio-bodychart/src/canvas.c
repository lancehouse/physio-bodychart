#include "canvas.h"
#include "stroke.h"
#include "body_outlines.h"
#include "overlays.h"
#include "overlay_svg.h"
#include "obj_chart.h"
#include <math.h>
#include <string.h>
#include <stdio.h>

/* ── Per-drawing-area context ────────────────────────────────────────────── *
 * g_col[0..3]  — quad view slots (anterior, posterior, lateral_l, lateral_r) *
 * g_col[4..7]  — matching single-view slots (same order)                    */
/* Cache surface dimensions in pixels (body space is 200×400 units; 2 px/bu). */
#define STROKE_CACHE_W 400
#define STROKE_CACHE_H 800

typedef struct {
    AppState  *app;
    BodyView   view;
    double    *p_zoom;
    double    *p_pan_x;
    double    *p_pan_y;
    double     last_zoom_scale;
    double     last_cx, last_cy;
    double     mid_pan_x0, mid_pan_y0;  /* pan at start of middle-button drag */
    double     mouse_x, mouse_y;        /* last known cursor position (screen px) */
    GtkWidget *da;
    GtkWidget *zoom_btn;
    GtkWidget *header_label;

    /* Committed-stroke offscreen cache.
     * Strokes and arrows for cd->view are rendered into this 400×800 image
     * surface (2 px per body-unit) whenever stroke_version changes.
     * During on_col_draw the cache is composited at the correct scale/offset
     * so only the active stroke and arrow preview are re-rendered each frame. */
    cairo_surface_t *stroke_cache;
    int              cache_stroke_version;  /* value of app->stroke_version when cache was built */
} ColData;

static ColData g_col[8];

/* Fixed single-view slot order */
static const BodyView SINGLE_SLOT_VIEWS[4] = {
    VIEW_ANTERIOR, VIEW_POSTERIOR, VIEW_LATERAL_L, VIEW_LATERAL_R
};

/* ── Stroke rendering ────────────────────────────────────────────────────── *
 * All widths/sizes are body-space units (body = 200×400 bu). They scale      *
 * naturally with zoom because Cairo is already in body-space after the       *
 * col transform. Symbol patterns batch all geometry into one stroke/fill.    */
static void draw_stroke(cairo_t *cr, const Stroke *s, const SymptomDef *sd,
                        const AppState *app)
{
    if (s->n_pts < 1) return;

    cairo_set_line_cap(cr, CAIRO_LINE_CAP_ROUND);
    cairo_set_line_join(cr, CAIRO_LINE_JOIN_ROUND);
    cairo_set_dash(cr, NULL, 0, 0);

    switch (sd->pattern) {

    case FILL_SOLID: {
        /* Pressure tracks within two bands selected by s->wide_mode:
         *   thin: 0.5–6.0 bu   wide: 1.5–9.5 bu */
        if (s->n_pts < 2) break;
        size_t n = s->n_pts;
        double p_cur = s->pts[0].pressure;
        double w_cur = s->wide_mode ? (1.5 + p_cur * 8.0) : (0.5 + p_cur * 5.5);
        cairo_set_line_width(cr, w_cur);
        cairo_set_source_rgba(cr, sd->r, sd->g, sd->b, 1.0);
        cairo_move_to(cr, s->pts[0].x, s->pts[0].y);
        for (size_t i = 1; i < n; i++) {
            double p = (s->pts[i-1].pressure + s->pts[i].pressure) * 0.5;
            double w = s->wide_mode ? (1.5 + p * 8.0) : (0.5 + p * 5.5);
            if (fabs(w - w_cur) > 0.5) {
                cairo_stroke(cr);
                w_cur = w;
                cairo_set_line_width(cr, w_cur);
                cairo_set_source_rgba(cr, sd->r, sd->g, sd->b, 1.0);
                cairo_move_to(cr, s->pts[i-1].x, s->pts[i-1].y);
            }
            /* Catmull-Rom control points for segment pts[i-1] → pts[i] */
            double x0 = (i >= 2) ? (double)s->pts[i-2].x : 2.0*s->pts[i-1].x - s->pts[i].x;
            double y0 = (i >= 2) ? (double)s->pts[i-2].y : 2.0*s->pts[i-1].y - s->pts[i].y;
            double x3 = (i+1 < n) ? (double)s->pts[i+1].x : 2.0*s->pts[i].x - s->pts[i-1].x;
            double y3 = (i+1 < n) ? (double)s->pts[i+1].y : 2.0*s->pts[i].y - s->pts[i-1].y;
            double cp1x = s->pts[i-1].x + (s->pts[i].x - x0) / 6.0;
            double cp1y = s->pts[i-1].y + (s->pts[i].y - y0) / 6.0;
            double cp2x = s->pts[i].x   - (x3 - s->pts[i-1].x) / 6.0;
            double cp2y = s->pts[i].y   - (y3 - s->pts[i-1].y) / 6.0;
            cairo_curve_to(cr, cp1x, cp1y, cp2x, cp2y, s->pts[i].x, s->pts[i].y);
        }
        cairo_stroke(cr);
        break;
    }

    case FILL_DASHED: {
        /* Finer pink dashes; pressure sets width. thin: 0.3–3.1 bu  wide: 0.8–5.8 bu */
        if (s->n_pts < 2) break;
        size_t n = s->n_pts;
        double avg_p = 0.0;
        for (size_t i = 0; i < n; i++) avg_p += s->pts[i].pressure;
        avg_p /= (double)n;
        cairo_set_line_width(cr, s->wide_mode ? (0.8 + avg_p * 5.0) : (0.3 + avg_p * 2.8));
        cairo_set_source_rgba(cr, sd->r, sd->g, sd->b, 1.0);
        double dashes[2] = { 6.0, 4.0 };
        cairo_set_dash(cr, dashes, 2, 0);
        cairo_move_to(cr, s->pts[0].x, s->pts[0].y);
        for (size_t i = 1; i < n; i++) {
            double x0 = (i >= 2) ? (double)s->pts[i-2].x : 2.0*s->pts[i-1].x - s->pts[i].x;
            double y0 = (i >= 2) ? (double)s->pts[i-2].y : 2.0*s->pts[i-1].y - s->pts[i].y;
            double x3 = (i+1 < n) ? (double)s->pts[i+1].x : 2.0*s->pts[i].x - s->pts[i-1].x;
            double y3 = (i+1 < n) ? (double)s->pts[i+1].y : 2.0*s->pts[i].y - s->pts[i-1].y;
            double cp1x = s->pts[i-1].x + (s->pts[i].x - x0) / 6.0;
            double cp1y = s->pts[i-1].y + (s->pts[i].y - y0) / 6.0;
            double cp2x = s->pts[i].x   - (x3 - s->pts[i-1].x) / 6.0;
            double cp2y = s->pts[i].y   - (y3 - s->pts[i-1].y) / 6.0;
            cairo_curve_to(cr, cp1x, cp1y, cp2x, cp2y, s->pts[i].x, s->pts[i].y);
        }
        cairo_stroke(cr);
        cairo_set_dash(cr, NULL, 0, 0);
        break;
    }

    case FILL_DOTS_SPACED: {
        /* Pressure controls COUNT of dots placed side-by-side perpendicular to stroke:
         *   p<0.40 → 1 dot   0.40–0.65 → 2 dots   0.65–0.82 → 3 dots   ≥0.82 → 4 dots
         * Dots are all the same radius (fixed, no size scaling with pressure). */
        double dot_r   = (double)app->pen_dot_radius;
        double spacing = (double)app->pen_dot_spacing;
        double dot_gap = dot_r * 2.5;  /* centre-to-centre perpendicular gap */
        cairo_set_source_rgba(cr, sd->r, sd->g, sd->b, 1.0);

        /* Stamp helper macro — places cnt dots perpendicular to (nx, ny) */
        #define STAMP_DOTS(px_, py_, nx_, ny_, cnt_) do { \
            double _o0 = -((cnt_) - 1) * 0.5 * dot_gap; \
            for (int _k = 0; _k < (cnt_); _k++) { \
                double _off = _o0 + _k * dot_gap; \
                cairo_new_sub_path(cr); \
                cairo_arc(cr, (px_) + (nx_)*_off, (py_) + (ny_)*_off, \
                          dot_r, 0, 2*M_PI); \
            } \
        } while (0)

        /* First point — no segment tangent yet; perp defaults to (0,1) */
        {
            double p = s->pts[0].pressure;
            int cnt = (p < 0.40) ? 1 : (p < 0.65) ? 2 : (p < 0.82) ? 3 : 4;
            STAMP_DOTS(s->pts[0].x, s->pts[0].y, 0.0, 1.0, cnt);
        }

        double accum = 0.0;
        for (size_t i = 1; i < s->n_pts; i++) {
            double dx  = s->pts[i].x - s->pts[i-1].x;
            double dy  = s->pts[i].y - s->pts[i-1].y;
            double len = sqrt(dx*dx + dy*dy);
            if (len < 1e-9) continue;
            double inv = 1.0 / len;
            double nx  = -dy * inv;   /* perpendicular to tangent */
            double ny  =  dx * inv;
            double need = spacing - accum;
            while (need <= len) {
                double t   = need / len;
                double px  = s->pts[i-1].x + t * dx;
                double py  = s->pts[i-1].y + t * dy;
                double p   = s->pts[i-1].pressure * (1.0 - t) + s->pts[i].pressure * t;
                int cnt = (p < 0.40) ? 1 : (p < 0.65) ? 2 : (p < 0.82) ? 3 : 4;
                STAMP_DOTS(px, py, nx, ny, cnt);
                need += spacing;
            }
            accum = len - (need - spacing);
        }
        #undef STAMP_DOTS
        cairo_fill(cr);
        break;
    }

    case FILL_H_STROKES: {
        /* Pressure controls dash LENGTH and COUNT (stacked vertically):
         *   p<0.45        → 1 short dash  (0.7× pen_dash_len)
         *   0.45–0.65     → 1 long dash   (1.4×)
         *   0.65–0.85     → 2 short dashes stacked
         *   ≥0.85         → 2 long dashes stacked
         * Dashes are always horizontal; stroke width set by pen_dash_width. */
        double dash_len = (double)app->pen_dash_len;
        double spacing  = (double)app->pen_dash_spacing;
        double lw       = (double)app->pen_dash_width;
        double dash_gap = dash_len * 0.9 + lw;  /* vertical gap between stacked dashes */
        cairo_set_source_rgba(cr, sd->r, sd->g, sd->b, 1.0);
        cairo_set_line_width(cr, lw);

        #define STAMP_DASHES(px_, py_, p_) do { \
            int   _cnt  = ((p_) >= 0.65) ? 2 : 1; \
            int   _long = (((p_) >= 0.45) && ((p_) < 0.65)) || ((p_) >= 0.85); \
            double _hw  = _long ? dash_len * 1.4 : dash_len * 0.7; \
            double _o0  = -(_cnt - 1) * 0.5 * dash_gap; \
            for (int _k = 0; _k < _cnt; _k++) { \
                double _yo = _o0 + _k * dash_gap; \
                cairo_move_to(cr, (px_) - _hw, (py_) + _yo); \
                cairo_line_to(cr, (px_) + _hw, (py_) + _yo); \
            } \
        } while (0)

        double accum = spacing * 0.5;
        for (size_t i = 1; i < s->n_pts; i++) {
            double dx  = s->pts[i].x - s->pts[i-1].x;
            double dy  = s->pts[i].y - s->pts[i-1].y;
            double len = sqrt(dx*dx + dy*dy);
            if (len < 1e-9) continue;
            double need = spacing - accum;
            while (need <= len) {
                double t   = need / len;
                double px  = s->pts[i-1].x + t * dx;
                double py  = s->pts[i-1].y + t * dy;
                double p   = s->pts[i-1].pressure * (1.0 - t) + s->pts[i].pressure * t;
                STAMP_DASHES(px, py, p);
                need += spacing;
            }
            accum = len - (need - spacing);
        }
        #undef STAMP_DASHES
        cairo_stroke(cr);
        break;
    }

    case FILL_XMARKS: {
        /* Pressure controls COUNT of X marks placed side-by-side perpendicular to stroke:
         *   p<0.40 → 1 X   0.40–0.65 → 2 X   0.65–0.82 → 3 X   ≥0.82 → 4 X
         * Stroke width set by pen_x_width. */
        double arm     = (double)app->pen_x_arm;
        double spacing = (double)app->pen_x_spacing;
        double lw      = (double)app->pen_x_width;
        double x_gap   = arm * 2.6;  /* centre-to-centre perpendicular gap */
        cairo_set_source_rgba(cr, sd->r, sd->g, sd->b, 1.0);
        cairo_set_line_width(cr, lw);

        #define STAMP_XS(px_, py_, nx_, ny_, cnt_) do { \
            double _o0 = -((cnt_) - 1) * 0.5 * x_gap; \
            for (int _k = 0; _k < (cnt_); _k++) { \
                double _off = _o0 + _k * x_gap; \
                double _cx = (px_) + (nx_)*_off; \
                double _cy = (py_) + (ny_)*_off; \
                cairo_move_to(cr, _cx - arm, _cy - arm); \
                cairo_line_to(cr, _cx + arm, _cy + arm); \
                cairo_move_to(cr, _cx + arm, _cy - arm); \
                cairo_line_to(cr, _cx - arm, _cy + arm); \
            } \
        } while (0)

        double accum = spacing * 0.5;
        for (size_t i = 1; i < s->n_pts; i++) {
            double dx  = s->pts[i].x - s->pts[i-1].x;
            double dy  = s->pts[i].y - s->pts[i-1].y;
            double len = sqrt(dx*dx + dy*dy);
            if (len < 1e-9) continue;
            double inv = 1.0 / len;
            double nx  = -dy * inv;
            double ny  =  dx * inv;
            double need = spacing - accum;
            while (need <= len) {
                double t   = need / len;
                double px  = s->pts[i-1].x + t * dx;
                double py  = s->pts[i-1].y + t * dy;
                double p   = s->pts[i-1].pressure * (1.0 - t) + s->pts[i].pressure * t;
                int cnt = (p < 0.40) ? 1 : (p < 0.65) ? 2 : (p < 0.82) ? 3 : 4;
                STAMP_XS(px, py, nx, ny, cnt);
                need += spacing;
            }
            accum = len - (need - spacing);
        }
        #undef STAMP_XS
        cairo_stroke(cr);
        break;
    }

    case FILL_TICK: {
        /* Checkmarks: pressure scales stroke width. */
        double avg_p = 0.0;
        for (size_t i = 0; i < s->n_pts; i++) avg_p += s->pts[i].pressure;
        if (s->n_pts > 0) avg_p /= (double)s->n_pts;
        cairo_set_source_rgba(cr, sd->r, sd->g, sd->b, 1.0);
        cairo_set_line_width(cr, 1.0 + avg_p * 1.4);
        cairo_set_line_cap(cr, CAIRO_LINE_CAP_ROUND);
        cairo_set_line_join(cr, CAIRO_LINE_JOIN_ROUND);

        #define TICK_AT(px, py) \
            cairo_move_to(cr, (px) - 4.5, (py) - 0.5); \
            cairo_line_to(cr, (px) - 1.0, (py) + 3.5); \
            cairo_line_to(cr, (px) + 5.5, (py) - 4.0);

        TICK_AT(s->pts[0].x, s->pts[0].y)

        double spacing = 14.0;
        double accum   = 0.0;
        for (size_t i = 1; i < s->n_pts; i++) {
            double dx  = s->pts[i].x - s->pts[i-1].x;
            double dy  = s->pts[i].y - s->pts[i-1].y;
            double len = sqrt(dx*dx + dy*dy);
            if (len < 1e-9) continue;
            double need = spacing - accum;
            while (need <= len) {
                double t = need / len;
                TICK_AT(s->pts[i-1].x + t * dx, s->pts[i-1].y + t * dy)
                need += spacing;
            }
            accum = len - (need - spacing);
        }
        #undef TICK_AT
        cairo_stroke(cr);
        break;
    }

    } /* switch */
}

/* ── Coordinate transform ────────────────────────────────────────────────── */
static double col_base_scale(double w, double h)
{
    return fmin(w / 200.0, h / 400.0);
}

static void apply_col_transform(cairo_t *cr, ColData *cd, double w, double h)
{
    double s = col_base_scale(w, h) * (*cd->p_zoom);
    if (s <= 0.0) return;
    double cx = w / 2.0 + (*cd->p_pan_x);
    double cy = h / 2.0 + (*cd->p_pan_y);
    cairo_translate(cr, cx, cy);
    cairo_scale(cr, s, s);
    cairo_translate(cr, -100.0, -200.0);
}

static void screen_to_body(ColData *cd, double sx, double sy,
                            double *bx, double *by)
{
    double w  = (double)gtk_widget_get_width(cd->da);
    double h  = (double)gtk_widget_get_height(cd->da);
    double s  = col_base_scale(w, h) * (*cd->p_zoom);
    double cx = w / 2.0 + (*cd->p_pan_x);
    double cy = h / 2.0 + (*cd->p_pan_y);
    *bx = (sx - cx) / s + 100.0;
    *by = (sy - cy) / s + 200.0;
}

/* ── Screen-space hit testing for draggable annotations ─────────────────── */
static void label_anchor_resolve(const NoteAnnotation *na,
                                  double *out_lbx, double *out_lby);  /* fwd */

/* Returns index of the note whose label box contains (sx, sy), or -1 */
static int note_hit_screen(AppState *app, ColData *cd, double sx, double sy)
{
    double w  = (double)gtk_widget_get_width(cd->da);
    double h  = (double)gtk_widget_get_height(cd->da);
    double s  = col_base_scale(w, h) * (*cd->p_zoom);
    double cx = w / 2.0 + (*cd->p_pan_x);
    double cy = h / 2.0 + (*cd->p_pan_y);
    for (int i = 0; i < app->note_count; i++) {
        const NoteAnnotation *na = &app->notes[i];
        if (na->view != (int)cd->view) continue;
        double lbx, lby;
        label_anchor_resolve(na, &lbx, &lby);
        double lsx = (lbx - 100.0) * s + cx;
        double lsy = (lby - 200.0) * s + cy;
        /* Approximate label box: bw~180, bh~40, box_ly = lsy - bh */
        if (sx >= lsx        && sx <= lsx + 180 &&
            sy >= lsy - 40   && sy <= lsy)
            return i;
    }
    return -1;
}

static gboolean link_summary_hit_screen(AppState *app, ColData *cd,
                                         double sx, double sy)
{
    if (!app->link_summary_active) return FALSE;
    /* No view restriction — box is draggable from any panel */
    double w  = (double)gtk_widget_get_width(cd->da);
    double h  = (double)gtk_widget_get_height(cd->da);
    double s  = col_base_scale(w, h) * (*cd->p_zoom);
    double cx = w / 2.0 + (*cd->p_pan_x);
    double cy = h / 2.0 + (*cd->p_pan_y);
    double lsx = (app->link_summary_bx - 100.0) * s + cx;
    double lsy = (app->link_summary_by - 200.0) * s + cy;
    return (sx >= lsx - 5   && sx <= lsx + 80 &&
            sy >= lsy - 225  && sy <= lsy + 5);
}

static int arrow_head_hit_screen(AppState *app, ColData *cd,
                                  double sx, double sy)
{
    double w  = (double)gtk_widget_get_width(cd->da);
    double h  = (double)gtk_widget_get_height(cd->da);
    double s  = col_base_scale(w, h) * (*cd->p_zoom);
    double acx = w / 2.0 + (*cd->p_pan_x);
    double acy = h / 2.0 + (*cd->p_pan_y);
    for (int i = 0; i < app->arrow_count; i++) {
        if (app->arrows[i].view != (int)cd->view) continue;
        double ax = (app->arrows[i].x2 - 100.0) * s + acx;
        double ay = (app->arrows[i].y2 - 200.0) * s + acy;
        double dx = sx - ax, dy = sy - ay;
        if (sqrt(dx*dx + dy*dy) < 20.0) return i;
    }
    return -1;
}

static int obj_point_hit_screen(AppState *app, ColData *cd, double sx, double sy)
{
    double w  = (double)gtk_widget_get_width(cd->da);
    double h  = (double)gtk_widget_get_height(cd->da);
    double s  = col_base_scale(w, h) * (*cd->p_zoom);
    double cx = w / 2.0 + (*cd->p_pan_x);
    double cy = h / 2.0 + (*cd->p_pan_y);
    for (int i = app->obj_point_count - 1; i >= 0; i--) {
        const ObjPoint *p = &app->obj_points[i];
        if (p->view != (int)cd->view) continue;
        double px = (p->bx - 100.0) * s + cx;
        double py = (p->by - 200.0) * s + cy;
        double dx = sx - px, dy = sy - py;
        if (dx*dx + dy*dy < 22.0 * 22.0) return i;
    }
    return -1;
}

/* ── Link summary rendering (graphical Cairo arrows, screen-space) ────────── */
static void draw_link_summary_screen(cairo_t *cr, AppState *app,
                                      double sx, double sy)
{
    if (!app->link_summary_active || app->link_rel_count == 0) return;

    const double pad   = 6.0;
    const double row_h = 20.0;
    const double fsz   = 11.0;
    const double bw    = 72.0;

    int    n  = app->link_rel_count;
    double bh = n * row_h + 2.0 * pad;

    cairo_save(cr);

    /* Background box — bottom-left anchored at (sx, sy) */
    cairo_set_source_rgba(cr, 0.95, 0.95, 0.82, 0.94);
    cairo_rectangle(cr, sx, sy - bh, bw, bh);
    cairo_fill(cr);
    cairo_set_source_rgba(cr, 0.25, 0.25, 0.25, 0.85);
    cairo_set_line_width(cr, 0.8);
    cairo_rectangle(cr, sx, sy - bh, bw, bh);
    cairo_stroke(cr);

    cairo_select_font_face(cr, "Sans",
                           CAIRO_FONT_SLANT_NORMAL, CAIRO_FONT_WEIGHT_BOLD);
    cairo_set_font_size(cr, fsz);

    for (int i = 0; i < n; i++) {
        const LinkRel *rel = &app->link_relations[i];
        double ry = sy - bh + pad + (i + 0.5) * row_h;  /* row vertical centre */
        double rx = sx + pad;

        /* From-number */
        char nbuf[16];
        snprintf(nbuf, sizeof(nbuf), "%d", rel->from + 1);
        cairo_set_source_rgba(cr, 0.1, 0.1, 0.1, 1.0);
        cairo_move_to(cr, rx, ry + 4.0);
        cairo_show_text(cr, nbuf);

        /* Arrow body */
        double ax        = rx + 17.0;   /* stem start */
        double tip_x     = ax + 26.0;   /* arrowhead tip */
        double head_base = tip_x - 8.0; /* arrowhead base */

        if (rel->state == LINK_YES)
            cairo_set_source_rgba(cr, 0.1, 0.45, 0.1, 1.0);
        else
            cairo_set_source_rgba(cr, 0.50, 0.50, 0.50, 0.90);

        /* Stem */
        cairo_set_line_width(cr, 1.5);
        cairo_move_to(cr, ax, ry);
        cairo_line_to(cr, head_base, ry);
        cairo_stroke(cr);

        /* Filled arrowhead */
        cairo_move_to(cr, tip_x, ry);
        cairo_line_to(cr, head_base, ry - 5.0);
        cairo_line_to(cr, head_base, ry + 5.0);
        cairo_close_path(cr);
        cairo_fill(cr);

        /* Red diagonal slash for LINK_NO */
        if (rel->state == LINK_NO) {
            cairo_set_source_rgba(cr, 0.85, 0.10, 0.10, 1.0);
            cairo_set_line_width(cr, 2.0);
            double cx = ax + 10.0;
            cairo_move_to(cr, cx - 5.0, ry + 7.0);
            cairo_line_to(cr, cx + 5.0, ry - 7.0);
            cairo_stroke(cr);
        }

        /* To-number */
        snprintf(nbuf, sizeof(nbuf), "%d", rel->to + 1);
        cairo_set_source_rgba(cr, 0.1, 0.1, 0.1, 1.0);
        cairo_move_to(cr, tip_x + 3.0, ry + 4.0);
        cairo_show_text(cr, nbuf);
    }

    cairo_restore(cr);
}

/* ── Legend rendering (screen-space, shows zone and point types) ───────── */
/* ── Note annotation rendering (screen-space, fixed pixel size) ─────────── */
/* Resolve label position: default offset from spot when not user-placed */
static void label_anchor_resolve(const NoteAnnotation *na,
                                  double *out_lbx, double *out_lby)
{
    if (na->label.placed) {
        *out_lbx = na->label.lx;
        *out_lby = na->label.ly;
    } else {
        *out_lbx = na->bx + 12.0;
        *out_lby = na->by - 8.0;
    }
}

/* Draw the connector line + arrowhead from label-box edge to spot.
 * All coords are screen-space. */
static void draw_note_connector(cairo_t *cr,
                                 double spot_sx, double spot_sy,
                                 double box_lx,  double box_ly,
                                 double bw,       double bh)
{
    double box_cx = box_lx + bw / 2.0;
    double box_cy = box_ly + bh / 2.0;
    double dx = spot_sx - box_cx, dy = spot_sy - box_cy;
    double dist = sqrt(dx * dx + dy * dy);
    if (dist < 8.0) return;

    /* Unit vector from box centre toward spot */
    double ux = dx / dist, uy = dy / dist;

    /* Exact intersection of the ray with the rectangle boundary */
    double tx = (ux != 0.0) ? (bw / 2.0) / fabs(ux) : 1e9;
    double ty = (uy != 0.0) ? (bh / 2.0) / fabs(uy) : 1e9;
    double t  = fmin(tx, ty);
    double start_x = box_cx + ux * t;
    double start_y = box_cy + uy * t;

    /* Arrowhead tip lands at the spot dot edge */
    double spot_r = 5.5;
    double end_x  = spot_sx - ux * spot_r;
    double end_y  = spot_sy - uy * spot_r;

    double head = 12.0;
    double hw   = 5.0;
    double px   = -uy, py = ux;
    double hbx  = end_x - ux * head;
    double hby  = end_y - uy * head;

    /* Shaft */
    cairo_set_source_rgba(cr, 0.15, 0.15, 0.15, 0.85);
    cairo_set_line_width(cr, 2.0);
    cairo_set_line_cap(cr, CAIRO_LINE_CAP_ROUND);
    cairo_move_to(cr, start_x, start_y);
    cairo_line_to(cr, hbx, hby);   /* stop at head base so it doesn't show behind head */
    cairo_stroke(cr);

    /* Filled arrowhead */
    cairo_move_to(cr, end_x, end_y);
    cairo_line_to(cr, hbx + px * hw, hby + py * hw);
    cairo_line_to(cr, hbx - px * hw, hby - py * hw);
    cairo_close_path(cr);
    cairo_fill(cr);
}

/* Render one note annotation: spot dot, connector, 2-line label box.
 * spot_sx/sy and label_sx/sy are screen-space. */
static void draw_note_screen(cairo_t *cr, const NoteAnnotation *na,
                              double spot_sx, double spot_sy,
                              double label_sx, double label_sy)
{
    double pad = 4.0;
    double fsz = 14.0;

    cairo_save(cr);
    cairo_select_font_face(cr, "Sans",
                           CAIRO_FONT_SLANT_NORMAL, CAIRO_FONT_WEIGHT_BOLD);
    cairo_set_font_size(cr, fsz);

    /* Split text on '\n' into up to 2 lines */
    char line1[128] = {0}, line2[128] = {0};
    const char *nl = strchr(na->text, '\n');
    if (nl) {
        int len1 = (int)(nl - na->text);
        if (len1 >= (int)sizeof(line1)) len1 = (int)sizeof(line1) - 1;
        memcpy(line1, na->text, (size_t)len1);
        snprintf(line2, sizeof(line2), "%s", nl + 1);
    } else {
        snprintf(line1, sizeof(line1), "%s", na->text);
    }

    cairo_text_extents_t e1, e2;
    cairo_text_extents(cr, line1, &e1);
    cairo_text_extents(cr, line2[0] ? line2 : " ", &e2);

    double line_h = -e1.y_bearing;            /* ascent */
    double gap    = 2.0;
    double bw = fmax(e1.width - e1.x_bearing, e2.width - e2.x_bearing) + 2.0 * pad;
    double bh = (line2[0] ? (line_h * 2.0 + gap) : line_h) + 2.0 * pad;

    /* Label box is drawn with its reference point as its left-baseline */
    double box_lx = label_sx;
    double box_ly = label_sy - bh;   /* box above reference */

    /* Connector first (drawn behind label box) */
    draw_note_connector(cr, spot_sx, spot_sy, box_lx, box_ly, bw, bh);

    /* Filled label box */
    cairo_set_source_rgba(cr, 1.0, 1.0, 0.82, 0.93);
    cairo_rectangle(cr, box_lx, box_ly, bw, bh);
    cairo_fill(cr);

    /* Border */
    cairo_set_source_rgba(cr, 0.25, 0.25, 0.25, 0.85);
    cairo_set_line_width(cr, 0.8);
    cairo_rectangle(cr, box_lx, box_ly, bw, bh);
    cairo_stroke(cr);

    /* Spot dot — filled circle with white ring so it reads on any background */
    cairo_set_source_rgba(cr, 1.0, 1.0, 1.0, 0.90);
    cairo_arc(cr, spot_sx, spot_sy, 7.0, 0, 2 * M_PI);
    cairo_fill(cr);
    cairo_set_source_rgba(cr, 0.12, 0.12, 0.12, 0.92);
    cairo_arc(cr, spot_sx, spot_sy, 5.5, 0, 2 * M_PI);
    cairo_fill(cr);

    /* Text lines */
    cairo_set_source_rgba(cr, 0.05, 0.05, 0.05, 1.0);
    cairo_move_to(cr, box_lx + pad - e1.x_bearing,
                      box_ly + pad + line_h);
    cairo_show_text(cr, line1);
    if (line2[0]) {
        cairo_move_to(cr, box_lx + pad - e2.x_bearing,
                          box_ly + pad + line_h * 2.0 + gap);
        cairo_show_text(cr, line2);
    }

    cairo_restore(cr);
}

/* ── Arrow path tracking (bezier curve fit) ─────────────────────────────── */
static void arrow_track_add(AppState *app, double bx, double by)
{
    if (app->arrow_track_n == 32) {
        for (int i = 0; i < 16; i++) {
            app->arrow_track_x[i] = app->arrow_track_x[i * 2];
            app->arrow_track_y[i] = app->arrow_track_y[i * 2];
        }
        app->arrow_track_n = 16;
    }
    app->arrow_track_x[app->arrow_track_n] = bx;
    app->arrow_track_y[app->arrow_track_n] = by;
    app->arrow_track_n++;
}

/* Returns the quadratic bezier control point that makes the curve pass
 * through the sampled midpoint at t≈0.5. */
static void arrow_get_cp(const AppState *app, double *cpx, double *cpy)
{
    if (app->arrow_track_n >= 2) {
        double mx = app->arrow_track_x[app->arrow_track_n / 2];
        double my = app->arrow_track_y[app->arrow_track_n / 2];
        *cpx = 2.0 * mx - 0.5 * (app->arrow_x1 + app->arrow_x2);
        *cpy = 2.0 * my - 0.5 * (app->arrow_y1 + app->arrow_y2);
    } else {
        *cpx = (app->arrow_x1 + app->arrow_x2) * 0.5;
        *cpy = (app->arrow_y1 + app->arrow_y2) * 0.5;
    }
}

/* ── Arrow rendering (body-space coordinates, quadratic bezier) ─────────── */
static void draw_arrow_body_space(cairo_t *cr,
                                   double x1, double y1,
                                   double cx, double cy,
                                   double x2, double y2)
{
    double dx = x2 - x1, dy = y2 - y1;
    double len = sqrt(dx*dx + dy*dy);
    if (len < 1.0) return;

    /* Tangent at tip = Q'(1) = 2*(P2 - control); use for head orientation */
    double tx = x2 - cx, ty = y2 - cy;
    double tlen = sqrt(tx*tx + ty*ty);
    if (tlen < 1e-9) { tx = dx; ty = dy; tlen = len; }
    tx /= tlen; ty /= tlen;

    double head_len = fmin(6.0, len * 0.22);
    double half_w   = head_len * 0.38;
    double px = -ty, py = tx;
    double hbx = x2 - tx * head_len;
    double hby = y2 - ty * head_len;

    cairo_set_source_rgba(cr, 0.0, 0.0, 0.0, 0.88);
    cairo_set_line_width(cr, 0.8);
    cairo_set_line_cap(cr, CAIRO_LINE_CAP_ROUND);

    /* Quadratic bezier shaft (converted to cubic for Cairo).
     * Shaft ends at head base, not tip, so the head sits clean. */
    double c1x = x1  + (2.0/3.0) * (cx - x1);
    double c1y = y1  + (2.0/3.0) * (cy - y1);
    double c2x = hbx + (2.0/3.0) * (cx - hbx);
    double c2y = hby + (2.0/3.0) * (cy - hby);
    cairo_move_to(cr, x1, y1);
    cairo_curve_to(cr, c1x, c1y, c2x, c2y, hbx, hby);
    cairo_stroke(cr);

    /* Filled triangular arrowhead */
    cairo_move_to(cr, x2, y2);
    cairo_line_to(cr, hbx + px * half_w, hby + py * half_w);
    cairo_line_to(cr, hbx - px * half_w, hby - py * half_w);
    cairo_close_path(cr);
    cairo_fill(cr);
}

/* ── Offscreen render (used by session export) ───────────────────────────── */
void canvas_render_view(AppState *app, cairo_t *cr, BodyView view,
                        double w, double h,
                        double zoom, double pan_x, double pan_y)
{
    double s  = col_base_scale(w, h) * zoom;
    double cx = w / 2.0 + pan_x;
    double cy = h / 2.0 + pan_y;

    cairo_save(cr);
    cairo_translate(cr, cx, cy);
    cairo_scale(cr, s, s);
    cairo_translate(cr, -100.0, -200.0);

    cairo_set_source_rgb(cr, 0.18, 0.18, 0.18);
    cairo_set_line_width(cr, 1.8);
    body_outline_draw(cr, view);

    if (app->current_mode == APP_MODE_OBJECTIVE) {
        obj_chart_render_body(app, cr, (int)view);
    } else {
        for (int i = 0; i < app->strokes->n; i++) {
            Stroke *sk = app->strokes->strokes[i];
            if (sk->view != (int)view) continue;
            draw_stroke(cr, sk, &SYMPTOM_DEFS[sk->type], app);
        }

        for (int i = 0; i < app->arrow_count; i++) {
            if (app->arrows[i].view != (int)view) continue;
            draw_arrow_body_space(cr, app->arrows[i].x1, app->arrows[i].y1,
                                  app->arrows[i].cx,  app->arrows[i].cy,
                                  app->arrows[i].x2,  app->arrows[i].y2);
        }
    }

    cairo_restore(cr);

    if (app->current_mode == APP_MODE_OBJECTIVE) {
        obj_chart_render_screen(app, cr, (int)view, s, cx, cy);
    } else {
        /* Note annotations in screen space */
        for (int i = 0; i < app->note_count; i++) {
            const NoteAnnotation *na = &app->notes[i];
            if (na->view != (int)view) continue;
            double spot_sx = (na->bx - 100.0) * s + cx;
            double spot_sy = (na->by - 200.0) * s + cy;
            double lbx, lby;
            label_anchor_resolve(na, &lbx, &lby);
            draw_note_screen(cr, na, spot_sx, spot_sy,
                             (lbx - 100.0) * s + cx,
                             (lby - 200.0) * s + cy);
        }

        /* Link summary shown in all views */
        if (app->link_summary_active)
            draw_link_summary_screen(cr, app,
                                      (app->link_summary_bx - 100.0) * s + cx,
                                      (app->link_summary_by - 200.0) * s + cy);
    }
}

/* ── Committed-stroke cache management ────────────────────────────────────── *
 * rebuild_stroke_cache() renders all committed strokes and arrows for          *
 * cd->view into cd->stroke_cache (STROKE_CACHE_W × STROKE_CACHE_H pixels,     *
 * 2 px per body-unit).  The cache is then stamped onto the screen surface in   *
 * on_col_draw instead of re-iterating the full stroke list every frame.        *
 *                                                                               *
 * Cache space: body (0,0) maps to pixel (0,0); body (200,400) → pixel          *
 * (400,800).  The transform is simply scale(2,2) from body space.              */
static void rebuild_stroke_cache(ColData *cd)
{
    AppState *app = cd->app;

    /* (Re-)create the image surface */
    if (cd->stroke_cache)
        cairo_surface_destroy(cd->stroke_cache);
    cd->stroke_cache = cairo_image_surface_create(
        CAIRO_FORMAT_ARGB32, STROKE_CACHE_W, STROKE_CACHE_H);

    cairo_t *cr = cairo_create(cd->stroke_cache);

    /* Clear to transparent */
    cairo_set_operator(cr, CAIRO_OPERATOR_CLEAR);
    cairo_paint(cr);
    cairo_set_operator(cr, CAIRO_OPERATOR_OVER);

    /* Body space: 1 body-unit = 2 pixels */
    cairo_scale(cr, 2.0, 2.0);

    /* Committed strokes */
    for (int i = 0; i < app->strokes->n; i++) {
        Stroke *s = app->strokes->strokes[i];
        if (s->view != (int)cd->view) continue;
        draw_stroke(cr, s, &SYMPTOM_DEFS[s->type], app);
    }

    /* Committed arrows */
    for (int i = 0; i < app->arrow_count; i++) {
        if (app->arrows[i].view != (int)cd->view) continue;
        draw_arrow_body_space(cr, app->arrows[i].x1, app->arrows[i].y1,
                              app->arrows[i].cx,  app->arrows[i].cy,
                              app->arrows[i].x2,  app->arrows[i].y2);
    }

    cairo_destroy(cr);
    cd->cache_stroke_version = app->stroke_version;
}

/* ── Draw callback ───────────────────────────────────────────────────────── */
static void on_col_draw(GtkDrawingArea *da, cairo_t *cr,
                        int width, int height, gpointer user_data)
{
    ColData  *cd  = user_data;
    AppState *app = cd->app;
    (void)da;

    cairo_set_source_rgb(cr, 1.0, 1.0, 1.0);
    cairo_paint(cr);

    cairo_save(cr);
    apply_col_transform(cr, cd, width, height);

    /* Body outline */
    cairo_set_source_rgb(cr, 0.18, 0.18, 0.18);
    cairo_set_line_width(cr, 1.8);
    body_outline_draw(cr, cd->view);

    /* Overlay */
    if (app->overlay_visible && app->overlay_category != OVERLAY_NONE) {
        if (app->overlay_category == OVERLAY_DERMATOME ||
            app->overlay_category == OVERLAY_PERIPHERAL) {
            cairo_push_group(cr);
            if (app->overlay_category == OVERLAY_DERMATOME)
                overlay_svg_draw_derm(cr, (int)cd->view);
            else
                overlay_svg_draw_periph(cr, (int)cd->view);
            cairo_pop_group_to_source(cr);
            cairo_paint_with_alpha(cr, app->overlay_alpha);
        } else {
            const OverlayDef *ov = overlay_get(app->overlay_category,
                                               app->overlay_index);
            if (ov) overlay_draw(cr, ov, (int)cd->view, app->overlay_alpha);
        }
    }

    if (app->current_mode == APP_MODE_SUBJECTIVE) {
        /* ── Committed strokes/arrows via offscreen cache ── *
         * Rebuild the cache if stroke_version changed (or first call).        *
         * Then blit the cache surface: body (0,0) is at pixel (0,0) of the   *
         * cache; cache is 2×body-space, so we draw at scale s/2 where         *
         * s = col_base_scale * zoom.  The col transform is already active.    *
         *                                                                       *
         * cairo_set_source_surface takes the surface's (0,0) as the reference *
         * point in the current coordinate system.  We're in body-space after  *
         * apply_col_transform, so we scale down by 0.5 to map cache pixels    *
         * back to body units, then paint.                                      */
        if (cd->cache_stroke_version != app->stroke_version)
            rebuild_stroke_cache(cd);

        if (cd->stroke_cache) {
            cairo_save(cr);
            /* Current transform: screen = T(cx,cy) · S(s) · T(-100,-200)
             * We want cache pixel p to land at body coordinate p/2, which
             * the existing transform already handles if we scale by 0.5. */
            cairo_scale(cr, 0.5, 0.5);
            cairo_set_source_surface(cr, cd->stroke_cache, 0.0, 0.0);
            cairo_paint(cr);
            cairo_restore(cr);
        }

        /* Active stroke (in-progress — rendered fresh every frame) */
        if (app->active_stroke && app->active_stroke->view == (int)cd->view)
            draw_stroke(cr, app->active_stroke,
                        &SYMPTOM_DEFS[app->active_stroke->type], app);

        /* Arrow preview while drawing */
        if (app->arrow_drawing && app->arrow_draw_view == (int)cd->view) {
            double cpx, cpy;
            arrow_get_cp(app, &cpx, &cpy);
            draw_arrow_body_space(cr, app->arrow_x1, app->arrow_y1,
                                  cpx, cpy,
                                  app->arrow_x2, app->arrow_y2);
        }
    } else if (app->current_mode == APP_MODE_OBJECTIVE) {
        obj_chart_render_body(app, cr, (int)cd->view);
        obj_chart_render_active_body(app, cr, (int)cd->view);
    }

    cairo_restore(cr);

    double s  = col_base_scale(width, height) * (*cd->p_zoom);
    double cx = width  / 2.0 + (*cd->p_pan_x);
    double cy = height / 2.0 + (*cd->p_pan_y);

    if (app->current_mode == APP_MODE_SUBJECTIVE) {
        /* Note annotations and link summary in screen space */
        for (int i = 0; i < app->note_count; i++) {
            const NoteAnnotation *na = &app->notes[i];
            if (na->view != (int)cd->view) continue;
            double spot_sx = (na->bx - 100.0) * s + cx;
            double spot_sy = (na->by - 200.0) * s + cy;
            double lbx, lby;
            label_anchor_resolve(na, &lbx, &lby);
            draw_note_screen(cr, na, spot_sx, spot_sy,
                             (lbx - 100.0) * s + cx,
                             (lby - 200.0) * s + cy);
        }
        if (app->link_summary_active)
            draw_link_summary_screen(cr, app,
                                      (app->link_summary_bx - 100.0) * s + cx,
                                      (app->link_summary_by - 200.0) * s + cy);
    } else if (app->current_mode == APP_MODE_OBJECTIVE) {
        obj_chart_render_screen(app, cr, (int)cd->view, s, cx, cy);
    }
}

/* ── Objective chart hit-testing (body-space) ────────────────────────────── */
static int obj_zone_hit_body(AppState *app, int view, double bx, double by)
{
    for (int i = app->obj_zone_count - 1; i >= 0; i--) {
        ObjZone *z = app->obj_zones[i];
        if (!z || z->view != view) continue;
        for (int j = 0; j < z->n; j++) {
            double dx = z->bx[j] - bx, dy = z->by[j] - by;
            if (dx*dx + dy*dy < 10.0 * 10.0) return i;
        }
    }
    return -1;
}

static int obj_point_hit_body(AppState *app, int view, double bx, double by)
{
    for (int i = app->obj_point_count - 1; i >= 0; i--) {
        ObjPoint *p = &app->obj_points[i];
        if (p->view != view) continue;
        double dx = p->bx - bx, dy = p->by - by;
        if (dx*dx + dy*dy < 12.0 * 12.0) return i;
    }
    return -1;
}

static void obj_commit_active_zone(AppState *app, GtkWidget *da)
{
    ObjZone *z = app->obj_active_zone;
    if (!z) return;
    app->obj_active_zone = NULL;
    if (z->n >= 3 && app->obj_zone_count < MAX_OBJ_ZONES) {
        app->obj_zones[app->obj_zone_count++] = z;
        if (app->obj_undo_type_top < 64)
            app->obj_undo_type_stack[app->obj_undo_type_top++] = 0;
    } else {
        obj_zone_free(z);
    }
    if (da) gtk_widget_queue_draw(da);
}

static gboolean obj_handle_erase(AppState *app, int view,
                                  double bx, double by, GtkWidget *da)
{
    int iz = obj_zone_hit_body(app, view, bx, by);
    if (iz >= 0) {
        obj_zone_free(app->obj_zones[iz]);
        for (int k = iz; k < app->obj_zone_count - 1; k++)
            app->obj_zones[k] = app->obj_zones[k + 1];
        app->obj_zone_count--;
        app->obj_zones[app->obj_zone_count] = NULL;
        if (app->obj_undo_type_top > 0 &&
            app->obj_undo_type_stack[app->obj_undo_type_top - 1] == 0)
            app->obj_undo_type_top--;
        gtk_widget_queue_draw(da);
        return TRUE;
    }
    int ip = obj_point_hit_body(app, view, bx, by);
    if (ip >= 0) {
        for (int k = ip; k < app->obj_point_count - 1; k++)
            app->obj_points[k] = app->obj_points[k + 1];
        app->obj_point_count--;
        if (app->obj_undo_type_top > 0 &&
            app->obj_undo_type_stack[app->obj_undo_type_top - 1] == 1)
            app->obj_undo_type_top--;
        gtk_widget_queue_draw(da);
        return TRUE;
    }
    return FALSE;
}

/* ── Pressure + tilt helper ──────────────────────────────────────────────── *
 * Returns raw (pre-gamma) pressure, optionally boosted by pen tilt.          *
 * pen_tilt_weight=0 ignores tilt entirely; 0.5 lets 45° tilt add ~0.35.     */
static double stylus_effective_pressure(GtkGestureStylus *gs,
                                        const AppState *app)
{
    GdkEvent *ev = gtk_gesture_get_last_event(GTK_GESTURE(gs), NULL);
    if (!ev) return 0.6;
    GdkDeviceTool *t = gdk_event_get_device_tool(ev);
    if (!t)   return 0.6;
    GdkDeviceToolType type = gdk_device_tool_get_tool_type(t);
    if (type != GDK_DEVICE_TOOL_TYPE_PEN &&
        type != GDK_DEVICE_TOOL_TYPE_ERASER) return 0.6;

    gdouble pressure = 0.6;
    gdk_event_get_axis(ev, GDK_AXIS_PRESSURE, &pressure);

    if (app->pen_tilt_weight > 0.0f) {
        gdouble xt = 0.0, yt = 0.0;
        gdk_event_get_axis(ev, GDK_AXIS_XTILT, &xt);
        gdk_event_get_axis(ev, GDK_AXIS_YTILT, &yt);
        /* GDK normalises tilt to ±1 (= ±90°). Diagonal max is √2; scale to 0–1. */
        double tilt = sqrt(xt * xt + yt * yt) * (1.0 / G_SQRT2);
        pressure = CLAMP(pressure + tilt * (double)app->pen_tilt_weight, 0.0, 1.0);
    }
    return pressure;
}

/* ── Stylus gestures ─────────────────────────────────────────────────────── */
static void on_stylus_down(GtkGestureStylus *gs, double x, double y,
                            gpointer d)
{
    ColData  *cd  = d;
    AppState *app = cd->app;
    app->current_view    = cd->view;
    app->last_stylus_us  = g_get_monotonic_time();

    GdkEvent *ev = gtk_gesture_get_last_event(GTK_GESTURE(gs), NULL);

    /* ── Barrel button detection ── */
    guint btn_num = 1;
    if (ev && GDK_IS_EVENT_TYPE(ev, GDK_BUTTON_PRESS))
        btn_num = gdk_button_event_get_button(ev);

    if (btn_num >= 2) {
        input_cancel(app);
        app->symptom = (SymptomType)((app->symptom + 1) % SYMPTOM_COUNT);
        app->tool    = TOOL_DRAW;
        if (app->toolbar_update_cb) app->toolbar_update_cb(app);
        gtk_widget_queue_draw(cd->da);
        return;
    }

    /* ── Any tool (Sx mode): drag existing notes/link-summary/legend if hit ── */
    if (app->current_mode == APP_MODE_SUBJECTIVE) {
        double bx, by;
        screen_to_body(cd, x, y, &bx, &by);
        if (link_summary_hit_screen(app, cd, x, y)) {
            app->link_drag_active = TRUE;
            app->link_drag_bx_off = app->link_summary_bx - bx;
            app->link_drag_by_off = app->link_summary_by - by;
            return;
        }
        int hit = note_hit_screen(app, cd, x, y);
        if (hit >= 0) {
            double lbx, lby;
            label_anchor_resolve(&app->notes[hit], &lbx, &lby);
            app->note_drag_idx    = hit;
            app->note_drag_bx_off = lbx - bx;
            app->note_drag_by_off = lby - by;
            return;
        }
    }

    /* ── Note tool: no existing annotation hit → open wizard ── */
    if (app->tool == TOOL_NOTE) {
        double bx, by;
        screen_to_body(cd, x, y, &bx, &by);
        if (app->show_note_wizard_cb)
            app->show_note_wizard_cb(app, (int)cd->view, bx, by);
        return;
    }

    /* ── Arrow tool: delete head tap, or begin new arrow ── */
    if (app->tool == TOOL_ARROW) {
        int hit = arrow_head_hit_screen(app, cd, x, y);
        if (hit >= 0) {
            for (int k = hit; k < app->arrow_count - 1; k++)
                app->arrows[k] = app->arrows[k + 1];
            app->arrow_count--;
            if (app->undo_type_top > 0 &&
                app->undo_type_stack[app->undo_type_top - 1] == 1)
                app->undo_type_top--;
            app->stroke_version++;  /* arrow deleted — invalidate cache */
            gtk_widget_queue_draw(cd->da);
            return;
        }
        double bx, by;
        screen_to_body(cd, x, y, &bx, &by);
        app->current_view      = cd->view;
        app->arrow_drawing     = TRUE;
        app->arrow_draw_view   = (int)cd->view;
        app->arrow_x1 = app->arrow_x2 = bx;
        app->arrow_y1 = app->arrow_y2 = by;
        app->arrow_track_n     = 0;
        arrow_track_add(app, bx, by);
        gtk_widget_queue_draw(cd->da);
        return;
    }

    /* ── Physical eraser tip ── */
    if (ev) {
        GdkDeviceTool *t = gdk_event_get_device_tool(ev);
        if (t && gdk_device_tool_get_tool_type(t) == GDK_DEVICE_TOOL_TYPE_ERASER)
            app->tool = TOOL_ERASE;
    }

    /* ── Objective mode: intercept all drawing/erase here ── */
    if (app->current_mode == APP_MODE_OBJECTIVE) {
        double bx, by;
        screen_to_body(cd, x, y, &bx, &by);
        app->current_view = cd->view;
        if (app->tool == TOOL_ERASE) {
            obj_handle_erase(app, (int)cd->view, bx, by, cd->da);
            return;
        }
        if (app->obj_point_mode) {
            /* Drag existing point if tapped, otherwise place new */
            int phit = obj_point_hit_screen(app, cd, x, y);
            if (phit >= 0) {
                app->obj_point_drag_idx    = phit;
                app->obj_point_drag_bx_off = app->obj_points[phit].bx - bx;
                app->obj_point_drag_by_off = app->obj_points[phit].by - by;
                return;
            }
            if (app->show_ppt_entry_cb)
                app->show_ppt_entry_cb(app, (int)cd->view, bx, by);
            return;
        }
        if (app->obj_active_zone) {
            obj_zone_free(app->obj_active_zone);
            app->obj_active_zone = NULL;
        }
        app->obj_active_zone = obj_zone_new(app->obj_zone_type, (int)cd->view);
        obj_zone_add_pt(app->obj_active_zone, (float)bx, (float)by);
        gtk_widget_queue_draw(cd->da);
        return;
    }

    /* ── Erase tool: also deletes arrow heads on tap ── */
    if (app->tool == TOOL_ERASE) {
        int hit = arrow_head_hit_screen(app, cd, x, y);
        if (hit >= 0) {
            for (int k = hit; k < app->arrow_count - 1; k++)
                app->arrows[k] = app->arrows[k + 1];
            app->arrow_count--;
            if (app->undo_type_top > 0 &&
                app->undo_type_stack[app->undo_type_top - 1] == 1)
                app->undo_type_top--;
            app->stroke_version++;  /* arrow deleted — invalidate cache */
            gtk_widget_queue_draw(cd->da);
            return;
        }
    }

    double bx, by;
    screen_to_body(cd, x, y, &bx, &by);
    input_begin(app, bx, by, stylus_effective_pressure(gs, app));
    gtk_widget_queue_draw(cd->da);
}

static void on_stylus_motion(GtkGestureStylus *gs, double x, double y,
                              gpointer d)
{
    ColData  *cd  = d;
    AppState *app = cd->app;
    app->last_stylus_us = g_get_monotonic_time();

    /* Note label drag / link drag (any tool) */
    if (app->note_drag_idx >= 0) {
        double bx, by;
        screen_to_body(cd, x, y, &bx, &by);
        NoteAnnotation *na = &app->notes[app->note_drag_idx];
        na->label.lx     = bx + app->note_drag_bx_off;
        na->label.ly     = by + app->note_drag_by_off;
        na->label.placed = 1;
        gtk_widget_queue_draw(cd->da);
        return;
    }
    if (app->link_drag_active) {
        double bx, by;
        screen_to_body(cd, x, y, &bx, &by);
        app->link_summary_bx   = bx + app->link_drag_bx_off;
        app->link_summary_by   = by + app->link_drag_by_off;
        app->link_summary_view = (int)cd->view;
        canvas_invalidate(app);
        return;
    }
    if (app->tool == TOOL_NOTE) return;

    /* Obj point drag */
    if (app->obj_point_drag_idx >= 0) {
        double bx, by;
        screen_to_body(cd, x, y, &bx, &by);
        app->obj_points[app->obj_point_drag_idx].bx = bx + app->obj_point_drag_bx_off;
        app->obj_points[app->obj_point_drag_idx].by = by + app->obj_point_drag_by_off;
        gtk_widget_queue_draw(cd->da);
        return;
    }

    if (app->tool == TOOL_ARROW && app->arrow_drawing) {
        double bx, by;
        screen_to_body(cd, x, y, &bx, &by);
        app->arrow_x2 = bx;
        app->arrow_y2 = by;
        arrow_track_add(app, bx, by);
        gtk_widget_queue_draw(cd->da);
        return;
    }

    if (app->current_mode == APP_MODE_OBJECTIVE && app->obj_active_zone) {
        double bx, by;
        screen_to_body(cd, x, y, &bx, &by);
        obj_zone_add_pt(app->obj_active_zone, (float)bx, (float)by);
        gtk_widget_queue_draw(cd->da);
        return;
    }

    double bx, by;
    screen_to_body(cd, x, y, &bx, &by);
    input_motion(app, bx, by, stylus_effective_pressure(gs, app));
    gtk_widget_queue_draw(cd->da);
}

static void on_stylus_up(GtkGestureStylus *gs, double x, double y,
                          gpointer d)
{
    ColData  *cd  = d;
    AppState *app = cd->app;
    (void)gs; (void)x; (void)y;
    app->last_stylus_us = g_get_monotonic_time();

    /* Clear note/link drag (any tool) */
    if (app->note_drag_idx >= 0 || app->link_drag_active) {
        app->note_drag_idx      = -1;
        app->link_drag_active   = FALSE;
        gtk_widget_queue_draw(cd->da);
        return;
    }
    if (app->tool == TOOL_NOTE) {
        gtk_widget_queue_draw(cd->da);
        return;
    }

    /* Clear obj point drag */
    if (app->obj_point_drag_idx >= 0) {
        app->obj_point_drag_idx = -1;
        gtk_widget_queue_draw(cd->da);
        return;
    }

    if (app->tool == TOOL_ARROW && app->arrow_drawing) {
        double bx, by;
        screen_to_body(cd, x, y, &bx, &by);
        app->arrow_x2 = bx; app->arrow_y2 = by;
        double adx = bx - app->arrow_x1, ady = by - app->arrow_y1;
        if (app->arrow_count < MAX_ARROWS &&
            sqrt(adx*adx + ady*ady) >= 2.0) {
            double cpx, cpy;
            arrow_get_cp(app, &cpx, &cpy);
            app->arrows[app->arrow_count] = (ArrowAnnotation){
                .view = app->arrow_draw_view,
                .x1 = app->arrow_x1, .y1 = app->arrow_y1,
                .cx = cpx, .cy = cpy,
                .x2 = bx,  .y2 = by
            };
            if (app->undo_type_top < 64)
                app->undo_type_stack[app->undo_type_top++] = 1;
            app->arrow_count++;
            app->stroke_version++;  /* arrow committed — invalidate cache */
        }
        app->arrow_drawing = FALSE;
        app->arrow_track_n = 0;
        gtk_widget_queue_draw(cd->da);
        return;
    }

    if (app->current_mode == APP_MODE_OBJECTIVE) {
        obj_commit_active_zone(app, cd->da);
        return;
    }

    input_end(app);
    gtk_widget_queue_draw(cd->da);
}

/* ── Drag gestures ───────────────────────────────────────────────────────── */
static void on_drag_begin(GtkGestureDrag *gd, double x, double y, gpointer d)
{
    ColData  *cd  = d;
    AppState *app = cd->app;
    (void)gd;

    /* Any tool (Sx mode): drag existing note/link-summary if hit */
    if (app->current_mode == APP_MODE_SUBJECTIVE) {
        double bx_hit, by_hit;
        screen_to_body(cd, x, y, &bx_hit, &by_hit);
        if (link_summary_hit_screen(app, cd, x, y)) {
            app->link_drag_active = TRUE;
            app->link_drag_bx_off = app->link_summary_bx - bx_hit;
            app->link_drag_by_off = app->link_summary_by - by_hit;
            return;
        }
        int hit = note_hit_screen(app, cd, x, y);
        if (hit >= 0) {
            double lbx, lby;
            label_anchor_resolve(&app->notes[hit], &lbx, &lby);
            app->note_drag_idx    = hit;
            app->note_drag_bx_off = lbx - bx_hit;
            app->note_drag_by_off = lby - by_hit;
            return;
        }
    }

    /* Note tool (no existing hit): open wizard via palm-rejection rules */
    if (app->tool == TOOL_NOTE) {
        double bx, by;
        screen_to_body(cd, x, y, &bx, &by);
        if (app->show_note_wizard_cb) {
            if (app->pen_palm_reject) {
                gint64 age_us = g_get_monotonic_time() - app->last_stylus_us;
                if (age_us >= 500000)
                    app->show_note_wizard_cb(app, (int)cd->view, bx, by);
            } else {
                app->show_note_wizard_cb(app, (int)cd->view, bx, by);
            }
        }
        return;
    }

    /* Arrow head deletion — allowed even during palm-rejection window */
    if (app->tool == TOOL_ARROW || app->tool == TOOL_ERASE) {
        int hit = arrow_head_hit_screen(app, cd, x, y);
        if (hit >= 0) {
            for (int k = hit; k < app->arrow_count - 1; k++)
                app->arrows[k] = app->arrows[k + 1];
            app->arrow_count--;
            if (app->undo_type_top > 0 &&
                app->undo_type_stack[app->undo_type_top - 1] == 1)
                app->undo_type_top--;
            app->stroke_version++;  /* arrow deleted — invalidate cache */
            gtk_widget_queue_draw(cd->da);
            return;
        }
    }

    /* Palm rejection for drawing tools */
    if (app->pen_palm_reject) {
        gint64 age_us = g_get_monotonic_time() - app->last_stylus_us;
        if (age_us < 500000) return;
    }

    app->current_view = cd->view;
    double bx, by;
    screen_to_body(cd, x, y, &bx, &by);

    /* Arrow tool: begin new arrow */
    if (app->tool == TOOL_ARROW) {
        app->arrow_drawing     = TRUE;
        app->arrow_draw_view   = (int)cd->view;
        app->arrow_x1 = app->arrow_x2 = bx;
        app->arrow_y1 = app->arrow_y2 = by;
        app->arrow_track_n     = 0;
        arrow_track_add(app, bx, by);
        gtk_widget_queue_draw(cd->da);
        return;
    }

    if (app->current_mode == APP_MODE_OBJECTIVE) {
        if (app->tool == TOOL_ERASE) {
            obj_handle_erase(app, (int)cd->view, bx, by, cd->da);
            return;
        }
        if (app->obj_point_mode) {
            int phit = obj_point_hit_screen(app, cd, x, y);
            if (phit >= 0) {
                app->obj_point_drag_idx    = phit;
                app->obj_point_drag_bx_off = app->obj_points[phit].bx - bx;
                app->obj_point_drag_by_off = app->obj_points[phit].by - by;
                return;
            }
            if (app->show_ppt_entry_cb)
                app->show_ppt_entry_cb(app, (int)cd->view, bx, by);
            return;
        }
        if (app->obj_active_zone) {
            obj_zone_free(app->obj_active_zone);
            app->obj_active_zone = NULL;
        }
        app->obj_active_zone = obj_zone_new(app->obj_zone_type, (int)cd->view);
        obj_zone_add_pt(app->obj_active_zone, (float)bx, (float)by);
        gtk_widget_queue_draw(cd->da);
        return;
    }

    input_begin(app, bx, by, 0.6);
    gtk_widget_queue_draw(cd->da);
}

static void on_drag_update(GtkGestureDrag *gd, double dx, double dy,
                            gpointer d)
{
    ColData  *cd  = d;
    AppState *app = cd->app;
    double sx, sy;
    gtk_gesture_drag_get_start_point(gd, &sx, &sy);
    double bx, by;
    screen_to_body(cd, sx + dx, sy + dy, &bx, &by);

    /* Note label drag / link drag (any tool) */
    if (app->note_drag_idx >= 0) {
        NoteAnnotation *na = &app->notes[app->note_drag_idx];
        na->label.lx     = bx + app->note_drag_bx_off;
        na->label.ly     = by + app->note_drag_by_off;
        na->label.placed = 1;
        gtk_widget_queue_draw(cd->da);
        return;
    }
    if (app->link_drag_active) {
        app->link_summary_bx   = bx + app->link_drag_bx_off;
        app->link_summary_by   = by + app->link_drag_by_off;
        app->link_summary_view = (int)cd->view;
        canvas_invalidate(app);
        return;
    }
    if (app->tool == TOOL_NOTE) return;

    /* Obj point drag */
    if (app->obj_point_drag_idx >= 0) {
        app->obj_points[app->obj_point_drag_idx].bx = bx + app->obj_point_drag_bx_off;
        app->obj_points[app->obj_point_drag_idx].by = by + app->obj_point_drag_by_off;
        gtk_widget_queue_draw(cd->da);
        return;
    }

    if (app->tool == TOOL_ARROW && app->arrow_drawing) {
        app->arrow_x2 = bx;
        app->arrow_y2 = by;
        arrow_track_add(app, bx, by);
        gtk_widget_queue_draw(cd->da);
        return;
    }

    if (app->current_mode == APP_MODE_OBJECTIVE && app->obj_active_zone) {
        obj_zone_add_pt(app->obj_active_zone, (float)bx, (float)by);
        gtk_widget_queue_draw(cd->da);
        return;
    }

    input_motion(app, bx, by, 0.6);
    gtk_widget_queue_draw(cd->da);
}

static void on_drag_end(GtkGestureDrag *gd, double dx, double dy, gpointer d)
{
    ColData  *cd  = d;
    AppState *app = cd->app;

    /* Clear note/link drag (any tool) */
    if (app->note_drag_idx >= 0 || app->link_drag_active) {
        app->note_drag_idx      = -1;
        app->link_drag_active   = FALSE;
        gtk_widget_queue_draw(cd->da);
        return;
    }
    if (app->tool == TOOL_NOTE) {
        gtk_widget_queue_draw(cd->da);
        return;
    }

    /* Clear obj point drag */
    if (app->obj_point_drag_idx >= 0) {
        app->obj_point_drag_idx = -1;
        gtk_widget_queue_draw(cd->da);
        return;
    }

    if (app->tool == TOOL_ARROW && app->arrow_drawing) {
        double sx, sy;
        gtk_gesture_drag_get_start_point(gd, &sx, &sy);
        double bx, by;
        screen_to_body(cd, sx + dx, sy + dy, &bx, &by);
        app->arrow_x2 = bx; app->arrow_y2 = by;
        double adx = bx - app->arrow_x1, ady = by - app->arrow_y1;
        if (app->arrow_count < MAX_ARROWS &&
            sqrt(adx*adx + ady*ady) >= 2.0) {
            double cpx, cpy;
            arrow_get_cp(app, &cpx, &cpy);
            app->arrows[app->arrow_count] = (ArrowAnnotation){
                .view = app->arrow_draw_view,
                .x1 = app->arrow_x1, .y1 = app->arrow_y1,
                .cx = cpx, .cy = cpy,
                .x2 = bx,  .y2 = by
            };
            if (app->undo_type_top < 64)
                app->undo_type_stack[app->undo_type_top++] = 1;
            app->arrow_count++;
            app->stroke_version++;  /* arrow committed — invalidate cache */
        }
        app->arrow_drawing = FALSE;
        app->arrow_track_n = 0;
        gtk_widget_queue_draw(cd->da);
        return;
    }

    if (app->current_mode == APP_MODE_OBJECTIVE) {
        obj_commit_active_zone(app, cd->da);
        return;
    }

    input_end(app);
    gtk_widget_queue_draw(cd->da);
}

/* ── Zoom reset ──────────────────────────────────────────────────────────── */
static void on_reset_zoom(GtkButton *btn, gpointer d)
{
    ColData *cd = d;
    (void)btn;
    *cd->p_zoom  = 1.0;
    *cd->p_pan_x = 0.0;
    *cd->p_pan_y = 0.0;
    gtk_button_set_label(GTK_BUTTON(cd->zoom_btn), "1×");
    gtk_widget_queue_draw(cd->da);
}

/* ── Pinch-to-zoom + two-finger pan ─────────────────────────────────────── */
static void on_zoom_begin(GtkGestureZoom *gz, GdkEventSequence *seq,
                           gpointer d)
{
    (void)seq;
    ColData *cd = d;
    cd->last_zoom_scale = 1.0;
    gtk_gesture_get_bounding_box_center(GTK_GESTURE(gz),
                                         &cd->last_cx, &cd->last_cy);
    input_cancel(cd->app);
    cd->app->note_drag_idx      = -1;
    cd->app->link_drag_active   = FALSE;
    cd->app->obj_point_drag_idx = -1;
    gtk_widget_queue_draw(cd->da);
}

static void on_zoom_changed(GtkGestureZoom *gz, gdouble scale, gpointer d)
{
    ColData  *cd  = d;

    double delta = scale / cd->last_zoom_scale;
    cd->last_zoom_scale = scale;

    double fx, fy;
    gtk_gesture_get_bounding_box_center(GTK_GESTURE(gz), &fx, &fy);

    /* Two-finger pan: translate by centroid movement */
    double pan_dx = fx - cd->last_cx;
    double pan_dy = fy - cd->last_cy;
    cd->last_cx = fx;
    cd->last_cy = fy;

    double w     = (double)gtk_widget_get_width(cd->da);
    double h     = (double)gtk_widget_get_height(cd->da);
    double old_z = *cd->p_zoom;
    double new_z = CLAMP(old_z * delta, 0.2, 20.0);

    /* Keep focal body-point under centroid, then apply pan */
    double cx = w / 2.0 + (*cd->p_pan_x);
    double cy = h / 2.0 + (*cd->p_pan_y);
    *cd->p_pan_x = fx + (new_z / old_z) * (cx - fx) - w / 2.0 + pan_dx;
    *cd->p_pan_y = fy + (new_z / old_z) * (cy - fy) - h / 2.0 + pan_dy;
    *cd->p_zoom  = new_z;

    if (cd->zoom_btn) {
        char buf[10];
        snprintf(buf, sizeof(buf), "%.1f×", new_z);
        gtk_button_set_label(GTK_BUTTON(cd->zoom_btn), buf);
    }

    gtk_widget_queue_draw(cd->da);
}

/* ── Raw event fallback for stylus barrel button (Lenovo ThinkPad pen) ───── *
 * GtkGestureStylus only sees button=1. The barrel fires GDK_BUTTON_PRESS     *
 * with button≥2 which gestures ignore. Catch it here at capture phase.       */
static gboolean on_raw_event(GtkEventControllerLegacy *ctrl,
                              GdkEvent *event, gpointer d)
{
    (void)ctrl;
    if (!GDK_IS_EVENT_TYPE(event, GDK_BUTTON_PRESS)) return FALSE;

    guint btn = gdk_button_event_get_button(event);
    if (btn < 2) return FALSE;

    GdkDeviceTool *tool = gdk_event_get_device_tool(event);
    if (!tool) return FALSE;
    GdkDeviceToolType type = gdk_device_tool_get_tool_type(tool);
    if (type != GDK_DEVICE_TOOL_TYPE_PEN &&
        type != GDK_DEVICE_TOOL_TYPE_ERASER) return FALSE;

    ColData  *cd  = d;
    AppState *app = cd->app;
    input_cancel(app);

    double x, y;
    gdk_event_get_position(event, &x, &y);
    double bx, by;
    screen_to_body(cd, x, y, &bx, &by);

    app->symptom = (SymptomType)((app->symptom + 1) % SYMPTOM_COUNT);
    app->tool    = TOOL_DRAW;
    if (app->toolbar_update_cb) app->toolbar_update_cb(app);
    gtk_widget_queue_draw(cd->da);
    return TRUE;
}

/* ── Mouse motion tracker (feeds scroll-zoom focal point) ────────────────── */
static void on_mouse_motion(GtkEventControllerMotion *ctrl,
                             double x, double y, gpointer d)
{
    (void)ctrl;
    ColData *cd = d;
    cd->mouse_x = x;
    cd->mouse_y = y;
}

/* ── Scroll-wheel zoom ───────────────────────────────────────────────────── */
static gboolean on_scroll(GtkEventControllerScroll *ctrl,
                           double dx, double dy, gpointer d)
{
    (void)ctrl; (void)dx;
    ColData *cd = d;

    double w = (double)gtk_widget_get_width(cd->da);
    double h = (double)gtk_widget_get_height(cd->da);
    if (w <= 0.0 || h <= 0.0) return FALSE;

    double mx = cd->mouse_x;
    double my = cd->mouse_y;

    double factor = (dy < 0) ? 1.12 : (1.0 / 1.12);
    double old_z = *cd->p_zoom;
    double new_z = CLAMP(old_z * factor, 0.2, 20.0);

    double cx = w / 2.0 + (*cd->p_pan_x);
    double cy = h / 2.0 + (*cd->p_pan_y);
    *cd->p_pan_x = mx + (new_z / old_z) * (cx - mx) - w / 2.0;
    *cd->p_pan_y = my + (new_z / old_z) * (cy - my) - h / 2.0;
    *cd->p_zoom  = new_z;

    if (cd->zoom_btn) {
        char buf[10];
        snprintf(buf, sizeof(buf), "%.1f\xc3\x97", new_z);
        gtk_button_set_label(GTK_BUTTON(cd->zoom_btn), buf);
    }
    gtk_widget_queue_draw(cd->da);
    return TRUE;
}

/* ── Middle-button pan ───────────────────────────────────────────────────── */
static void on_mid_drag_begin(GtkGestureDrag *gd, double x, double y, gpointer d)
{
    (void)gd; (void)x; (void)y;
    ColData *cd = d;
    input_cancel(cd->app);
    cd->mid_pan_x0 = *cd->p_pan_x;
    cd->mid_pan_y0 = *cd->p_pan_y;
}

static void on_mid_drag_update(GtkGestureDrag *gd, double dx, double dy, gpointer d)
{
    (void)gd;
    ColData *cd = d;
    *cd->p_pan_x = cd->mid_pan_x0 + dx;
    *cd->p_pan_y = cd->mid_pan_y0 + dy;
    gtk_widget_queue_draw(cd->da);
}

/* ── Build one drawing area with header + all gesture controllers ────────── */
static GtkWidget *make_drawing_area(AppState *app, ColData *cd,
                                     const char *label)
{
    GtkWidget *vbox = gtk_box_new(GTK_ORIENTATION_VERTICAL, 0);
    gtk_widget_set_hexpand(vbox, TRUE);
    gtk_widget_set_vexpand(vbox, TRUE);

    /* Header bar */
    GtkWidget *hdr = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 4);
    gtk_widget_set_name(hdr, "col-header");

    GtkWidget *lbl = gtk_label_new(label);
    gtk_widget_set_hexpand(lbl, TRUE);
    gtk_label_set_xalign(GTK_LABEL(lbl), 0.0);
    gtk_widget_set_margin_start(lbl, 6);
    cd->header_label = lbl;
    gtk_box_append(GTK_BOX(hdr), lbl);

    GtkWidget *zbtn = gtk_button_new_with_label("1×");
    gtk_widget_set_name(zbtn, "zoom-btn");
    gtk_widget_set_size_request(zbtn, 44, 26);
    gtk_widget_set_margin_end(zbtn, 4);
    gtk_widget_set_margin_top(zbtn, 2);
    gtk_widget_set_margin_bottom(zbtn, 2);
    cd->zoom_btn = zbtn;
    g_signal_connect(zbtn, "clicked", G_CALLBACK(on_reset_zoom), cd);
    gtk_box_append(GTK_BOX(hdr), zbtn);
    gtk_box_append(GTK_BOX(vbox), hdr);

    /* Drawing area */
    GtkWidget *da = gtk_drawing_area_new();
    cd->da = da;
    gtk_drawing_area_set_draw_func(GTK_DRAWING_AREA(da), on_col_draw, cd, NULL);
    gtk_widget_set_hexpand(da, TRUE);
    gtk_widget_set_vexpand(da, TRUE);

    /* Stylus */
    GtkGesture *stylus = gtk_gesture_stylus_new();
    gtk_widget_add_controller(da, GTK_EVENT_CONTROLLER(stylus));
    g_signal_connect(stylus, "down",   G_CALLBACK(on_stylus_down),   cd);
    g_signal_connect(stylus, "motion", G_CALLBACK(on_stylus_motion), cd);
    g_signal_connect(stylus, "up",     G_CALLBACK(on_stylus_up),     cd);

    /* Drag (mouse / single touch) */
    GtkGesture *drag = gtk_gesture_drag_new();
    gtk_gesture_single_set_touch_only(GTK_GESTURE_SINGLE(drag), FALSE);
    gtk_widget_add_controller(da, GTK_EVENT_CONTROLLER(drag));
    g_signal_connect(drag, "drag-begin",  G_CALLBACK(on_drag_begin),  cd);
    g_signal_connect(drag, "drag-update", G_CALLBACK(on_drag_update), cd);
    g_signal_connect(drag, "drag-end",    G_CALLBACK(on_drag_end),    cd);

    /* Pinch-zoom (also drives two-finger pan) */
    GtkGesture *zoom = gtk_gesture_zoom_new();
    gtk_widget_add_controller(da, GTK_EVENT_CONTROLLER(zoom));
    g_signal_connect(zoom, "begin",         G_CALLBACK(on_zoom_begin),   cd);
    g_signal_connect(zoom, "scale-changed", G_CALLBACK(on_zoom_changed), cd);

    /* All input types (stylus, mouse, touch) work independently.
     * Do NOT group or make exclusive — let all gesture recognizers work in parallel. */

    /* Scroll-wheel zoom */
    GtkEventController *scroll = gtk_event_controller_scroll_new(
        GTK_EVENT_CONTROLLER_SCROLL_VERTICAL);
    gtk_widget_add_controller(da, scroll);
    g_signal_connect(scroll, "scroll", G_CALLBACK(on_scroll), cd);

    /* Mouse motion — keeps cd->mouse_x/y current for scroll zoom focal point */
    GtkEventController *motion = gtk_event_controller_motion_new();
    gtk_widget_add_controller(da, motion);
    g_signal_connect(motion, "motion", G_CALLBACK(on_mouse_motion), cd);

    /* Middle-button pan */
    GtkGesture *mid = gtk_gesture_drag_new();
    gtk_gesture_single_set_button(GTK_GESTURE_SINGLE(mid), 2);
    gtk_widget_add_controller(da, GTK_EVENT_CONTROLLER(mid));
    g_signal_connect(mid, "drag-begin",  G_CALLBACK(on_mid_drag_begin),  cd);
    g_signal_connect(mid, "drag-update", G_CALLBACK(on_mid_drag_update), cd);

    /* Raw event capture for barrel button on pens that bypass GtkGestureStylus */
    GtkEventController *raw = gtk_event_controller_legacy_new();
    gtk_event_controller_set_propagation_phase(raw, GTK_PHASE_CAPTURE);
    gtk_widget_add_controller(da, raw);
    g_signal_connect(raw, "event", G_CALLBACK(on_raw_event), cd);

    gtk_box_append(GTK_BOX(vbox), da);

    (void)app;
    return vbox;
}

/* ── Public API ──────────────────────────────────────────────────────────── */

GtkWidget *canvas_new(AppState *app)
{
    app->note_drag_idx        = -1;
    app->link_drag_active     = FALSE;
    app->obj_point_drag_idx   = -1;

    /* Initialise right slot views (can be overridden by settings before canvas_new) */
    if (app->right_slot_views[0] == 0 && app->right_slot_views[1] == 0) {
        app->right_slot_views[0] = VIEW_LATERAL_L;
        app->right_slot_views[1] = VIEW_LATERAL_R;
    }

    /* Initialise zoom/pan state */
    for (int i = 0; i < 4; i++) {
        app->col_zoom[i]    = app->single_zoom[i]    = 1.0;
        app->col_pan_x[i]   = app->single_pan_x[i]   = 0.0;
        app->col_pan_y[i]   = app->single_pan_y[i]   = 0.0;
        app->col_da[i]      = app->single_da[i]       = NULL;
    }

    /* Initialise ColData for quad slots (0-3) and single slots (4-7).
     * Free any existing cache surfaces in case canvas_new is called again. */
    for (int i = 0; i < 8; i++) {
        if (g_col[i].stroke_cache) {
            cairo_surface_destroy(g_col[i].stroke_cache);
            g_col[i].stroke_cache = NULL;
        }
    }
    for (int i = 0; i < 4; i++) {
        /* Quad right slots (2,3) use cyclable views; left slots and all singles are fixed */
        BodyView qview = (i < 2) ? SINGLE_SLOT_VIEWS[i] : app->right_slot_views[i - 2];
        g_col[i]   = (ColData){ .app = app, .view = qview,
                                 .p_zoom  = &app->col_zoom[i],
                                 .p_pan_x = &app->col_pan_x[i],
                                 .p_pan_y = &app->col_pan_y[i],
                                 .last_zoom_scale = 1.0,
                                 .stroke_cache = NULL,
                                 .cache_stroke_version = -1 };
        g_col[4+i] = (ColData){ .app = app, .view = SINGLE_SLOT_VIEWS[i],
                                 .p_zoom  = &app->single_zoom[i],
                                 .p_pan_x = &app->single_pan_x[i],
                                 .p_pan_y = &app->single_pan_y[i],
                                 .last_zoom_scale = 1.0,
                                 .stroke_cache = NULL,
                                 .cache_stroke_version = -1 };
    }

    /* GtkStack: one page per layout mode */
    GtkWidget *stack = gtk_stack_new();
    gtk_stack_set_transition_type(GTK_STACK(stack), GTK_STACK_TRANSITION_TYPE_NONE);
    gtk_widget_set_hexpand(stack, TRUE);
    gtk_widget_set_vexpand(stack, TRUE);

    /* ── Quad layout ── *
     * GtkGrid with 5 homogeneous columns × 2 homogeneous rows:            *
     *   cols 0-1 = anterior  (2 cols wide, full height)                   *
     *   cols 2-3 = posterior (2 cols wide, full height)                   *
     *   col  4, row 0 = lateral_l  (1 col wide, half height)              *
     *   col  4, row 1 = lateral_r  (1 col wide, half height)              *
     * Column homogeneity → 2:2:1 width ratio automatically.               */
    GtkWidget *grid = gtk_grid_new();
    gtk_grid_set_column_homogeneous(GTK_GRID(grid), TRUE);
    gtk_grid_set_row_homogeneous(GTK_GRID(grid), TRUE);
    gtk_widget_set_hexpand(grid, TRUE);
    gtk_widget_set_vexpand(grid, TRUE);

    GtkWidget *w;

    w = make_drawing_area(app, &g_col[0], "Anterior");
    app->col_da[0] = g_col[0].da;
    gtk_grid_attach(GTK_GRID(grid), w, 0, 0, 2, 2);

    w = make_drawing_area(app, &g_col[1], "Posterior");
    app->col_da[1] = g_col[1].da;
    gtk_grid_attach(GTK_GRID(grid), w, 2, 0, 2, 2);

    w = make_drawing_area(app, &g_col[2], "Left lateral");
    app->col_da[2] = g_col[2].da;
    gtk_grid_attach(GTK_GRID(grid), w, 4, 0, 1, 1);

    w = make_drawing_area(app, &g_col[3], "Right lateral");
    app->col_da[3] = g_col[3].da;
    gtk_grid_attach(GTK_GRID(grid), w, 4, 1, 1, 1);

    gtk_stack_add_named(GTK_STACK(stack), grid, "quad");

    /* ── Single-view pages ── */
    static const char *sv_labels[] = {
        "Anterior", "Posterior", "Left lateral", "Right lateral"
    };
    static const char *sv_names[] = {
        "anterior", "posterior", "lateral_l", "lateral_r"
    };
    for (int i = 0; i < 4; i++) {
        w = make_drawing_area(app, &g_col[4 + i], sv_labels[i]);
        app->single_da[i] = g_col[4 + i].da;
        gtk_stack_add_named(GTK_STACK(stack), w, sv_names[i]);
    }

    gtk_stack_set_visible_child_name(GTK_STACK(stack), "quad");
    app->layout_mode  = LAYOUT_QUAD;
    app->current_view = VIEW_ANTERIOR;
    app->canvas       = stack;

    return stack;
}

void canvas_set_layout(AppState *app, LayoutMode mode)
{
    static const char *names[] = {
        "quad", "anterior", "posterior", "lateral_l", "lateral_r"
    };
    static const BodyView sv[] = {
        VIEW_ANTERIOR,  /* LAYOUT_QUAD — not used for current_view */
        VIEW_ANTERIOR,
        VIEW_POSTERIOR,
        VIEW_LATERAL_L,
        VIEW_LATERAL_R,
    };

    app->layout_mode = mode;
    if (mode != LAYOUT_QUAD)
        app->current_view = sv[mode];

    gtk_stack_set_visible_child_name(GTK_STACK(app->canvas), names[mode]);
}

void canvas_invalidate(AppState *app)
{
    for (int i = 0; i < 4; i++) {
        if (app->col_da[i])    gtk_widget_queue_draw(app->col_da[i]);
        if (app->single_da[i]) gtk_widget_queue_draw(app->single_da[i]);
    }
}

void canvas_clear(AppState *app)
{
    stroke_list_clear(app->strokes);
    app->note_count          = 0;
    app->note_drag_idx       = -1;
    app->link_summary_active = FALSE;
    app->link_rel_count      = 0;
    app->arrow_count         = 0;
    app->arrow_drawing       = FALSE;
    app->undo_type_top       = 0;
    app->stroke_version++;

    for (int i = 0; i < app->obj_zone_count; i++) {
        obj_zone_free(app->obj_zones[i]);
        app->obj_zones[i] = NULL;
    }
    app->obj_zone_count = 0;
    app->obj_point_count = 0;
    app->obj_undo_type_top = 0;
    if (app->obj_active_zone) {
        obj_zone_free(app->obj_active_zone);
        app->obj_active_zone = NULL;
    }

    canvas_invalidate(app);
}

void canvas_undo(AppState *app)
{
    if (app->current_mode == APP_MODE_OBJECTIVE) {
        if (app->obj_undo_type_top > 0) {
            guint8 type = app->obj_undo_type_stack[--app->obj_undo_type_top];
            if (type == 1) {
                if (app->obj_point_count > 0) app->obj_point_count--;
            } else {
                if (app->obj_zone_count > 0) {
                    obj_zone_free(app->obj_zones[--app->obj_zone_count]);
                    app->obj_zones[app->obj_zone_count] = NULL;
                }
            }
        }
        canvas_invalidate(app);
        return;
    }
    if (app->undo_type_top > 0) {
        guint8 type = app->undo_type_stack[--app->undo_type_top];
        if (type == 1) {
            if (app->arrow_count > 0) app->arrow_count--;
        } else {
            stroke_free(stroke_list_pop(app->strokes));
        }
    } else {
        stroke_free(stroke_list_pop(app->strokes));
    }
    app->stroke_version++;
    canvas_invalidate(app);
}

/* ── View name helpers ───────────────────────────────────────────────────── */
const char *canvas_view_name(BodyView v)
{
    static const char *names[] = {
        "Anterior", "Posterior", "Left lateral", "Right lateral"
    };
    return (unsigned)v < 4 ? names[v] : "?";
}

const char *canvas_view_short_name(BodyView v)
{
    static const char *names[] = { "Ant", "Post", "L lat", "R lat" };
    return (unsigned)v < 4 ? names[v] : "?";
}

/* ── Right column slot cycling ───────────────────────────────────────────── */
void canvas_cycle_right_slot(AppState *app, int slot)
{
    BodyView nv = (BodyView)((app->right_slot_views[slot] + 1) % 4);
    app->right_slot_views[slot] = nv;
    int ci = 2 + slot;
    g_col[ci].view = nv;
    if (g_col[ci].header_label)
        gtk_label_set_text(GTK_LABEL(g_col[ci].header_label),
                           canvas_view_name(nv));
    gtk_widget_queue_draw(g_col[ci].da);
}

void canvas_reset_all_zoom(AppState *app)
{
    for (int i = 0; i < 8; i++) {
        *g_col[i].p_zoom  = 1.0;
        *g_col[i].p_pan_x = 0.0;
        *g_col[i].p_pan_y = 0.0;
        if (g_col[i].zoom_btn)
            gtk_button_set_label(GTK_BUTTON(g_col[i].zoom_btn), "1\xc3\x97");
    }
    canvas_invalidate(app);
}

void canvas_screen_to_body(AppState *app, double sx, double sy,
                            double *bx, double *by)
{
    int base = (app->layout_mode == LAYOUT_QUAD) ? 0 : 4;
    for (int i = base; i < base + 4; i++) {
        if (g_col[i].view == app->current_view && g_col[i].da) {
            screen_to_body(&g_col[i], sx, sy, bx, by);
            return;
        }
    }
    *bx = sx;
    *by = sy;
}
