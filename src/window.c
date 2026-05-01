#include "window.h"
#include "canvas.h"
#include "input.h"
#include "overlays.h"
#include "stroke.h"
#include "session.h"
#include <string.h>
#include <stdio.h>

/* ── Forward decls ──────────────────────────────────────────────────────── */
static void update_toolbar_state(AppState *app);

/* ── Key controller ─────────────────────────────────────────────────────── */
static gboolean on_key_pressed(GtkEventControllerKey *ctrl,
                                guint keyval, guint keycode,
                                GdkModifierType mods, gpointer data)
{
    (void)ctrl; (void)keycode;
    return input_key_pressed((AppState *)data, keyval, mods);
}

/* ── Symptom buttons ────────────────────────────────────────────────────── */
static void on_symptom_clicked(GtkButton *btn, gpointer data)
{
    AppState *app = ((gpointer*)data)[0];
    SymptomType st = (SymptomType)(gintptr)((gpointer*)data)[1];
    (void)btn;
    app->symptom = st;
    app->tool    = TOOL_DRAW;
    update_toolbar_state(app);
}

/* ── Layout / view switching ────────────────────────────────────────────── */
static void on_layout_clicked(GtkButton *btn, gpointer data)
{
    (void)btn;
    gpointer *pair  = data;
    AppState  *app  = pair[0];
    LayoutMode mode = (LayoutMode)(gintptr)pair[1];
    canvas_set_layout(app, mode);
    update_toolbar_state(app);
}

/* ── Overlay controls ───────────────────────────────────────────────────── */
static void on_overlay_cat_clicked(GtkButton *btn, gpointer data)
{
    (void)btn;
    gpointer *pair = data;
    AppState *app  = pair[0];
    OverlayCategory cat = (OverlayCategory)(gintptr)pair[1];
    if (app->overlay_category == cat && app->overlay_visible) {
        app->overlay_visible = FALSE;
    } else {
        app->overlay_category = cat;
        app->overlay_index    = 0;
        app->overlay_visible  = TRUE;
    }
    canvas_invalidate(app);
    update_toolbar_state(app);
}

static void on_overlay_prev(GtkButton *btn, gpointer data)
{
    (void)btn;
    AppState *app = data;
    int n = overlay_count(app->overlay_category);
    if (n > 0) {
        app->overlay_index = (app->overlay_index - 1 + n) % n;
        app->overlay_visible = TRUE;
        canvas_invalidate(app);
        update_toolbar_state(app);
    }
}

static void on_overlay_next(GtkButton *btn, gpointer data)
{
    (void)btn;
    AppState *app = data;
    int n = overlay_count(app->overlay_category);
    if (n > 0) {
        app->overlay_index = (app->overlay_index + 1) % n;
        app->overlay_visible = TRUE;
        canvas_invalidate(app);
        update_toolbar_state(app);
    }
}

static void on_overlay_alpha(GtkRange *range, gpointer data)
{
    AppState *app = data;
    app->overlay_alpha = (float)gtk_range_get_value(range);
    canvas_invalidate(app);
}

/* ── Note tool button ───────────────────────────────────────────────────── */
static void on_note_clicked(GtkButton *btn, gpointer data)
{
    (void)btn;
    AppState *app = data;
    app->tool = (app->tool == TOOL_NOTE) ? TOOL_DRAW : TOOL_NOTE;
    update_toolbar_state(app);
}

/* ── Arrow tool button ──────────────────────────────────────────────────── */
static void on_arrow_clicked(GtkButton *btn, gpointer data)
{
    (void)btn;
    AppState *app = data;
    app->tool = (app->tool == TOOL_ARROW) ? TOOL_DRAW : TOOL_ARROW;
    update_toolbar_state(app);
}

/* ── Tool buttons ───────────────────────────────────────────────────────── */
static void on_erase_clicked(GtkButton *btn, gpointer data)
{
    (void)btn;
    AppState *app = data;
    app->tool = (app->tool == TOOL_ERASE) ? TOOL_DRAW : TOOL_ERASE;
    update_toolbar_state(app);
}
/* ── Link matrix popup ───────────────────────────────────────────────────── */

static GtkWidget *make_btn(const char *label, int min_w, int min_h);  /* fwd */

typedef struct _LinkPopupData LinkPopupData;
typedef struct {
    LinkPopupData *pd;
    int            from, to;
} LinkCellData;

struct _LinkPopupData {
    AppState     *app;
    GtkWidget    *window;
    GtkWidget    *cell_btns[MAX_NOTES][MAX_NOTES];
    LinkCellData  cd[MAX_NOTES][MAX_NOTES];
};

static const char *link_state_label(int state)
{
    switch (state) {
        case LINK_YES: return "-->";
        case LINK_NO:  return "-/->";
        default:       return "  ";
    }
}

static void on_link_cell(GtkButton *btn, gpointer data)
{
    (void)btn;
    LinkCellData  *c  = data;
    LinkPopupData *pd = c->pd;
    int i = c->from, j = c->to;
    pd->app->link_matrix[i][j] = (pd->app->link_matrix[i][j] + 1) % 3;
    gtk_button_set_label(GTK_BUTTON(pd->cell_btns[i][j]),
                         link_state_label(pd->app->link_matrix[i][j]));
}

static void on_link_generate(GtkButton *btn, gpointer data)
{
    (void)btn;
    LinkPopupData *pd = data;
    AppState *app = pd->app;

    app->link_rel_count = 0;
    for (int i = 0; i < app->note_count; i++) {
        for (int j = 0; j < app->note_count; j++) {
            if (i == j) continue;
            int st = app->link_matrix[i][j];
            if (st == LINK_NEITHER) continue;
            if (app->link_rel_count < MAX_NOTES * MAX_NOTES) {
                app->link_relations[app->link_rel_count].from  = i;
                app->link_relations[app->link_rel_count].to    = j;
                app->link_relations[app->link_rel_count].state = st;
                app->link_rel_count++;
            }
        }
    }

    if (app->link_rel_count > 0) {
        app->link_summary_active = TRUE;
        app->link_summary_view   = (int)VIEW_ANTERIOR;
        app->link_summary_bx     = 12.0;
        app->link_summary_by     = 378.0;
    }
    canvas_invalidate(app);
    gtk_window_destroy(GTK_WINDOW(pd->window));
}

static void on_link_cancel(GtkButton *btn, gpointer data)
{
    (void)btn;
    LinkPopupData *pd = data;
    gtk_window_destroy(GTK_WINDOW(pd->window));
}

static void on_link_popup_destroy(GtkWidget *w, gpointer d)
{
    (void)w;
    LinkPopupData *pd = d;
    pd->app->tool = TOOL_DRAW;
    if (pd->app->toolbar_update_cb) pd->app->toolbar_update_cb(pd->app);
    g_free(d);
}

static void show_link_popup(AppState *app)
{
    if (app->note_count < 1) return;

    LinkPopupData *pd = g_malloc0(sizeof(LinkPopupData));
    pd->app = app;

    pd->window = gtk_window_new();
    gtk_window_set_title(GTK_WINDOW(pd->window), "Link notes");
    gtk_window_set_transient_for(GTK_WINDOW(pd->window),
                                 GTK_WINDOW(app->window));
    gtk_window_set_modal(GTK_WINDOW(pd->window), TRUE);
    gtk_window_set_resizable(GTK_WINDOW(pd->window), FALSE);
    g_signal_connect(pd->window, "destroy",
                     G_CALLBACK(on_link_popup_destroy), pd);

    int n = app->note_count;

    /* Outer layout */
    GtkWidget *outer = gtk_box_new(GTK_ORIENTATION_VERTICAL, 10);
    gtk_widget_set_margin_top(outer, 14);
    gtk_widget_set_margin_bottom(outer, 14);
    gtk_widget_set_margin_start(outer, 14);
    gtk_widget_set_margin_end(outer, 14);

    GtkWidget *title = gtk_label_new("Tap cells to cycle:  blank → --> → -/-> → blank");
    gtk_widget_set_name(title, "wiz-title");
    gtk_box_append(GTK_BOX(outer), title);

    /* Matrix grid */
    GtkWidget *grid = gtk_grid_new();
    gtk_grid_set_row_spacing(GTK_GRID(grid), 3);
    gtk_grid_set_column_spacing(GTK_GRID(grid), 3);

    /* Column headers */
    for (int j = 0; j < n; j++) {
        char lbl[16]; snprintf(lbl, sizeof(lbl), "→ %d", j+1);
        GtkWidget *h = gtk_label_new(lbl);
        gtk_widget_set_size_request(h, 52, 28);
        gtk_label_set_xalign(GTK_LABEL(h), 0.5);
        gtk_grid_attach(GTK_GRID(grid), h, j+1, 0, 1, 1);
    }

    /* Rows */
    for (int i = 0; i < n; i++) {
        char row_lbl[16]; snprintf(row_lbl, sizeof(row_lbl), "%d", i+1);
        GtkWidget *rl = gtk_label_new(row_lbl);
        gtk_widget_set_size_request(rl, 28, 44);
        gtk_label_set_xalign(GTK_LABEL(rl), 0.5);
        gtk_grid_attach(GTK_GRID(grid), rl, 0, i+1, 1, 1);

        for (int j = 0; j < n; j++) {
            if (i == j) {
                GtkWidget *dash = gtk_label_new("—");
                gtk_widget_set_size_request(dash, 52, 44);
                gtk_label_set_xalign(GTK_LABEL(dash), 0.5);
                gtk_grid_attach(GTK_GRID(grid), dash, j+1, i+1, 1, 1);
            } else {
                pd->cd[i][j].pd   = pd;
                pd->cd[i][j].from = i;
                pd->cd[i][j].to   = j;
                GtkWidget *btn = gtk_button_new_with_label(
                    link_state_label(app->link_matrix[i][j]));
                gtk_widget_set_name(btn, "wiz-num");
                gtk_widget_set_size_request(btn, 52, 44);
                g_signal_connect(btn, "clicked",
                                 G_CALLBACK(on_link_cell), &pd->cd[i][j]);
                pd->cell_btns[i][j] = btn;
                gtk_grid_attach(GTK_GRID(grid), btn, j+1, i+1, 1, 1);
            }
        }
    }
    gtk_box_append(GTK_BOX(outer), grid);

    /* Action row */
    GtkWidget *actions = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 12);
    gtk_widget_set_halign(actions, GTK_ALIGN_END);
    GtkWidget *cancel_btn = make_btn("Cancel", 100, 44);
    g_signal_connect(cancel_btn, "clicked", G_CALLBACK(on_link_cancel), pd);
    GtkWidget *gen_btn = make_btn("Generate Summary", 180, 44);
    gtk_widget_set_name(gen_btn, "wiz-btn");
    g_signal_connect(gen_btn, "clicked", G_CALLBACK(on_link_generate), pd);
    gtk_box_append(GTK_BOX(actions), cancel_btn);
    gtk_box_append(GTK_BOX(actions), gen_btn);
    gtk_box_append(GTK_BOX(outer), actions);

    gtk_window_set_child(GTK_WINDOW(pd->window), outer);
    gtk_window_present(GTK_WINDOW(pd->window));
}

static void on_cycle_right_slot(GtkButton *btn, gpointer data)
{
    (void)btn;
    gpointer *pair = data;
    AppState  *app  = pair[0];
    int        slot = (int)(gintptr)pair[1];
    canvas_cycle_right_slot(app, slot);
    update_toolbar_state(app);
}

static void on_link_clicked(GtkButton *btn, gpointer data)
{
    (void)btn;
    AppState *app = data;
    app->tool = TOOL_LINK;
    update_toolbar_state(app);
    show_link_popup(app);
}
static void on_linemode_clicked(GtkButton *b, gpointer data)
{
    (void)b;
    AppState *app = data;
    app->pen_wide_mode = !app->pen_wide_mode;
    update_toolbar_state(app);
}
static void on_undo_clicked(GtkButton *btn, gpointer data)
{
    (void)btn;
    AppState *app = data;
    canvas_undo(app);
}
static void on_clear_clicked(GtkButton *btn, gpointer data)
{
    (void)btn;
    AppState *app = data;
    canvas_clear(app);
}

/* ── Toolbar state references ───────────────────────────────────────────── */
static GtkWidget *g_symptom_btns[SYMPTOM_COUNT];
static GtkWidget *g_note_btn;
static GtkWidget *g_arrow_btn;
static GtkWidget *g_erase_btn;
static GtkWidget *g_link_btn;
static GtkWidget *g_linemode_btn;
static GtkWidget *g_overlay_label;
static GtkWidget *g_overlay_cat_btns[3];
static GtkWidget *g_overlay_nav_box;
static GtkWidget *g_layout_btns[LAYOUT_COUNT];
static GtkWidget *g_right_slot_btns[2];  /* cycle buttons for right column */
static AppState  *g_app_ref;

static void update_toolbar_state(AppState *app)
{
    if (!g_app_ref) return;

    for (int i = 0; i < SYMPTOM_COUNT; i++) {
        if (!g_symptom_btns[i]) continue;
        gboolean active = (app->symptom == (SymptomType)i &&
                           app->tool    == TOOL_DRAW);
        gtk_widget_set_name(g_symptom_btns[i],
                            active ? "symptom-btn-active" : "symptom-btn");
    }

    if (g_note_btn)
        gtk_widget_set_name(g_note_btn,
            app->tool == TOOL_NOTE ? "tool-btn-active" : "tool-btn");
    if (g_arrow_btn)
        gtk_widget_set_name(g_arrow_btn,
            app->tool == TOOL_ARROW ? "tool-btn-active" : "tool-btn");
    if (g_erase_btn)
        gtk_widget_set_name(g_erase_btn,
            app->tool == TOOL_ERASE ? "tool-btn-active" : "tool-btn");
    if (g_link_btn)
        gtk_widget_set_name(g_link_btn,
            app->tool == TOOL_LINK ? "tool-btn-active" : "tool-btn");
    if (g_linemode_btn) {
        gtk_widget_set_name(g_linemode_btn,
            app->pen_wide_mode ? "tool-btn-active" : "tool-btn");
        gtk_button_set_label(GTK_BUTTON(g_linemode_btn),
            app->pen_wide_mode ? "Bold" : "Fine");
    }

    for (int i = 0; i < 3; i++) {
        if (!g_overlay_cat_btns[i]) continue;
        OverlayCategory cat = (OverlayCategory)(i + 1);
        gboolean active = (app->overlay_category == cat && app->overlay_visible);
        gtk_widget_set_name(g_overlay_cat_btns[i],
                            active ? "overlay-btn-active" : "overlay-btn");
    }

    for (int i = 0; i < LAYOUT_COUNT; i++) {
        if (!g_layout_btns[i]) continue;
        gboolean active = (app->layout_mode == (LayoutMode)i);
        gtk_widget_set_name(g_layout_btns[i],
                            active ? "tool-btn-active" : "tool-btn");
    }

    for (int i = 0; i < 2; i++) {
        if (!g_right_slot_btns[i]) continue;
        char buf[20];
        snprintf(buf, sizeof(buf), "%s \xe2\x86\xbb",
                 canvas_view_short_name(app->right_slot_views[i]));
        gtk_button_set_label(GTK_BUTTON(g_right_slot_btns[i]), buf);
    }

    if (g_overlay_nav_box) {
        /* Nav only makes sense for somatic (multiple patterns); hide for derm */
        gboolean show_nav = app->overlay_visible &&
                            app->overlay_category == OVERLAY_SOMATIC;
        gtk_widget_set_visible(g_overlay_nav_box, show_nav);
    }

    if (g_overlay_label) {
        if (app->overlay_visible && app->overlay_category != OVERLAY_NONE) {
            if (app->overlay_category == OVERLAY_DERMATOME)
                gtk_label_set_text(GTK_LABEL(g_overlay_label), "Dermatomes");
            else if (app->overlay_category == OVERLAY_PERIPHERAL)
                gtk_label_set_text(GTK_LABEL(g_overlay_label), "Peripheral");
            else {
                const OverlayDef *ov = overlay_get(app->overlay_category,
                                                   app->overlay_index);
                if (ov) {
                    char buf[64];
                    int n = overlay_count(app->overlay_category);
                    snprintf(buf, sizeof(buf), "%s  %d/%d",
                             ov->short_label, app->overlay_index + 1, n);
                    gtk_label_set_text(GTK_LABEL(g_overlay_label), buf);
                }
            }
        } else {
            gtk_label_set_text(GTK_LABEL(g_overlay_label), "Off");
        }
    }
}

/* ── Shared button factory ───────────────────────────────────────────────── */
static GtkWidget *make_btn(const char *label, int min_w, int min_h)
{
    GtkWidget *btn = gtk_button_new_with_label(label);
    gtk_widget_set_size_request(btn, min_w, min_h);
    gtk_widget_set_name(btn, "tool-btn");
    return btn;
}

/* ── 2-column homogeneous grid helper ────────────────────────────────────── */
static GtkWidget *make_grid2col(void)
{
    GtkWidget *g = gtk_grid_new();
    gtk_grid_set_row_spacing(GTK_GRID(g), 3);
    gtk_grid_set_column_spacing(GTK_GRID(g), 3);
    gtk_grid_set_column_homogeneous(GTK_GRID(g), TRUE);
    return g;
}

/* ── CSS ─────────────────────────────────────────────────────────────────── */
static void apply_css(void)
{
    GtkCssProvider *css = gtk_css_provider_new();
    gtk_css_provider_load_from_string(css,
        "window { background: #2b2b2b; }"
        "#toolbar { background: #1e1e1e; padding: 2px; }"
        "button { "
        "  min-height: 34px; min-width: 28px; "
        "  border-radius: 6px; padding: 1px 3px; "
        "  font-size: 11px; "
        "}"
        "#symptom-btn { background: #3a3a3a; color: #ccc; border: 1px solid #555; }"
        "#symptom-btn-active { background: #555; color: #fff; border: 2px solid #aaa; }"
        "#tool-btn { background: #333; color: #bbb; border: 1px solid #555; }"
        "#tool-btn-active { background: #666; color: #fff; border: 2px solid #aaa; }"
        "#overlay-btn { background: #2a3040; color: #8ab; border: 1px solid #446; }"
        "#overlay-btn-active { background: #3a5080; color: #cef; border: 2px solid #68c; }"
        "#section-label { color: #888; font-size: 9px; margin-top: 4px; margin-bottom: 1px; }"
        "#overlay-name { color: #8ab; font-size: 10px; }"
        "separator { background: #444; min-width: 1px; margin: 1px 2px; }"
        "#col-header { background: #f0f0f0; border-bottom: 1px solid #ccc; min-height: 28px; }"
        "#col-header label { font-size: 11px; font-weight: bold; color: #333; }"
        "#zoom-btn { min-height: 22px; min-width: 40px; padding: 0 6px; font-size: 10px;"
        "  background: #e0e0e0; color: #444; border: 1px solid #bbb; border-radius: 4px; }"
        "#zoom-btn:hover { background: #d0d0d0; }"

        /* ── Tab bar ── */
        "#sidebar { background: #1e1e1e; min-width: 110px; max-width: 110px; }"
        "#tab-bar { background: #151515; padding: 2px 2px 0 2px; }"
        "#tab-btn { background: #2a2a2a; color: #777; font-size: 11px;"
        "  border-radius: 4px 4px 0 0; min-height: 34px; min-width: 0;"
        "  border: none; padding: 0 4px; }"
        "#tab-btn-active { background: #1e1e1e; color: #fff; font-size: 11px;"
        "  border-radius: 4px 4px 0 0; min-height: 34px; min-width: 0;"
        "  border: none; padding: 0 4px; }"

        /* ── File tab ── */
        "#file-status { color: #7bc; font-size: 10px; padding: 4px 2px; }"

        /* ── Note wizard ── */
        "#wiz-title { font-size: 15px; font-weight: bold; color: #ddd;"
        "  margin-bottom: 6px; }"
        "#wiz-btn { font-size: 14px; min-height: 56px; min-width: 180px;"
        "  background: #2a4a70; color: #dde; border: 1px solid #4a6a90; }"
        "#wiz-btn:hover { background: #3a5a80; color: #fff; }"
        "#wiz-num { font-size: 14px; font-weight: bold; min-height: 52px;"
        "  min-width: 40px; background: #1e3050; color: #ccd;"
        "  border: 1px solid #3a5070; }"
        "#wiz-num:hover { background: #2a4060; color: #fff; }"
        "#wiz-qual-btn { font-size: 12px; min-height: 44px; min-width: 76px;"
        "  background: #2a4a70; color: #dde; border: 1px solid #4a6a90; }"
        "#wiz-qual-btn:hover { background: #3a5a80; color: #fff; }"
        "#wiz-window { background: #1a1a2e; }"
    );
    gtk_style_context_add_provider_for_display(
        gdk_display_get_default(),
        GTK_STYLE_PROVIDER(css),
        GTK_STYLE_PROVIDER_PRIORITY_APPLICATION);
}

/* ── Tab state ───────────────────────────────────────────────────────────── */
#define N_TABS 2
static GtkWidget *g_tab_stack;
static GtkWidget *g_tab_btns[N_TABS];
static GtkWidget *g_file_status;

static const char *TAB_NAMES[N_TABS] = { "draw", "file" };

static void set_active_tab(int idx)
{
    gtk_stack_set_visible_child_name(GTK_STACK(g_tab_stack), TAB_NAMES[idx]);
    for (int i = 0; i < N_TABS; i++)
        gtk_widget_set_name(g_tab_btns[i], i == idx ? "tab-btn-active" : "tab-btn");
}

static void on_tab_clicked(GtkButton *btn, gpointer data)
{
    (void)btn;
    set_active_tab((int)(gintptr)data);
}

/* ── Save / export callbacks ─────────────────────────────────────────────── */
static void do_export(const char *ext)
{
    if (!g_app_ref) return;
    char path[1024];
    session_auto_path(path, sizeof(path), ext);

    gboolean ok = FALSE;
    if      (strcmp(ext, "svg") == 0) ok = session_save(g_app_ref, path);
    else if (strcmp(ext, "png") == 0) ok = session_export_png(g_app_ref, path);
    else if (strcmp(ext, "pdf") == 0) ok = session_export_pdf(g_app_ref, path);

    if (ok) {
        const char *name = strrchr(path, '/');
        name = name ? name + 1 : path;
        char msg[1100];
        snprintf(msg, sizeof(msg), "Saved:\n%s", name);
        gtk_label_set_text(GTK_LABEL(g_file_status), msg);
    } else {
        gtk_label_set_text(GTK_LABEL(g_file_status), "Save failed");
    }
}

static void on_save_svg(GtkButton *b, gpointer d) { (void)b; (void)d; do_export("svg"); }
static void on_save_png(GtkButton *b, gpointer d) { (void)b; (void)d; do_export("png"); }
static void on_save_pdf(GtkButton *b, gpointer d) { (void)b; (void)d; do_export("pdf"); }

/* Public wrapper used by keyboard shortcuts in input.c */
void window_do_export(const char *ext) { do_export(ext); }

/* ── Note wizard ─────────────────────────────────────────────────────────── */

typedef struct _WizardData WizardData;
typedef struct {
    WizardData *wd;
    int         value;
    int         step;   /* 0=temporal, 1=depth, 2=quality, 3=avg, 4=worst */
} WBtnPair;

struct _WizardData {
    AppState   *app;
    int         view;
    double      bx, by;
    GtkWidget  *window;
    GtkWidget  *stack;
    int         temporal;       /* 0=C 1=Im */
    int         depth;          /* 0=S 1=D */
    int         quality;        /* 0-12 index into QUALITY_SHORT */
    int         avg_int;
    int         worst_int;
    WBtnPair    c_q1[2];
    WBtnPair    c_q2[2];
    WBtnPair    c_q3[NOTE_QUALITY_COUNT];
    WBtnPair    n_q4[11];
    WBtnPair    n_q5[11];
};

static gboolean g_wizard_open = FALSE;

static void wizard_commit(WizardData *wd);   /* forward decl */

static void on_wiz_answer(GtkButton *b, gpointer data)
{
    (void)b;
    WBtnPair   *p  = data;
    WizardData *wd = p->wd;
    static const char *pages[] = { "q1", "q2", "q3", "q4", "q5" };
    switch (p->step) {
        case 0: wd->temporal  = p->value;
                gtk_stack_set_visible_child_name(GTK_STACK(wd->stack), pages[1]); break;
        case 1: wd->depth     = p->value;
                gtk_stack_set_visible_child_name(GTK_STACK(wd->stack), pages[2]); break;
        case 2: wd->quality   = p->value;
                gtk_stack_set_visible_child_name(GTK_STACK(wd->stack), pages[3]); break;
        case 3: wd->avg_int   = p->value;
                gtk_stack_set_visible_child_name(GTK_STACK(wd->stack), pages[4]); break;
        case 4: wd->worst_int = p->value;
                wizard_commit(wd); break;
    }
}

static void on_wizard_destroy(GtkWidget *w, gpointer d)
{
    (void)w;
    g_wizard_open = FALSE;
    g_free(d);
}

static const char *QUALITY_SHORT[NOTE_QUALITY_COUNT] = {
    "Pain", "Ache", "Numb", "Shrp", "Dull",
    "Hot",  "Cold", "Itch", "Craw", "Elec",
    "Shot", "Buzz", "Othr", "P+N"
};

static void wizard_commit(WizardData *wd)
{
    AppState *app = wd->app;
    if (app->note_count < MAX_NOTES) {
        NoteAnnotation *na = &app->notes[app->note_count];
        na->view             = wd->view;
        na->bx               = wd->bx;
        na->by               = wd->by;
        na->number           = app->note_count + 1;
        na->temporal         = wd->temporal;
        na->depth            = wd->depth;
        na->quality          = wd->quality;
        na->avg_intensity    = wd->avg_int;
        na->worst_intensity  = wd->worst_int;
        snprintf(na->text, sizeof(na->text), "(%d)%s %s %s %d/%d",
                 na->number,
                 na->temporal == 0 ? "Con" : "Int",
                 na->depth    == 0 ? "Sup" : "Dep",
                 QUALITY_SHORT[na->quality],
                 na->avg_intensity, na->worst_intensity);
        app->note_count++;
    }
    canvas_invalidate(app);
    gtk_window_destroy(GTK_WINDOW(wd->window));  /* triggers on_wizard_destroy → g_free */
}

static GtkWidget *wiz_choice_row(WBtnPair pairs[2],
                                  const char *l0, const char *l1)
{
    GtkWidget *row = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 16);
    gtk_widget_set_halign(row, GTK_ALIGN_CENTER);
    const char *lbls[2] = { l0, l1 };
    for (int i = 0; i < 2; i++) {
        GtkWidget *btn = gtk_button_new_with_label(lbls[i]);
        gtk_widget_set_name(btn, "wiz-btn");
        g_signal_connect(btn, "clicked", G_CALLBACK(on_wiz_answer), &pairs[i]);
        gtk_box_append(GTK_BOX(row), btn);
    }
    return row;
}

static GtkWidget *wiz_number_row(WBtnPair pairs[11])
{
    GtkWidget *row = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 4);
    gtk_widget_set_halign(row, GTK_ALIGN_CENTER);
    for (int n = 0; n <= 10; n++) {
        char buf[3];
        snprintf(buf, sizeof(buf), "%d", n);
        GtkWidget *btn = gtk_button_new_with_label(buf);
        gtk_widget_set_name(btn, "wiz-num");
        g_signal_connect(btn, "clicked", G_CALLBACK(on_wiz_answer), &pairs[n]);
        gtk_box_append(GTK_BOX(row), btn);
    }
    return row;
}

static GtkWidget *wiz_quality_grid(WBtnPair pairs[NOTE_QUALITY_COUNT])
{
    static const char *labels[NOTE_QUALITY_COUNT] = {
        "Pain",     "Ache",     "Numb",    "Sharp",
        "Dull",     "Hot",      "Cold",    "Itch",
        "Crawl",    "Electric", "Shooting","Buzzing",
        "Other",    "P+N"
    };
    GtkWidget *grid = gtk_grid_new();
    gtk_grid_set_row_spacing(GTK_GRID(grid), 4);
    gtk_grid_set_column_spacing(GTK_GRID(grid), 4);
    gtk_widget_set_halign(grid, GTK_ALIGN_CENTER);
    /* Items 0–11 in a 4-column × 3-row block */
    for (int i = 0; i < 12; i++) {
        GtkWidget *btn = gtk_button_new_with_label(labels[i]);
        gtk_widget_set_name(btn, "wiz-qual-btn");
        g_signal_connect(btn, "clicked", G_CALLBACK(on_wiz_answer), &pairs[i]);
        gtk_grid_attach(GTK_GRID(grid), btn, i % 4, i / 4, 1, 1);
    }
    /* Row 3: Other (left 2 cols) + P+N (right 2 cols) */
    GtkWidget *other = gtk_button_new_with_label(labels[12]);
    gtk_widget_set_name(other, "wiz-qual-btn");
    gtk_widget_set_hexpand(other, TRUE);
    g_signal_connect(other, "clicked", G_CALLBACK(on_wiz_answer), &pairs[12]);
    gtk_grid_attach(GTK_GRID(grid), other, 0, 3, 2, 1);

    GtkWidget *pn = gtk_button_new_with_label(labels[13]);
    gtk_widget_set_name(pn, "wiz-qual-btn");
    gtk_widget_set_hexpand(pn, TRUE);
    g_signal_connect(pn, "clicked", G_CALLBACK(on_wiz_answer), &pairs[13]);
    gtk_grid_attach(GTK_GRID(grid), pn, 2, 3, 2, 1);
    return grid;
}

static GtkWidget *wiz_page(const char *title, GtkWidget *buttons)
{
    GtkWidget *page = gtk_box_new(GTK_ORIENTATION_VERTICAL, 10);
    gtk_widget_set_margin_top(page, 16);
    gtk_widget_set_margin_bottom(page, 16);
    gtk_widget_set_margin_start(page, 16);
    gtk_widget_set_margin_end(page, 16);
    GtkWidget *lbl = gtk_label_new(title);
    gtk_widget_set_name(lbl, "wiz-title");
    gtk_label_set_xalign(GTK_LABEL(lbl), 0.5);
    gtk_box_append(GTK_BOX(page), lbl);
    gtk_box_append(GTK_BOX(page), buttons);
    return page;
}

static void show_note_wizard(AppState *app, int view, double bx, double by)
{
    if (g_wizard_open) return;
    g_wizard_open = TRUE;

    WizardData *wd = g_malloc0(sizeof(WizardData));
    wd->app  = app;
    wd->view = view;
    wd->bx   = bx;
    wd->by   = by;

    for (int i = 0; i < 2; i++) {
        wd->c_q1[i] = (WBtnPair){ wd, i, 0 };
        wd->c_q2[i] = (WBtnPair){ wd, i, 1 };
    }
    for (int i = 0; i < NOTE_QUALITY_COUNT; i++)
        wd->c_q3[i] = (WBtnPair){ wd, i, 2 };
    for (int i = 0; i <= 10; i++) {
        wd->n_q4[i] = (WBtnPair){ wd, i, 3 };
        wd->n_q5[i] = (WBtnPair){ wd, i, 4 };
    }

    wd->window = gtk_window_new();
    gtk_widget_set_name(wd->window, "wiz-window");
    gtk_window_set_title(GTK_WINDOW(wd->window), "Note");
    gtk_window_set_transient_for(GTK_WINDOW(wd->window),
                                 GTK_WINDOW(app->window));
    gtk_window_set_modal(GTK_WINDOW(wd->window), TRUE);
    gtk_window_set_resizable(GTK_WINDOW(wd->window), FALSE);
    g_signal_connect(wd->window, "destroy",
                     G_CALLBACK(on_wizard_destroy), wd);

    wd->stack = gtk_stack_new();
    gtk_stack_set_transition_type(GTK_STACK(wd->stack),
                                  GTK_STACK_TRANSITION_TYPE_NONE);

    gtk_stack_add_named(GTK_STACK(wd->stack),
        wiz_page("Temporal pattern?",
                 wiz_choice_row(wd->c_q1, "Constant (C)", "Intermittent (Im)")),
        "q1");

    gtk_stack_add_named(GTK_STACK(wd->stack),
        wiz_page("Depth?",
                 wiz_choice_row(wd->c_q2, "Superficial (S)", "Deep (D)")),
        "q2");

    gtk_stack_add_named(GTK_STACK(wd->stack),
        wiz_page("Quality?",
                 wiz_quality_grid(wd->c_q3)),
        "q3");

    gtk_stack_add_named(GTK_STACK(wd->stack),
        wiz_page("Average intensity /10",
                 wiz_number_row(wd->n_q4)),
        "q4");

    gtk_stack_add_named(GTK_STACK(wd->stack),
        wiz_page("Worst intensity /10",
                 wiz_number_row(wd->n_q5)),
        "q5");

    gtk_stack_set_visible_child_name(GTK_STACK(wd->stack), "q1");
    gtk_window_set_child(GTK_WINDOW(wd->window), wd->stack);
    gtk_window_present(GTK_WINDOW(wd->window));
}

/* ── Build "Draw" tab content ────────────────────────────────────────────── */
static GtkWidget *build_draw_tab(AppState *app)
{
    GtkWidget *box = gtk_box_new(GTK_ORIENTATION_VERTICAL, 3);
    gtk_widget_set_name(box, "toolbar");
    gtk_widget_set_margin_start(box, 2);
    gtk_widget_set_margin_end(box, 2);
    gtk_widget_set_margin_top(box, 2);

    /* ── View section: 4-View full-width, then 2×2 grid ── */
    GtkWidget *lbl0 = gtk_label_new("View");
    gtk_widget_set_name(lbl0, "section-label");
    gtk_box_append(GTK_BOX(box), lbl0);

    static const char *layout_labels[] = { "4-View", "Ant", "Post", "Lat L", "Lat R" };
    static gpointer    layout_pairs[LAYOUT_COUNT][2];
    static gpointer    cycle_pairs[2][2];

    GtkWidget *view_grid = make_grid2col();

    /* 4-View full-width */
    {
        GtkWidget *btn = make_btn(layout_labels[0], -1, 34);
        gtk_widget_set_hexpand(btn, TRUE);
        gtk_widget_set_name(btn, "tool-btn-active");
        layout_pairs[0][0] = app;
        layout_pairs[0][1] = (gpointer)(gintptr)0;
        g_signal_connect(btn, "clicked", G_CALLBACK(on_layout_clicked), layout_pairs[0]);
        g_layout_btns[0] = btn;
        gtk_grid_attach(GTK_GRID(view_grid), btn, 0, 0, 2, 1);
    }
    /* Ant / Post single-view buttons */
    for (int i = 1; i <= 2; i++) {
        GtkWidget *btn = make_btn(layout_labels[i], -1, 34);
        gtk_widget_set_hexpand(btn, TRUE);
        gtk_widget_set_name(btn, "tool-btn");
        layout_pairs[i][0] = app;
        layout_pairs[i][1] = (gpointer)(gintptr)i;
        g_signal_connect(btn, "clicked", G_CALLBACK(on_layout_clicked), layout_pairs[i]);
        g_layout_btns[i] = btn;
        gtk_grid_attach(GTK_GRID(view_grid), btn, i - 1, 1, 1, 1);
    }
    /* Right column cycle buttons */
    for (int s = 0; s < 2; s++) {
        char lbl[20];
        snprintf(lbl, sizeof(lbl), "%s \xe2\x86\xbb",
                 canvas_view_short_name(app->right_slot_views[s]));
        GtkWidget *btn = make_btn(lbl, -1, 34);
        gtk_widget_set_hexpand(btn, TRUE);
        gtk_widget_set_name(btn, "tool-btn");
        cycle_pairs[s][0] = app;
        cycle_pairs[s][1] = (gpointer)(gintptr)s;
        g_signal_connect(btn, "clicked", G_CALLBACK(on_cycle_right_slot), cycle_pairs[s]);
        g_right_slot_btns[s] = btn;
        gtk_grid_attach(GTK_GRID(view_grid), btn, s, 2, 1, 1);
    }
    gtk_box_append(GTK_BOX(box), view_grid);

    gtk_box_append(GTK_BOX(box), gtk_separator_new(GTK_ORIENTATION_HORIZONTAL));

    /* ── Symptom section: 2-column grid ── */
    GtkWidget *lbl1 = gtk_label_new("Symptom");
    gtk_widget_set_name(lbl1, "section-label");
    gtk_box_append(GTK_BOX(box), lbl1);

    /* P&N=· (fine dots), Para=× (cross marks), Tick=✓ (symptom-free stamp) */
    static const char *sym_labels[] = {
        "Pain\n●", "Pain\n◌", "P&N\n·", "Numb\n≡", "Para\n×", "Tick\n✓"
    };
    static gpointer   sym_pairs[SYMPTOM_COUNT][2];

    GtkWidget *sym_grid = make_grid2col();
    for (int i = 0; i < SYMPTOM_COUNT; i++) {
        GtkWidget *btn = make_btn(sym_labels[i], -1, 40);
        gtk_widget_set_hexpand(btn, TRUE);
        gtk_widget_set_name(btn, "symptom-btn");
        sym_pairs[i][0] = app;
        sym_pairs[i][1] = (gpointer)(gintptr)i;
        g_signal_connect(btn, "clicked", G_CALLBACK(on_symptom_clicked), sym_pairs[i]);
        g_symptom_btns[i] = btn;
        gtk_grid_attach(GTK_GRID(sym_grid), btn, i % 2, i / 2, 1, 1);
    }

    /* Note tool button — full width, below symptoms */
    g_note_btn = make_btn("Note ✎", -1, 34);
    gtk_widget_set_hexpand(g_note_btn, TRUE);
    gtk_widget_set_name(g_note_btn, "tool-btn");
    g_signal_connect(g_note_btn, "clicked", G_CALLBACK(on_note_clicked), app);
    gtk_grid_attach(GTK_GRID(sym_grid), g_note_btn, 0, SYMPTOM_COUNT / 2, 2, 1);

    /* Arrow tool button — full width, below Note */
    g_arrow_btn = make_btn("Arrow →", -1, 34);
    gtk_widget_set_hexpand(g_arrow_btn, TRUE);
    gtk_widget_set_name(g_arrow_btn, "tool-btn");
    g_signal_connect(g_arrow_btn, "clicked", G_CALLBACK(on_arrow_clicked), app);
    gtk_grid_attach(GTK_GRID(sym_grid), g_arrow_btn, 0, SYMPTOM_COUNT / 2 + 1, 2, 1);

    gtk_box_append(GTK_BOX(box), sym_grid);

    gtk_box_append(GTK_BOX(box), gtk_separator_new(GTK_ORIENTATION_HORIZONTAL));

    /* ── Tools section: 2-column grid ── */
    GtkWidget *lbl2 = gtk_label_new("Tools");
    gtk_widget_set_name(lbl2, "section-label");
    gtk_box_append(GTK_BOX(box), lbl2);

    GtkWidget *tool_grid = make_grid2col();

    g_linemode_btn = make_btn(app->pen_wide_mode ? "Bold" : "Fine", -1, 34);
    gtk_widget_set_hexpand(g_linemode_btn, TRUE);
    gtk_widget_set_name(g_linemode_btn, app->pen_wide_mode ? "tool-btn-active" : "tool-btn");
    g_signal_connect(g_linemode_btn, "clicked", G_CALLBACK(on_linemode_clicked), app);
    gtk_grid_attach(GTK_GRID(tool_grid), g_linemode_btn, 0, 0, 1, 1);

    g_erase_btn = make_btn("Erase", -1, 34);
    gtk_widget_set_hexpand(g_erase_btn, TRUE);
    g_signal_connect(g_erase_btn, "clicked", G_CALLBACK(on_erase_clicked), app);
    gtk_grid_attach(GTK_GRID(tool_grid), g_erase_btn, 1, 0, 1, 1);

    GtkWidget *undo_btn = make_btn("Undo", -1, 34);
    gtk_widget_set_hexpand(undo_btn, TRUE);
    g_signal_connect(undo_btn, "clicked", G_CALLBACK(on_undo_clicked), app);
    gtk_grid_attach(GTK_GRID(tool_grid), undo_btn, 0, 1, 1, 1);

    GtkWidget *clear_btn = make_btn("Clear", -1, 34);
    gtk_widget_set_hexpand(clear_btn, TRUE);
    g_signal_connect(clear_btn, "clicked", G_CALLBACK(on_clear_clicked), app);
    gtk_grid_attach(GTK_GRID(tool_grid), clear_btn, 1, 1, 1, 1);

    g_link_btn = make_btn("Link", -1, 34);
    gtk_widget_set_hexpand(g_link_btn, TRUE);
    g_signal_connect(g_link_btn, "clicked", G_CALLBACK(on_link_clicked), app);
    gtk_grid_attach(GTK_GRID(tool_grid), g_link_btn, 0, 2, 2, 1);

    gtk_box_append(GTK_BOX(box), tool_grid);

    gtk_box_append(GTK_BOX(box), gtk_separator_new(GTK_ORIENTATION_HORIZONTAL));

    /* ── Overlay section: 2-column grid + compact nav ── */
    GtkWidget *lbl4 = gtk_label_new("Overlay");
    gtk_widget_set_name(lbl4, "section-label");
    gtk_box_append(GTK_BOX(box), lbl4);

    static const char *cat_labels[] = { "Derm", "Periph", "Somat" };
    static gpointer    cat_pairs[3][2];

    GtkWidget *ov_grid = make_grid2col();
    for (int i = 0; i < 2; i++) {
        GtkWidget *btn = make_btn(cat_labels[i], -1, 34);
        gtk_widget_set_hexpand(btn, TRUE);
        gtk_widget_set_name(btn, "overlay-btn");
        cat_pairs[i][0] = app;
        cat_pairs[i][1] = (gpointer)(gintptr)(i + 1);
        g_signal_connect(btn, "clicked", G_CALLBACK(on_overlay_cat_clicked), cat_pairs[i]);
        g_overlay_cat_btns[i] = btn;
        gtk_grid_attach(GTK_GRID(ov_grid), btn, i, 0, 1, 1);
    }
    g_overlay_cat_btns[2] = NULL;  /* Somatic button removed */
    gtk_box_append(GTK_BOX(box), ov_grid);

    g_overlay_label = gtk_label_new("Off");
    gtk_widget_set_name(g_overlay_label, "overlay-name");
    gtk_widget_set_hexpand(g_overlay_label, TRUE);
    gtk_label_set_wrap(GTK_LABEL(g_overlay_label), TRUE);
    gtk_label_set_justify(GTK_LABEL(g_overlay_label), GTK_JUSTIFY_CENTER);
    gtk_box_append(GTK_BOX(box), g_overlay_label);

    g_overlay_nav_box = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 2);
    GtkWidget *prev_btn = gtk_button_new_with_label("◀");
    GtkWidget *next_btn = gtk_button_new_with_label("▶");
    gtk_widget_set_size_request(prev_btn, 28, 30);
    gtk_widget_set_size_request(next_btn, 28, 30);
    g_signal_connect(prev_btn, "clicked", G_CALLBACK(on_overlay_prev), app);
    g_signal_connect(next_btn, "clicked", G_CALLBACK(on_overlay_next), app);
    gtk_box_append(GTK_BOX(g_overlay_nav_box), prev_btn);
    gtk_box_append(GTK_BOX(g_overlay_nav_box), next_btn);
    gtk_widget_set_visible(g_overlay_nav_box, FALSE);
    gtk_box_append(GTK_BOX(box), g_overlay_nav_box);

    GtkWidget *alpha_lbl = gtk_label_new("Opacity");
    gtk_widget_set_name(alpha_lbl, "section-label");
    gtk_box_append(GTK_BOX(box), alpha_lbl);

    GtkWidget *slider = gtk_scale_new_with_range(GTK_ORIENTATION_HORIZONTAL, 0.0, 1.0, 0.05);
    gtk_range_set_value(GTK_RANGE(slider), 0.5);
    gtk_scale_set_draw_value(GTK_SCALE(slider), FALSE);
    gtk_widget_set_hexpand(slider, TRUE);
    g_signal_connect(slider, "value-changed", G_CALLBACK(on_overlay_alpha), app);
    gtk_box_append(GTK_BOX(box), slider);

    GtkWidget *spacer = gtk_box_new(GTK_ORIENTATION_VERTICAL, 0);
    gtk_widget_set_vexpand(spacer, TRUE);
    gtk_box_append(GTK_BOX(box), spacer);

    return box;
}

/* ── Build "File" tab content ────────────────────────────────────────────── */
static GtkWidget *build_file_tab(void)
{
    GtkWidget *box = gtk_box_new(GTK_ORIENTATION_VERTICAL, 6);
    gtk_widget_set_margin_top(box, 6);
    gtk_widget_set_margin_start(box, 4);
    gtk_widget_set_margin_end(box, 4);

    GtkWidget *lbl = gtk_label_new("Save");
    gtk_widget_set_name(lbl, "section-label");
    gtk_box_append(GTK_BOX(box), lbl);

    GtkWidget *svg_btn = make_btn("SVG", 60, 44);
    g_signal_connect(svg_btn, "clicked", G_CALLBACK(on_save_svg), NULL);
    gtk_box_append(GTK_BOX(box), svg_btn);

    GtkWidget *png_btn = make_btn("PNG", 60, 44);
    g_signal_connect(png_btn, "clicked", G_CALLBACK(on_save_png), NULL);
    gtk_box_append(GTK_BOX(box), png_btn);

    GtkWidget *pdf_btn = make_btn("PDF", 60, 44);
    g_signal_connect(pdf_btn, "clicked", G_CALLBACK(on_save_pdf), NULL);
    gtk_box_append(GTK_BOX(box), pdf_btn);

    GtkWidget *spacer = gtk_box_new(GTK_ORIENTATION_VERTICAL, 0);
    gtk_widget_set_vexpand(spacer, TRUE);
    gtk_box_append(GTK_BOX(box), spacer);

    g_file_status = gtk_label_new("");
    gtk_widget_set_name(g_file_status, "file-status");
    gtk_label_set_wrap(GTK_LABEL(g_file_status), TRUE);
    gtk_label_set_justify(GTK_LABEL(g_file_status), GTK_JUSTIFY_CENTER);
    gtk_widget_set_margin_bottom(g_file_status, 6);
    gtk_box_append(GTK_BOX(box), g_file_status);

    return box;
}

/* ── Build tabbed sidebar ────────────────────────────────────────────────── */
static GtkWidget *build_sidebar(AppState *app)
{
    GtkWidget *outer = gtk_box_new(GTK_ORIENTATION_VERTICAL, 0);
    gtk_widget_set_name(outer, "sidebar");
    gtk_widget_set_size_request(outer, 110, -1);
    gtk_widget_set_hexpand(outer, FALSE);

    /* Tab bar */
    GtkWidget *tab_bar = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 0);
    gtk_widget_set_name(tab_bar, "tab-bar");

    static const char *tab_labels[N_TABS] = { "D", "F" };
    for (int i = 0; i < N_TABS; i++) {
        GtkWidget *btn = gtk_button_new_with_label(tab_labels[i]);
        gtk_widget_set_name(btn, "tab-btn");
        gtk_widget_set_hexpand(btn, TRUE);
        gtk_widget_set_size_request(btn, -1, 34);
        g_signal_connect(btn, "clicked", G_CALLBACK(on_tab_clicked),
                         (gpointer)(gintptr)i);
        g_tab_btns[i] = btn;
        gtk_box_append(GTK_BOX(tab_bar), btn);
    }
    gtk_box_append(GTK_BOX(outer), tab_bar);

    /* Tab content stack */
    g_tab_stack = gtk_stack_new();
    gtk_stack_set_transition_type(GTK_STACK(g_tab_stack),
                                  GTK_STACK_TRANSITION_TYPE_NONE);
    gtk_widget_set_vexpand(g_tab_stack, TRUE);

    /* Helper: wrap a child in a scrolled window and add to stack */
    #define ADD_TAB(child, name) \
    do { \
        GtkWidget *_sc = gtk_scrolled_window_new(); \
        gtk_scrolled_window_set_policy(GTK_SCROLLED_WINDOW(_sc), \
                                       GTK_POLICY_NEVER, GTK_POLICY_AUTOMATIC); \
        gtk_scrolled_window_set_has_frame(GTK_SCROLLED_WINDOW(_sc), FALSE); \
        gtk_scrolled_window_set_child(GTK_SCROLLED_WINDOW(_sc), (child)); \
        gtk_stack_add_named(GTK_STACK(g_tab_stack), _sc, (name)); \
    } while (0)

    ADD_TAB(build_draw_tab(app), "draw");
    ADD_TAB(build_file_tab(),    "file");

    #undef ADD_TAB

    gtk_box_append(GTK_BOX(outer), g_tab_stack);

    set_active_tab(0);
    return outer;
}

/* ── Public: create main window ─────────────────────────────────────────── */
void window_create(AppState *app, GtkApplication *gtk_app)
{
    g_app_ref = app;
    app->toolbar_update_cb    = update_toolbar_state;
    app->show_note_wizard_cb  = show_note_wizard;
    apply_css();

    app->window = gtk_application_window_new(gtk_app);
    gtk_window_set_title(GTK_WINDOW(app->window), "PhysioChart");
    gtk_window_set_default_size(GTK_WINDOW(app->window), 900, 700);
    gtk_window_maximize(GTK_WINDOW(app->window));

    GtkWidget *hbox = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 0);
    gtk_window_set_child(GTK_WINDOW(app->window), hbox);

    gtk_box_append(GTK_BOX(hbox), build_sidebar(app));

    GtkWidget *canvas = canvas_new(app);
    gtk_box_append(GTK_BOX(hbox), canvas);

    GtkEventController *key_ctrl = gtk_event_controller_key_new();
    gtk_widget_add_controller(app->window, key_ctrl);
    g_signal_connect(key_ctrl, "key-pressed",
                     G_CALLBACK(on_key_pressed), app);

    update_toolbar_state(app);
    gtk_window_present(GTK_WINDOW(app->window));
}
