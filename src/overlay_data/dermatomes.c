#include "../overlays.h"

/* ── Dermatome overlay path data ────────────────────────────────────────── *
 * Paths are in the 200×400 unit coordinate space matching body_outlines.c
 * Colours use a spectral scheme: cervical=warm, thoracic=mid, lumbar=cool, sacral=purple
 * These are clinically-approximate initial paths — refine over time.
 * ─────────────────────────────────────────────────────────────────────────── */

const OverlayDef DERMATOME_OVERLAYS[] = {
    {
        .id          = "C4",
        .label       = "C4 dermatome",
        .short_label = "C4",
        .category    = OVERLAY_DERMATOME,
        .r = 0.90f, .g = 0.30f, .b = 0.20f,
        /* Anterior: cape distribution over shoulders */
        .path_anterior =
            "M 88 72 C 74 74 58 78 52 86 C 48 92 50 98 56 100 "
            "C 66 104 80 104 88 100 C 96 96 100 90 100 86 "
            "C 100 90 104 96 112 100 C 120 104 134 104 144 100 "
            "C 150 98 152 92 148 86 C 142 78 126 74 112 72 Z",
        .path_posterior =
            "M 88 72 C 74 74 56 80 50 90 C 46 98 50 106 58 108 "
            "C 70 112 84 110 90 104 C 96 98 100 90 100 86 "
            "C 100 90 104 98 110 104 C 116 110 130 112 142 108 "
            "C 150 106 154 98 150 90 C 144 80 126 74 112 72 Z",
        .path_lateral_r = NULL,
        .path_lateral_l = NULL,
        .path_hand      = NULL,
        .path_foot      = NULL,
    },
    {
        .id          = "C5",
        .label       = "C5 dermatome",
        .short_label = "C5",
        .category    = OVERLAY_DERMATOME,
        .r = 0.92f, .g = 0.45f, .b = 0.15f,
        /* Lateral shoulder and upper arm */
        .path_anterior =
            "M 54 92 C 46 96 40 104 38 116 C 36 126 38 136 44 142 "
            "C 50 148 58 148 64 144 C 70 140 72 132 72 122 "
            "C 72 112 70 104 66 98 Z "
            "M 146 92 C 154 96 160 104 162 116 C 164 126 162 136 156 142 "
            "C 150 148 142 148 136 144 C 130 140 128 132 128 122 "
            "C 128 112 130 104 134 98 Z",
        .path_posterior =
            "M 54 92 C 44 98 38 108 38 120 C 38 132 44 142 52 146 "
            "C 58 148 64 146 68 140 C 72 134 72 124 70 114 Z "
            "M 146 92 C 156 98 162 108 162 120 C 162 132 156 142 148 146 "
            "C 142 148 136 146 132 140 C 128 134 128 124 130 114 Z",
        .path_hand      = NULL,
        .path_foot      = NULL,
    },
    {
        .id          = "C6",
        .label       = "C6 dermatome",
        .short_label = "C6",
        .category    = OVERLAY_DERMATOME,
        .r = 0.95f, .g = 0.65f, .b = 0.10f,
        /* Radial forearm, thumb and index finger */
        .path_anterior =
            "M 66 130 C 58 138 52 150 50 162 C 48 174 50 184 54 190 "
            "C 56 196 60 200 64 202 C 66 204 68 212 66 216 "
            "C 64 220 60 222 58 218 C 54 212 50 206 48 200 "
            "C 44 190 44 178 48 166 C 52 152 58 140 66 130 Z",
        .path_posterior = NULL,
        .path_hand =
            "M 80 200 C 74 194 70 184 70 174 C 70 164 74 156 80 150 "
            "C 86 144 96 142 104 142 C 112 142 118 146 120 152 "
            "C 118 148 112 144 104 144 C 96 144 88 148 84 154 "
            "C 80 162 80 172 82 180 Z",
        .path_foot = NULL,
    },
    {
        .id          = "C7",
        .label       = "C7 dermatome",
        .short_label = "C7",
        .category    = OVERLAY_DERMATOME,
        .r = 0.80f, .g = 0.80f, .b = 0.10f,
        /* Middle finger, mid-forearm */
        .path_anterior =
            "M 48 160 C 46 170 46 180 48 190 C 50 198 54 202 58 202 "
            "C 62 200 62 194 60 186 C 58 176 56 166 56 158 Z",
        .path_posterior = NULL,
        .path_hand =
            "M 94 130 C 92 114 92 96 94 80 C 96 68 100 64 106 64 "
            "C 112 64 116 68 116 80 C 118 96 116 114 114 130 Z",
        .path_foot = NULL,
    },
    {
        .id          = "C8",
        .label       = "C8 dermatome",
        .short_label = "C8",
        .category    = OVERLAY_DERMATOME,
        .r = 0.50f, .g = 0.80f, .b = 0.20f,
        /* Ulnar forearm, little finger */
        .path_anterior =
            "M 50 164 C 50 178 52 192 56 202 C 60 210 64 212 68 210 "
            "C 72 206 72 198 70 190 C 68 180 66 168 66 158 Z",
        .path_posterior = NULL,
        .path_hand =
            "M 118 138 C 118 124 118 112 120 100 C 122 90 126 86 132 86 "
            "C 138 86 140 90 140 100 C 142 112 140 126 138 138 Z",
        .path_foot = NULL,
    },
    {
        .id          = "T4",
        .label       = "T4 dermatome",
        .short_label = "T4",
        .category    = OVERLAY_DERMATOME,
        .r = 0.20f, .g = 0.75f, .b = 0.40f,
        /* Band across chest at nipple level */
        .path_anterior =
            "M 52 116 C 60 114 72 112 84 112 C 96 112 100 114 100 114 "
            "C 100 114 104 112 116 112 C 128 112 140 114 148 116 "
            "L 148 124 C 140 122 128 120 116 120 C 104 120 100 122 100 122 "
            "C 100 122 96 120 84 120 C 72 120 60 122 52 124 Z",
        .path_posterior =
            "M 52 116 L 148 116 L 148 126 L 52 126 Z",
        .path_hand = NULL,
        .path_foot = NULL,
    },
    {
        .id          = "T10",
        .label       = "T10 dermatome",
        .short_label = "T10",
        .category    = OVERLAY_DERMATOME,
        .r = 0.10f, .g = 0.65f, .b = 0.55f,
        /* Band at umbilicus */
        .path_anterior =
            "M 54 148 L 146 148 L 146 158 L 54 158 Z",
        .path_posterior =
            "M 54 148 L 146 148 L 146 158 L 54 158 Z",
        .path_hand = NULL,
        .path_foot = NULL,
    },
    {
        .id          = "L2",
        .label       = "L2 dermatome",
        .short_label = "L2",
        .category    = OVERLAY_DERMATOME,
        .r = 0.15f, .g = 0.45f, .b = 0.85f,
        /* Anterior upper thigh */
        .path_anterior =
            "M 82 200 C 78 210 76 222 76 234 C 76 242 78 248 82 250 "
            "C 86 252 92 250 96 244 C 100 238 100 228 100 218 "
            "C 100 208 100 200 100 200 C 96 200 90 200 82 200 Z "
            "M 118 200 C 122 210 124 222 124 234 C 124 242 122 248 118 250 "
            "C 114 252 108 250 104 244 C 100 238 100 228 100 218 "
            "C 100 208 100 200 100 200 C 104 200 110 200 118 200 Z",
        .path_posterior = NULL,
        .path_hand = NULL,
        .path_foot = NULL,
    },
    {
        .id          = "L3",
        .label       = "L3 dermatome",
        .short_label = "L3",
        .category    = OVERLAY_DERMATOME,
        .r = 0.22f, .g = 0.55f, .b = 0.95f,
        /* Anterior mid-thigh, medial knee */
        .path_anterior =
            "M 78 248 C 76 262 76 276 78 288 C 80 298 84 304 90 306 "
            "C 96 308 102 304 104 296 C 106 286 106 272 104 258 "
            "C 102 246 100 240 100 240 C 98 248 94 254 88 254 Z "
            "M 122 248 C 124 262 124 276 122 288 C 120 298 116 304 110 306 "
            "C 104 308 98 304 96 296 C 94 286 94 272 96 258 "
            "C 98 246 100 240 100 240 C 102 248 106 254 112 254 Z",
        .path_posterior = NULL,
        .path_hand = NULL,
        .path_foot = NULL,
    },
    {
        .id          = "L4",
        .label       = "L4 dermatome",
        .short_label = "L4",
        .category    = OVERLAY_DERMATOME,
        .r = 0.40f, .g = 0.40f, .b = 0.95f,
        /* Medial lower leg, medial foot */
        .path_anterior =
            "M 84 300 C 82 316 82 330 84 344 C 86 356 88 364 90 372 "
            "C 88 376 84 380 80 382 C 72 384 66 382 64 376 "
            "C 68 372 72 366 74 358 C 76 346 76 332 76 318 "
            "C 76 306 78 298 82 296 Z",
        .path_posterior = NULL,
        .path_foot =
            "M 70 340 C 68 320 70 298 76 280 C 78 272 82 268 88 268 "
            "C 94 270 96 278 96 288 C 96 308 92 330 88 348 Z",
    },
    {
        .id          = "L5",
        .label       = "L5 dermatome",
        .short_label = "L5",
        .category    = OVERLAY_DERMATOME,
        .r = 0.60f, .g = 0.30f, .b = 0.90f,
        /* Lateral lower leg, dorsum of foot, first web space */
        .path_anterior =
            "M 92 300 C 90 318 90 334 90 350 C 90 362 90 372 88 378 "
            "C 86 382 84 384 82 384 C 80 384 78 380 76 374 "
            "C 78 366 82 356 84 344 C 86 330 86 314 86 298 Z "
            "M 110 300 C 112 318 112 334 112 350 C 112 362 112 372 114 378 "
            "C 116 382 118 384 120 384 C 122 384 124 380 124 374 "
            "C 122 366 118 356 116 344 C 114 330 114 314 114 298 Z",
        .path_posterior =
            "M 92 300 C 90 320 90 340 92 358 C 94 372 96 380 98 384 "
            "C 96 386 92 386 90 382 C 86 374 84 360 84 344 "
            "C 82 326 84 308 88 296 Z",
        .path_foot =
            "M 94 224 C 90 210 88 196 90 186 C 92 178 98 174 104 174 "
            "C 110 174 114 178 114 186 C 116 196 114 210 112 224 Z "
            "M 108 226 C 108 210 110 196 114 184 C 116 176 120 174 126 176 "
            "C 130 180 130 190 128 202 Z",
    },
    {
        .id          = "S1",
        .label       = "S1 dermatome",
        .short_label = "S1",
        .category    = OVERLAY_DERMATOME,
        .r = 0.75f, .g = 0.20f, .b = 0.70f,
        /* Posterior lower leg, lateral heel and foot */
        .path_anterior =
            "M 80 378 C 76 382 72 390 70 396 C 74 398 84 398 90 394 "
            "C 90 388 90 380 88 376 Z "
            "M 120 378 C 124 382 128 390 130 396 C 126 398 116 398 110 394 "
            "C 110 388 110 380 112 376 Z",
        .path_posterior =
            "M 90 320 C 88 338 88 356 90 370 C 92 380 94 386 96 390 "
            "C 98 392 100 392 102 390 C 104 386 106 380 108 370 "
            "C 110 356 110 338 108 320 Z",
        .path_foot =
            "M 130 338 C 130 318 128 298 124 282 C 120 270 114 266 108 268 "
            "C 102 270 100 280 100 294 C 100 314 104 336 110 352 Z",
    },
    {
        .id          = "S2",
        .label       = "S2 dermatome",
        .short_label = "S2",
        .category    = OVERLAY_DERMATOME,
        .r = 0.85f, .g = 0.15f, .b = 0.50f,
        /* Posterior thigh midline, popliteal fossa */
        .path_anterior = NULL,
        .path_posterior =
            "M 92 240 C 90 260 90 280 92 298 C 94 312 96 320 100 322 "
            "C 104 320 106 312 108 298 C 110 280 110 260 108 240 Z",
        .path_hand = NULL,
        .path_foot = NULL,
    },
};

int DERMATOME_COUNT = sizeof(DERMATOME_OVERLAYS) / sizeof(DERMATOME_OVERLAYS[0]);
