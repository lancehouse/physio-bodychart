#include "settings.h"
#include "canvas.h"
#include "input.h"
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <sys/stat.h>
#include <errno.h>

/* ── Hotkey value parser ─────────────────────────────────────────────────── *
 * Accepts: [ctrl+][shift+][alt+]<keyname>                                    *
 * Key names: single chars ("d", "1"), GDK names ("F1", "Home", "Delete"),   *
 * or aliases ("[" = bracketleft, "]" = bracketright).                        */
static void parse_hotkey(const char *val, guint *out_kv, GdkModifierType *out_mod)
{
    GdkModifierType mod = 0;
    const char *p = val;
    char tmp[8];

    /* Strip modifier prefixes (case-insensitive) */
    while (1) {
        size_t len = strlen(p);
        if (len >= 5) {
            strncpy(tmp, p, 5); tmp[5] = '\0';
            for (int i = 0; tmp[i]; i++) tmp[i] = (char)g_ascii_tolower(tmp[i]);
            if (strcmp(tmp, "ctrl+") == 0) { mod |= GDK_CONTROL_MASK; p += 5; continue; }
        }
        if (len >= 6) {
            strncpy(tmp, p, 6); tmp[6] = '\0';
            for (int i = 0; tmp[i]; i++) tmp[i] = (char)g_ascii_tolower(tmp[i]);
            if (strcmp(tmp, "shift+") == 0) { mod |= GDK_SHIFT_MASK; p += 6; continue; }
        }
        if (len >= 4) {
            strncpy(tmp, p, 4); tmp[4] = '\0';
            for (int i = 0; tmp[i]; i++) tmp[i] = (char)g_ascii_tolower(tmp[i]);
            if (strcmp(tmp, "alt+") == 0) { mod |= GDK_META_MASK; p += 4; continue; }
        }
        break;
    }

    /* Aliases for symbols that aren't valid GDK names */
    const char *name = p;
    if (strcmp(p, "[") == 0)      name = "bracketleft";
    else if (strcmp(p, "]") == 0) name = "bracketright";
    else if (strcmp(p, "-") == 0) name = "minus";
    else if (strcmp(p, "=") == 0) name = "equal";
    else if (strcmp(p, "/") == 0) name = "slash";

    guint kv = gdk_keyval_from_name(name);
    if (kv == GDK_KEY_VoidSymbol && strlen(name) > 1) {
        /* Try capitalising first letter (f1→F1, home→Home, delete→Delete, etc.) */
        char cap[64];
        strncpy(cap, name, sizeof(cap) - 1); cap[sizeof(cap)-1] = '\0';
        cap[0] = (char)g_ascii_toupper(cap[0]);
        kv = gdk_keyval_from_name(cap);
    }

    if (kv != GDK_KEY_VoidSymbol) {
        *out_kv  = kv;
        *out_mod = mod;
    }
    /* If still VoidSymbol, silently ignore — default binding unchanged */
}

static void settings_path(char *buf, size_t len)
{
    const char *home = g_get_home_dir();
    snprintf(buf, len, "%s/.config/physiochart/settings.conf", home);
}

void settings_load(AppState *app)
{
    char path[512];
    settings_path(path, sizeof(path));

    FILE *f = fopen(path, "r");
    if (!f) return;

    char line[128];
    while (fgets(line, sizeof(line), f)) {
        /* strip trailing newline */
        size_t n = strlen(line);
        while (n > 0 && (line[n-1] == '\n' || line[n-1] == '\r')) line[--n] = '\0';

        if (line[0] == '#' || line[0] == '\0') continue;

        char key[64], val[64];
        if (sscanf(line, "%63[^=]=%63s", key, val) != 2) continue;

        if (strcmp(key, "pen_gamma") == 0) {
            float v = (float)atof(val);
            if (v >= 0.1f && v <= 2.0f) app->pen_gamma = v;
        } else if (strcmp(key, "pen_wide_mode") == 0) {
            app->pen_wide_mode = atoi(val) != 0;
        } else if (strcmp(key, "palm_reject") == 0) {
            app->pen_palm_reject = atoi(val) != 0;
        } else if (strcmp(key, "overlay_opacity") == 0) {
            float v = (float)atof(val);
            if (v >= 0.0f && v <= 1.0f) app->overlay_alpha = v;
        } else if (strcmp(key, "pen_dot_radius") == 0) {
            float v = (float)atof(val);
            if (v >= 0.2f && v <= 10.0f) app->pen_dot_radius = v;
        } else if (strcmp(key, "pen_dot_spacing") == 0) {
            float v = (float)atof(val);
            if (v >= 1.0f && v <= 30.0f) app->pen_dot_spacing = v;
        } else if (strcmp(key, "pen_dash_len") == 0) {
            float v = (float)atof(val);
            if (v >= 0.5f && v <= 15.0f) app->pen_dash_len = v;
        } else if (strcmp(key, "pen_dash_spacing") == 0) {
            float v = (float)atof(val);
            if (v >= 1.0f && v <= 30.0f) app->pen_dash_spacing = v;
        } else if (strcmp(key, "pen_dash_width") == 0) {
            float v = (float)atof(val);
            if (v >= 0.1f && v <= 5.0f) app->pen_dash_width = v;
        } else if (strcmp(key, "pen_x_arm") == 0) {
            float v = (float)atof(val);
            if (v >= 0.5f && v <= 12.0f) app->pen_x_arm = v;
        } else if (strcmp(key, "pen_x_spacing") == 0) {
            float v = (float)atof(val);
            if (v >= 1.0f && v <= 30.0f) app->pen_x_spacing = v;
        } else if (strcmp(key, "pen_x_width") == 0) {
            float v = (float)atof(val);
            if (v >= 0.1f && v <= 5.0f) app->pen_x_width = v;
        } else if (strcmp(key, "pen_tilt_weight") == 0) {
            float v = (float)atof(val);
            if (v >= 0.0f && v <= 1.0f) app->pen_tilt_weight = v;
        } else if (strncmp(key, "hotkey_", 7) == 0) {
            for (int i = 0; i < HK_COUNT; i++) {
                if (strcmp(key, HOTKEY_NAMES[i]) == 0) {
                    parse_hotkey(val, &app->hotkey_val[i], &app->hotkey_mod[i]);
                    break;
                }
            }
        }
    }
    fclose(f);
}

void settings_apply_args(AppState *app, int *argc, char **argv)
{
    int out = 1;
    for (int i = 1; i < *argc; i++) {
        if (strncmp(argv[i], "--pen-gamma=", 12) == 0) {
            float v = (float)atof(argv[i] + 12);
            if (v >= 0.1f && v <= 2.0f) app->pen_gamma = v;
        } else if (strcmp(argv[i], "--wide") == 0) {
            app->pen_wide_mode = TRUE;
        } else if (strcmp(argv[i], "--no-palm-reject") == 0) {
            app->pen_palm_reject = FALSE;
        } else if (strncmp(argv[i], "--overlay-opacity=", 18) == 0) {
            float v = (float)atof(argv[i] + 18);
            if (v >= 0.0f && v <= 1.0f) app->overlay_alpha = v;
        } else {
            argv[out++] = argv[i];
        }
    }
    *argc = out;
}
