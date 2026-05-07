#include "svg_views.h"
#include <librsvg/rsvg.h>
#include <stdio.h>
#include <string.h>

static const char *SVG_NAMES[VIEW_COUNT] = {
    "anterior.svg",
    "posterior.svg",
    "lateral_r.svg",
    "lateral_l.svg",
    "hand_palmar.svg",
    "hand_dorsal.svg",
    "foot_plantar.svg",
    "foot_dorsal.svg",
};

static RsvgHandle *g_svg[VIEW_COUNT];

static void try_dir(const char *dir)
{
    for (int i = 0; i < VIEW_COUNT; i++) {
        if (g_svg[i]) continue;
        char path[1024];
        snprintf(path, sizeof(path), "%s/%s", dir, SVG_NAMES[i]);
        GError *err = NULL;
        RsvgHandle *h = rsvg_handle_new_from_file(path, &err);
        if (h) {
            g_svg[i] = h;
        } else {
            if (err) g_error_free(err);
        }
    }
}

void svg_views_init(void)
{
    /* Priority order: user overrides first, then system, then dev tree */
    char buf[1024];
    const char *home = g_get_home_dir();

    snprintf(buf, sizeof(buf), "%s/.local/share/physio-bodychart/views", home);
    try_dir(buf);

    try_dir("/usr/local/share/physio-bodychart/views");
    try_dir("/usr/share/physio-bodychart/views");

    /* Dev: SVGs saved directly in the source tree */
    snprintf(buf, sizeof(buf), "%s/Projects/physio-bodychart/physio-bodychart/views", home);
    try_dir(buf);

    try_dir("data/views");   /* fallback when running from build/ in dev */
}

gboolean svg_view_available(BodyView view)
{
    return g_svg[view] != NULL;
}

void svg_view_draw(cairo_t *cr, BodyView view)
{
    RsvgHandle *h = g_svg[view];
    if (!h) return;
    RsvgRectangle vp = {0.0, 0.0, 200.0, 400.0};
    GError *err = NULL;
    rsvg_handle_render_document(h, cr, &vp, &err);
    if (err) g_error_free(err);
}
