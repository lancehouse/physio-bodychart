#pragma once
#include <cairo/cairo.h>

typedef struct _AppState AppState;   /* full definition in canvas.h */

#define MAX_OBJ_ZONES    60
#define MAX_OBJ_ZONE_PTS 512
#define MAX_OBJ_POINTS   60

typedef enum {
    OBJ_ZONE_ALLODYNIA    = 0,   /* yellow   #F5D100 */
    OBJ_ZONE_HYPERALGESIA,       /* orange   #F07820 */
    OBJ_ZONE_ERYTHEMA,           /* pink     #E8607A */
    OBJ_ZONE_TEMP_COOL,          /* cyan     #40A0E0 */
    OBJ_ZONE_TEMP_WARM,          /* deep-red #C03030 */
    OBJ_ZONE_COUNT
} ObjZoneType;

typedef enum {
    OBJ_POINT_PPT = 0,           /* Pressure Pain Threshold, kg/cm² */
    OBJ_POINT_TEMPORAL_SUM,      /* Temporal summation score, 0–10 */
    OBJ_POINT_COUNT
} ObjPointType;

typedef struct {
    float       *bx, *by;        /* body-space path (dynamic array) */
    int          n, cap;
    int          view;
    ObjZoneType  type;
} ObjZone;

typedef struct {
    double       bx, by;         /* body-space position */
    double       value;
    int          view;
    ObjPointType type;
    char         label[20];      /* e.g. "4.2" for PPT */
} ObjPoint;

typedef struct {
    float        r, g, b;
    const char  *name;
    const char  *short_name;     /* for sidebar button */
} ObjZoneDef;

extern const ObjZoneDef OBJ_ZONE_DEFS[OBJ_ZONE_COUNT];

ObjZone *obj_zone_new(ObjZoneType type, int view);
void     obj_zone_add_pt(ObjZone *z, float bx, float by);
void     obj_zone_free(ObjZone *z);

/* Render objective layer — called from canvas.c */
void obj_chart_render_body(AppState *app, cairo_t *cr, int view);
void obj_chart_render_screen(AppState *app, cairo_t *cr, int view,
                              double s, double cx, double cy);
void obj_chart_render_active_body(AppState *app, cairo_t *cr, int view);
