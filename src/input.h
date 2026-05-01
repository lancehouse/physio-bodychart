#pragma once
#include <gtk/gtk.h>
#include "stroke.h"
#include "overlays.h"

typedef enum {
    TOOL_DRAW = 0,
    TOOL_ERASE,
    TOOL_LINK,
    TOOL_NOTE,
    TOOL_ARROW,
} ActiveTool;

/* ── Hotkey actions ──────────────────────────────────────────────────────── */
typedef enum {
    HK_SYMPTOM_CONSTANT = 0,
    HK_SYMPTOM_INTERMITTENT,
    HK_SYMPTOM_PARAESTHESIA,
    HK_SYMPTOM_ANAESTHESIA,
    HK_SYMPTOM_DEEP_ACHE,
    HK_SYMPTOM_TICK,
    HK_TOOL_DRAW,
    HK_TOOL_ERASE,
    HK_TOOL_NOTE,
    HK_TOOL_LINK,
    HK_WIDE_MODE,
    HK_UNDO,
    HK_CLEAR,
    HK_OVERLAY_DERM,
    HK_OVERLAY_PERIPH,
    HK_OVERLAY_SOMATIC,
    HK_OVERLAY_TOGGLE,
    HK_OVERLAY_PREV,
    HK_OVERLAY_NEXT,
    HK_VIEW_QUAD,
    HK_VIEW_ANTERIOR,
    HK_VIEW_POSTERIOR,
    HK_VIEW_LATERAL_L,
    HK_VIEW_LATERAL_R,
    HK_ZOOM_RESET,
    HK_SAVE_SVG,
    HK_SAVE_PNG,
    HK_SAVE_PDF,
    HK_COUNT
} HotkeyAction;

/* Config-file key name for each action */
extern const char *const HOTKEY_NAMES[HK_COUNT];

typedef struct _AppState AppState;

void input_begin(AppState *app, double x, double y, double pressure);
void input_motion(AppState *app, double x, double y, double pressure);
void input_end(AppState *app);
void input_cancel(AppState *app);

/* Set app->hotkey_val / hotkey_mod to built-in defaults.
 * Call before settings_load() so the config file can override. */
void input_hotkeys_init(AppState *app);

gboolean input_key_pressed(AppState *app, guint keyval, GdkModifierType mods);
