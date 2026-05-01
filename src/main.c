#include <gtk/gtk.h>
#include <string.h>
#include "canvas.h"
#include "window.h"
#include "stroke.h"
#include "overlays.h"
#include "svg_views.h"
#include "overlay_svg.h"
#include "settings.h"
#include "input.h"

static void on_activate(GtkApplication *app, gpointer user_data)
{
    AppState *state = user_data;
    window_create(state, app);
}

int main(int argc, char *argv[])
{
    svg_views_init();
    overlay_svg_init();

    /* Initialise app state */
    AppState state;
    memset(&state, 0, sizeof(state));
    state.strokes          = stroke_list_new();
    state.current_view     = VIEW_ANTERIOR;
    state.layout_mode      = LAYOUT_QUAD;
    state.tool             = TOOL_DRAW;
    state.symptom          = SYMPTOM_PAIN_CONSTANT;
    state.overlay_visible  = FALSE;
    state.overlay_category = OVERLAY_DERMATOME;
    state.overlay_index    = 0;
    state.overlay_alpha    = 0.5f;
    state.canvas_w         = 900;
    state.canvas_h         = 700;

    state.pen_gamma           = 0.3f;
    state.pen_wide_mode       = FALSE;
    state.pen_palm_reject     = TRUE;
    state.pen_btn_action      = BTN_CYCLE_SYMPTOM;
    state.pen_dot_radius      = 1.0f;
    state.pen_dot_spacing     = 4.5f;
    state.pen_dash_len        = 2.0f;
    state.pen_dash_spacing    = 5.0f;
    state.pen_dash_width      = 0.5f;
    state.pen_x_arm           = 2.0f;
    state.pen_x_spacing       = 6.0f;
    state.pen_x_width         = 0.5f;
    state.pen_tilt_weight     = 0.0f;
    state.right_slot_views[0] = VIEW_LATERAL_L;
    state.right_slot_views[1] = VIEW_LATERAL_R;

    input_hotkeys_init(&state);   /* set defaults; settings_load may override */
    settings_load(&state);
    settings_apply_args(&state, &argc, argv);

    GtkApplication *gtk_app = gtk_application_new(
        "com.physio.bodychart",
        G_APPLICATION_DEFAULT_FLAGS);

    g_signal_connect(gtk_app, "activate", G_CALLBACK(on_activate), &state);

    int status = g_application_run(G_APPLICATION(gtk_app), argc, argv);

    stroke_list_free(state.strokes);
    g_object_unref(gtk_app);
    return status;
}
