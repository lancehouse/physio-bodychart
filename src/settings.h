#pragma once
typedef struct _AppState AppState;

/* Load ~/.config/physiochart/settings.conf into app state (silently no-ops if missing) */
void settings_load(AppState *app);

/* Parse and strip known --flag=value args from argv, modifying argc in place */
void settings_apply_args(AppState *app, int *argc, char **argv);
