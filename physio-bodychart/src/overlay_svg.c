#include "overlay_svg.h"
#include <librsvg/rsvg.h>
#include <stdio.h>
#include <glib.h>

/* Filenames within the views directory, indexed by view (ant=0, post=1) */
static const char *DERM_NAMES[2] = {
    "anterior dermatomes.svg",
    "posterior dermatomes.svg",
};
static const char *PERIPH_NAMES[2] = {
    "anterior peripheral n.svg",
    "posterior peripheral n.svg",
};

static RsvgHandle *g_derm[2];
static RsvgHandle *g_periph[2];

static void load_svgs_from_dir(const char *dir)
{
    for (int i = 0; i < 2; i++) {
        if (!g_derm[i]) {
            char path[1024];
            snprintf(path, sizeof(path), "%s/%s", dir, DERM_NAMES[i]);
            GError *err = NULL;
            RsvgHandle *h = rsvg_handle_new_from_file(path, &err);
            if (h) g_derm[i] = h;
            else if (err) g_error_free(err);
        }
        if (!g_periph[i]) {
            char path[1024];
            snprintf(path, sizeof(path), "%s/%s", dir, PERIPH_NAMES[i]);
            GError *err = NULL;
            RsvgHandle *h = rsvg_handle_new_from_file(path, &err);
            if (h) g_periph[i] = h;
            else if (err) g_error_free(err);
        }
    }
}

void overlay_svg_init(void)
{
    char buf[1024];
    const char *home = g_get_home_dir();

    snprintf(buf, sizeof(buf), "%s/.local/share/physio-bodychart/views", home);
    load_svgs_from_dir(buf);
    load_svgs_from_dir("/usr/local/share/physio-bodychart/views");
    load_svgs_from_dir("/usr/share/physio-bodychart/views");
    snprintf(buf, sizeof(buf), "%s/Projects/physio-bodychart/physio-bodychart/views", home);
    load_svgs_from_dir(buf);
    load_svgs_from_dir("data/views");
}

static void render_svg(RsvgHandle *h, cairo_t *cr)
{
    RsvgRectangle vp = { 0.0, 0.0, 200.0, 400.0 };
    GError *err = NULL;
    rsvg_handle_render_document(h, cr, &vp, &err);
    if (err) g_error_free(err);
}

void overlay_svg_draw_derm(cairo_t *cr, int view_index)
{
    if (view_index < 0 || view_index > 1) return;
    if (g_derm[view_index]) render_svg(g_derm[view_index], cr);
}

void overlay_svg_draw_periph(cairo_t *cr, int view_index)
{
    if (view_index < 0 || view_index > 1) return;
    if (g_periph[view_index]) render_svg(g_periph[view_index], cr);
}
