#include "overlays.h"
#include "body_outlines.h"
#include <stdlib.h>
#include <string.h>
#include <math.h>

/* ── SVG-subset path parser ─────────────────────────────────────────────── *
 * Supports: M, L, C, Q, Z (absolute only — enough for our hand-authored paths)
 * ─────────────────────────────────────────────────────────────────────────── */
static const char *skip_ws(const char *p) {
    while (*p == ' ' || *p == ',' || *p == '\t' || *p == '\n') p++;
    return p;
}

static const char *read_float(const char *p, float *out) {
    char *end;
    *out = strtof(p, &end);
    return end;
}

static void cairo_path_from_svg(cairo_t *cr, const char *d)
{
    if (!d || !*d) return;
    const char *p = d;
    float x, y, x1, y1, x2, y2;
    char cmd = 0;

    while (*p) {
        p = skip_ws(p);
        if (!*p) break;
        if ((*p >= 'A' && *p <= 'Z') || (*p >= 'a' && *p <= 'z')) {
            cmd = *p++;
        }
        p = skip_ws(p);
        switch (cmd) {
            case 'M':
                p = read_float(p, &x); p = skip_ws(p);
                p = read_float(p, &y);
                cairo_move_to(cr, x, y);
                cmd = 'L'; break;
            case 'L':
                p = read_float(p, &x); p = skip_ws(p);
                p = read_float(p, &y);
                cairo_line_to(cr, x, y); break;
            case 'C':
                p = read_float(p, &x1); p = skip_ws(p);
                p = read_float(p, &y1); p = skip_ws(p);
                p = read_float(p, &x2); p = skip_ws(p);
                p = read_float(p, &y2); p = skip_ws(p);
                p = read_float(p, &x);  p = skip_ws(p);
                p = read_float(p, &y);
                cairo_curve_to(cr, x1,y1, x2,y2, x,y); break;
            case 'Q': {
                float qx1, qy1, qx, qy;
                p = read_float(p, &qx1); p = skip_ws(p);
                p = read_float(p, &qy1); p = skip_ws(p);
                p = read_float(p, &qx);  p = skip_ws(p);
                p = read_float(p, &qy);
                /* Convert quadratic to cubic */
                double cx, cy;
                cairo_get_current_point(cr, &cx, &cy);
                cairo_curve_to(cr,
                    cx  + 2.0/3.0*(qx1-cx),  cy  + 2.0/3.0*(qy1-cy),
                    qx  + 2.0/3.0*(qx1-qx),  qy  + 2.0/3.0*(qy1-qy),
                    qx, qy);
                break;
            }
            case 'Z': case 'z':
                cairo_close_path(cr); break;
            default:
                p++; break; /* skip unknown */
        }
        p = skip_ws(p);
    }
}

/* ── Public: draw one overlay ───────────────────────────────────────────── */
void overlay_draw(cairo_t *cr, const OverlayDef *ov, int view_index, float alpha)
{
    if (!ov || alpha <= 0.0f) return;

    const char *path_str = NULL;
    switch (view_index) {
        case 0: path_str = ov->path_anterior;  break;
        case 1: path_str = ov->path_posterior; break;
        case 2: path_str = ov->path_lateral_r; break;
        case 3: path_str = ov->path_lateral_l; break;
        case 4:
        case 5: path_str = ov->path_hand;      break;
        case 6:
        case 7: path_str = ov->path_foot;      break;
        default: break;
    }
    if (!path_str) return;

    cairo_save(cr);
    cairo_path_from_svg(cr, path_str);
    cairo_set_source_rgba(cr, ov->r, ov->g, ov->b, alpha * 0.5f);
    cairo_fill_preserve(cr);
    cairo_set_source_rgba(cr, ov->r, ov->g, ov->b, alpha);
    cairo_set_line_width(cr, 1.2);
    cairo_stroke(cr);
    cairo_restore(cr);
}

/* ── Lookup helpers ──────────────────────────────────────────────────────── */
const OverlayDef *overlay_get(OverlayCategory cat, int index)
{
    switch (cat) {
        case OVERLAY_DERMATOME:
            if (index < 0 || index >= DERMATOME_COUNT) return NULL;
            return &DERMATOME_OVERLAYS[index];
        case OVERLAY_PERIPHERAL:
            if (index < 0 || index >= PERIPHERAL_COUNT) return NULL;
            return &PERIPHERAL_OVERLAYS[index];
        case OVERLAY_SOMATIC:
            if (index < 0 || index >= SOMATIC_COUNT) return NULL;
            return &SOMATIC_OVERLAYS[index];
        default: return NULL;
    }
}

int overlay_count(OverlayCategory cat)
{
    switch (cat) {
        case OVERLAY_DERMATOME:  return DERMATOME_COUNT;
        case OVERLAY_PERIPHERAL: return PERIPHERAL_COUNT;
        case OVERLAY_SOMATIC:    return SOMATIC_COUNT;
        default: return 0;
    }
}

const char *overlay_category_label(OverlayCategory cat)
{
    switch (cat) {
        case OVERLAY_DERMATOME:  return "Dermatomes";
        case OVERLAY_PERIPHERAL: return "Peripheral nerves";
        case OVERLAY_SOMATIC:    return "Somatic referral";
        default: return "None";
    }
}
