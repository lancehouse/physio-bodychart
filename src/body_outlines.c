#include "body_outlines.h"
#include "svg_views.h"
#include <math.h>

const char *VIEW_LABELS[VIEW_COUNT] = {
    "Anterior", "Posterior", "Right lateral", "Left lateral",
    "Hand (palmar)", "Hand (dorsal)", "Foot (plantar)", "Foot (dorsal)"
};

/* ── helpers ─────────────────────────────────────────────────────────────── */
static void move(cairo_t *cr, double x, double y) { cairo_move_to(cr, x, y); }
static void line(cairo_t *cr, double x, double y) { cairo_line_to(cr, x, y); }
static void curve(cairo_t *cr,
                  double x1, double y1, double x2, double y2,
                  double x3, double y3)
{ cairo_curve_to(cr, x1, y1, x2, y2, x3, y3); }

static void ellipse(cairo_t *cr, double cx, double cy, double rx, double ry)
{
    cairo_save(cr);
    cairo_translate(cr, cx, cy);
    cairo_scale(cr, rx, ry);
    cairo_arc(cr, 0, 0, 1, 0, 2 * M_PI);
    cairo_restore(cr);
}

/* ── Shared body silhouette (anterior-facing) ────────────────────────────── *
 * 200×400 unit space. Head top ~y=5, feet bottom ~y=396.                    *
 * Mirrored by draw_posterior via cairo_scale(-1,1).                         *
 * Does NOT include view-specific internal landmarks (clavicles, navel etc)  *
 * so those can be added cleanly per-view.                                   */
static void draw_body_silhouette(cairo_t *cr)
{
    /* ── Head ── */
    ellipse(cr, 100, 27, 17, 22);
    cairo_stroke(cr);

    /* ── Neck ── */
    move(cr, 92, 48);  curve(cr, 91,54, 90,60, 90,68);
    move(cr, 108, 48); curve(cr, 109,54, 110,60, 110,68);
    cairo_stroke(cr);

    /* ── Left torso silhouette: neck → shoulder → waist → hip → groin ── */
    move(cr, 90, 68);
    curve(cr, 78,70,  62,74,  54,82);    /* shoulder slope */
    curve(cr, 46,90,  42,100, 44,112);   /* deltoid → axilla */
    curve(cr, 46,124, 48,138, 50,152);   /* upper lateral trunk */
    curve(cr, 51,161, 52,169, 54,178);   /* waist */
    curve(cr, 57,187, 62,194, 70,200);   /* hip flare */
    curve(cr, 74,204, 79,210, 81,216);   /* inguinal → crotch */
    cairo_stroke(cr);

    /* ── Right torso silhouette ── */
    move(cr, 110, 68);
    curve(cr, 122,70,  138,74,  146,82);
    curve(cr, 154,90,  158,100, 156,112);
    curve(cr, 154,124, 152,138, 150,152);
    curve(cr, 149,161, 148,169, 146,178);
    curve(cr, 143,187, 138,194, 130,200);
    curve(cr, 126,204, 121,210, 119,216);
    cairo_stroke(cr);

    /* ── Crotch base ── */
    move(cr, 81, 216);
    curve(cr, 88,220, 94,222, 100,222);
    curve(cr, 106,222, 112,220, 119,216);
    cairo_stroke(cr);

    /* ── Left arm: outer edge ── */
    move(cr, 52, 90);
    curve(cr, 44,96,  38,108, 36,122);
    curve(cr, 34,136, 34,150, 36,166);
    curve(cr, 38,178, 36,192, 36,206);
    curve(cr, 36,216, 36,226, 36,234);
    cairo_stroke(cr);

    /* ── Left arm: inner edge ── */
    move(cr, 44, 112);
    curve(cr, 44,124, 44,138, 46,154);
    curve(cr, 48,168, 48,182, 48,196);
    curve(cr, 48,208, 48,220, 50,232);
    cairo_stroke(cr);

    /* ── Left hand (simplified palm blob) ── */
    move(cr, 36, 234);
    curve(cr, 32,242, 32,252, 36,260);
    curve(cr, 40,266, 46,268, 52,266);
    curve(cr, 58,264, 60,256, 58,248);
    curve(cr, 56,240, 50,234, 50,232);
    cairo_stroke(cr);

    /* ── Right arm: outer edge ── */
    move(cr, 148, 90);
    curve(cr, 156,96,  162,108, 164,122);
    curve(cr, 166,136, 166,150, 164,166);
    curve(cr, 162,178, 164,192, 164,206);
    curve(cr, 164,216, 164,226, 164,234);
    cairo_stroke(cr);

    /* ── Right arm: inner edge ── */
    move(cr, 156, 112);
    curve(cr, 156,124, 156,138, 154,154);
    curve(cr, 152,168, 152,182, 152,196);
    curve(cr, 152,208, 152,220, 150,232);
    cairo_stroke(cr);

    /* ── Right hand ── */
    move(cr, 164, 234);
    curve(cr, 168,242, 168,252, 164,260);
    curve(cr, 160,266, 154,268, 148,266);
    curve(cr, 142,264, 140,256, 142,248);
    curve(cr, 144,240, 150,234, 150,232);
    cairo_stroke(cr);

    /* ── Left leg: outer edge ── */
    move(cr, 70, 200);
    curve(cr, 67,216, 64,234, 63,252);
    curve(cr, 62,270, 62,286, 62,304);
    curve(cr, 62,312, 60,322, 60,338);
    curve(cr, 60,354, 60,368, 58,380);
    cairo_stroke(cr);

    /* ── Left leg: inner edge ── */
    move(cr, 81, 216);
    curve(cr, 81,230, 81,246, 81,264);
    curve(cr, 81,280, 80,294, 80,308);
    curve(cr, 80,318, 80,330, 80,346);
    curve(cr, 80,362, 78,374, 76,382);
    cairo_stroke(cr);

    /* ── Right leg: outer edge ── */
    move(cr, 130, 200);
    curve(cr, 133,216, 136,234, 137,252);
    curve(cr, 138,270, 138,286, 138,304);
    curve(cr, 138,312, 140,322, 140,338);
    curve(cr, 140,354, 140,368, 142,380);
    cairo_stroke(cr);

    /* ── Right leg: inner edge ── */
    move(cr, 119, 216);
    curve(cr, 119,230, 119,246, 119,264);
    curve(cr, 119,280, 120,294, 120,308);
    curve(cr, 120,318, 120,330, 120,346);
    curve(cr, 120,362, 122,374, 124,382);
    cairo_stroke(cr);

    /* ── Left foot ── */
    move(cr, 58, 380);
    curve(cr, 52,386, 46,394, 44,396);   /* outer ankle → lateral heel */
    curve(cr, 46,398, 56,398, 68,396);   /* heel → sole */
    curve(cr, 76,394, 82,388, 80,380);   /* sole → medial ankle */
    line(cr, 78, 380);
    cairo_stroke(cr);

    /* ── Right foot ── */
    move(cr, 142, 380);
    curve(cr, 148,386, 154,394, 156,396);
    curve(cr, 154,398, 144,398, 132,396);
    curve(cr, 124,394, 118,388, 120,380);
    line(cr, 122, 380);
    cairo_stroke(cr);
}

/* ── Anterior ────────────────────────────────────────────────────────────── */
static void draw_anterior(cairo_t *cr)
{
    draw_body_silhouette(cr);

    /* Clavicles */
    move(cr, 100, 72);
    curve(cr, 88,71, 74,72, 62,80);
    move(cr, 100, 72);
    curve(cr, 112,71, 126,72, 138,80);
    cairo_stroke(cr);

    /* Knee caps */
    ellipse(cr, 71, 308, 10, 7);
    cairo_stroke(cr);
    ellipse(cr, 129, 308, 10, 7);
    cairo_stroke(cr);

    /* Navel */
    cairo_arc(cr, 100, 158, 2.5, 0, 2 * M_PI);
    cairo_fill(cr);

    /* Midline dashed */
    double dashes[] = {4.0, 4.0};
    cairo_save(cr);
    cairo_set_dash(cr, dashes, 2, 0);
    cairo_set_line_width(cr, 0.6);
    move(cr, 100, 48); line(cr, 100, 218);
    cairo_stroke(cr);
    cairo_restore(cr);
}

/* ── Posterior ───────────────────────────────────────────────────────────── */
static void draw_posterior(cairo_t *cr)
{
    /* Mirror the shared silhouette */
    cairo_save(cr);
    cairo_translate(cr, 200, 0);
    cairo_scale(cr, -1, 1);
    draw_body_silhouette(cr);
    cairo_restore(cr);

    /* Spine dashed */
    double dashes[] = {4.0, 4.0};
    cairo_save(cr);
    cairo_set_dash(cr, dashes, 2, 0);
    cairo_set_line_width(cr, 0.6);
    move(cr, 100, 48); line(cr, 100, 210);
    cairo_stroke(cr);
    cairo_restore(cr);

    /* Left scapula */
    move(cr, 78, 82);
    curve(cr, 70,86,  64,96,  66,112);
    curve(cr, 68,122, 76,128, 86,126);
    curve(cr, 94,124, 96,114, 94,102);
    curve(cr, 92,90,  86,82,  78,82);
    cairo_stroke(cr);

    /* Right scapula (mirror of left) */
    move(cr, 122, 82);
    curve(cr, 130,86,  136,96,  134,112);
    curve(cr, 132,122, 124,128, 114,126);
    curve(cr, 106,124, 104,114, 106,102);
    curve(cr, 108,90,  114,82,  122,82);
    cairo_stroke(cr);

    /* Gluteal definition */
    move(cr, 100, 196);
    curve(cr, 94,204, 82,210, 76,220);
    move(cr, 100, 196);
    curve(cr, 106,204, 118,210, 124,220);
    cairo_stroke(cr);
}

/* ── Lateral views — sagittal profile with arm raised ───────────────────── *
 * flip=0: right lateral (anterior faces right / +x)                         *
 * flip=1: left lateral (mirrored)                                           */
static void draw_lateral(cairo_t *cr, int flip)
{
    cairo_save(cr);
    if (flip) {
        cairo_translate(cr, 200, 0);
        cairo_scale(cr, -1, 1);
    }

    /* ── Head (profile, slightly anterior-biased) ── */
    ellipse(cr, 106, 27, 16, 22);
    cairo_stroke(cr);

    /* ── Neck ── */
    move(cr, 114, 46); curve(cr, 116,54, 117,62, 116,70);   /* anterior */
    move(cr,  98, 46); curve(cr,  95,54,  93,62,  92,70);   /* posterior */
    cairo_stroke(cr);

    /* ── Anterior torso line ── */
    move(cr, 116, 70);
    curve(cr, 120,80,  124,92,  126,106);   /* chest forward */
    curve(cr, 127,118, 126,130, 124,144);   /* lower chest */
    curve(cr, 122,156, 120,166, 118,178);   /* abdomen */
    curve(cr, 116,188, 114,198, 112,210);   /* lower abdomen → pubis */
    cairo_stroke(cr);

    /* ── Posterior torso line (S-curve of spine) ── */
    move(cr, 92, 70);
    curve(cr,  88,82,  86,96,  88,112);     /* slight thoracic kyphosis */
    curve(cr,  90,126, 90,138, 88,152);     /* mid back */
    curve(cr,  86,164, 84,176, 86,190);     /* lumbar lordosis */
    curve(cr,  90,202, 96,212, 98,222);     /* sacrum → buttock */
    cairo_stroke(cr);

    /* ── Groin/upper thigh join ── */
    move(cr, 112, 210);
    curve(cr, 110,218, 108,224, 106,228);
    move(cr, 98, 222);
    curve(cr, 100,228, 102,230, 104,232);
    cairo_stroke(cr);

    /* ── Raised arm (alongside head, outer edge) ── */
    move(cr, 124, 92);
    curve(cr, 130,76,  130,56,  126,38);
    curve(cr, 123,24,  118,12,  114, 4);
    cairo_stroke(cr);

    /* ── Raised arm (inner edge) ── */
    move(cr, 116, 88);
    curve(cr, 120,72,  120,52,  116,36);
    curve(cr, 113,22,  110,12,  107, 6);
    cairo_stroke(cr);

    /* ── Hand at top of raised arm ── */
    move(cr, 107, 6);
    curve(cr, 106,2,  110,0,  114,3);
    curve(cr, 117,6,  116,10, 114, 4);
    cairo_stroke(cr);

    /* ── Anterior leg ── */
    move(cr, 106, 228);
    curve(cr, 108,244, 110,260, 110,278);
    curve(cr, 110,294, 108,308, 108,322);   /* anterior knee */
    curve(cr, 108,336, 108,352, 106,366);
    curve(cr, 104,374, 104,380, 106,386);
    cairo_stroke(cr);

    /* ── Posterior leg (calf bulge) ── */
    move(cr, 98, 222);
    curve(cr,  94,238,  90,256,  88,274);
    curve(cr,  86,290,  88,306,  90,318);   /* popliteal crease */
    curve(cr,  92,328,  94,338,  92,354);
    curve(cr,  90,366,  88,376,  90,384);   /* calf → achilles */
    cairo_stroke(cr);

    /* ── Foot (lateral profile) ── */
    move(cr, 106, 386);
    curve(cr, 110,392, 116,396, 124,397);   /* dorsum → toes */
    curve(cr, 130,398, 134,396, 132,392);
    curve(cr, 124,394, 108,394,  96,390);   /* sole */
    curve(cr,  90,387,  88,382,  90,384);
    cairo_stroke(cr);

    cairo_restore(cr);
}

/* ── Hand palmar ─────────────────────────────────────────────────────────── */
static void draw_hand_palmar(cairo_t *cr)
{
    /* Palm */
    move(cr, 76, 226);
    curve(cr, 70,206, 68,182, 70,164);
    curve(cr, 72,148, 76,138, 84,132);
    curve(cr, 92,126, 102,126, 110,132);
    curve(cr, 118,138, 122,148, 124,164);
    curve(cr, 126,182, 126,206, 120,226);
    line(cr, 76, 226);
    cairo_stroke(cr);

    /* Thumb */
    move(cr, 72, 174);
    curve(cr, 60,166, 50,156, 44,146);
    curve(cr, 40,138, 42,130, 48,126);
    curve(cr, 54,122, 62,124, 66,134);
    curve(cr, 70,144, 70,158, 72,170);
    cairo_stroke(cr);

    /* Index finger */
    move(cr, 82, 132);
    curve(cr, 80,116, 78,100, 80,86);
    curve(cr, 82,74, 88,70, 94,70);
    curve(cr, 100,70, 104,74, 104,86);
    curve(cr, 106,100, 104,116, 102,132);
    cairo_stroke(cr);

    /* Middle finger */
    move(cr, 96, 130);
    curve(cr, 94,112, 92,94, 94,78);
    curve(cr, 96,66, 102,62, 108,62);
    curve(cr, 114,62, 118,66, 118,78);
    curve(cr, 120,94, 118,112, 116,130);
    cairo_stroke(cr);

    /* Ring finger */
    move(cr, 108, 132);
    curve(cr, 106,116, 106,100, 108,86);
    curve(cr, 110,74, 116,70, 122,70);
    curve(cr, 128,70, 132,74, 132,86);
    curve(cr, 134,100, 132,116, 130,132);
    cairo_stroke(cr);

    /* Little finger */
    move(cr, 120, 138);
    curve(cr, 120,124, 120,112, 122,100);
    curve(cr, 124,90, 128,86, 134,86);
    curve(cr, 140,86, 142,90, 142,100);
    curve(cr, 144,112, 142,126, 140,138);
    cairo_stroke(cr);

    /* Wrist crease */
    double dashes[] = {3.0, 3.0};
    cairo_save(cr);
    cairo_set_dash(cr, dashes, 2, 0);
    cairo_set_line_width(cr, 0.5);
    move(cr, 74, 228);
    curve(cr, 88,234, 112,234, 124,228);
    cairo_stroke(cr);
    cairo_restore(cr);
}

/* ── Hand dorsal — mirror of palmar with knuckle marks ─────────────────── */
static void draw_hand_dorsal(cairo_t *cr)
{
    cairo_save(cr);
    cairo_translate(cr, 200, 0);
    cairo_scale(cr, -1, 1);
    draw_hand_palmar(cr);
    cairo_restore(cr);

    /* Knuckle arcs */
    for (int i = 0; i < 4; i++) {
        double kx = 94 + i * 12;
        double ky = 132;
        cairo_save(cr);
        cairo_translate(cr, kx, ky);
        cairo_scale(cr, 5, 3);
        cairo_arc(cr, 0, 0, 1, M_PI, 2 * M_PI);
        cairo_restore(cr);
        cairo_stroke(cr);
    }
}

/* ── Foot plantar ────────────────────────────────────────────────────────── */
static void draw_foot_plantar(cairo_t *cr)
{
    /* Heel */
    ellipse(cr, 100, 362, 28, 22);
    cairo_stroke(cr);

    /* Medial and lateral arches */
    move(cr, 72, 344);
    curve(cr, 70,316, 72,288, 78,264);
    curve(cr, 82,248, 88,236, 96,230);
    curve(cr, 104,224, 114,224, 120,230);
    curve(cr, 128,238, 132,252, 134,268);
    curve(cr, 136,288, 134,316, 130,342);
    cairo_stroke(cr);

    /* Big toe */
    move(cr, 96, 230);
    curve(cr, 92,216, 90,200, 92,188);
    curve(cr, 94,178, 100,174, 106,174);
    curve(cr, 112,174, 116,178, 116,188);
    curve(cr, 118,200, 116,216, 114,230);
    cairo_stroke(cr);

    /* Toes 2–5 */
    double tx[] = { 110, 118, 124, 130 };
    double ty[] = { 232, 238, 246, 254 };
    for (int i = 0; i < 4; i++) {
        move(cr, tx[i], ty[i]);
        curve(cr, tx[i]+2, ty[i]-18, tx[i]+4, ty[i]-30, tx[i]+2, ty[i]-38);
        curve(cr, tx[i],   ty[i]-44, tx[i]-4, ty[i]-46, tx[i]-6, ty[i]-42);
        curve(cr, tx[i]-8, ty[i]-36, tx[i]-6, ty[i]-24, tx[i]-4, ty[i]-12);
        cairo_stroke(cr);
    }
}

/* ── Foot dorsal — mirror of plantar ────────────────────────────────────── */
static void draw_foot_dorsal(cairo_t *cr)
{
    cairo_save(cr);
    cairo_translate(cr, 200, 0);
    cairo_scale(cr, -1, 1);
    draw_foot_plantar(cr);
    cairo_restore(cr);
}

/* ── Public API ──────────────────────────────────────────────────────────── */
void body_outline_draw(cairo_t *cr, BodyView view)
{
    if (svg_view_available(view)) {
        svg_view_draw(cr, view);
        return;
    }

    cairo_set_line_cap(cr, CAIRO_LINE_CAP_ROUND);
    cairo_set_line_join(cr, CAIRO_LINE_JOIN_ROUND);
    cairo_set_line_width(cr, 1.8);

    switch (view) {
        case VIEW_ANTERIOR:     draw_anterior(cr);        break;
        case VIEW_POSTERIOR:    draw_posterior(cr);       break;
        case VIEW_LATERAL_R:    draw_lateral(cr, 0);      break;
        case VIEW_LATERAL_L:    draw_lateral(cr, 1);      break;
        case VIEW_HAND_PALMAR:  draw_hand_palmar(cr);     break;
        case VIEW_HAND_DORSAL:  draw_hand_dorsal(cr);     break;
        case VIEW_FOOT_PLANTAR: draw_foot_plantar(cr);    break;
        case VIEW_FOOT_DORSAL:  draw_foot_dorsal(cr);     break;
        default: break;
    }
}

float body_outline_aspect(BodyView view)
{
    switch (view) {
        case VIEW_HAND_PALMAR:
        case VIEW_HAND_DORSAL:  return 0.6f;
        case VIEW_FOOT_PLANTAR:
        case VIEW_FOOT_DORSAL:  return 0.5f;
        default:                return 0.5f;
    }
}
