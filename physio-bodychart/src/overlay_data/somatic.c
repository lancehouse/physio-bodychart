#include "../overlays.h"

const OverlayDef SOMATIC_OVERLAYS[] = {
    {
        .id = "disc_L4_5",
        .label = "Discogenic L4/5 referral",
        .short_label = "L4/5 disc",
        .category = OVERLAY_SOMATIC,
        .r = 0.85f, .g = 0.55f, .b = 0.10f,
        /* Diffuse low back, posterior thigh, lateral lower leg */
        .path_anterior = NULL,
        .path_posterior =
            "M 72 176 C 68 186 66 198 68 208 C 70 218 76 224 84 226 "
            "C 92 228 100 224 108 220 C 116 224 124 228 132 226 "
            "C 140 224 146 218 148 208 C 150 198 148 186 144 176 "
            "C 136 172 124 170 112 170 C 100 170 88 172 80 176 Z "
            "M 88 226 C 86 244 86 262 88 280 C 90 294 94 302 100 304 "
            "C 106 302 110 294 112 280 C 114 262 114 244 112 226 Z",
        .path_hand = NULL,
        .path_foot = NULL,
    },
    {
        .id = "disc_L5_S1",
        .label = "Discogenic L5/S1 referral",
        .short_label = "L5/S1 disc",
        .category = OVERLAY_SOMATIC,
        .r = 0.80f, .g = 0.35f, .b = 0.15f,
        /* Low back, posterior thigh, calf, heel */
        .path_anterior = NULL,
        .path_posterior =
            "M 76 182 C 72 194 72 208 76 220 C 80 228 88 232 100 232 "
            "C 112 232 120 228 124 220 C 128 208 128 194 124 182 "
            "C 116 178 108 176 100 176 C 92 176 84 178 76 182 Z "
            "M 90 232 C 88 252 88 272 90 292 C 92 308 96 318 100 320 "
            "C 104 318 108 308 110 292 C 112 272 112 252 110 232 Z "
            "M 92 320 C 90 338 90 354 92 366 C 94 374 98 378 102 376 "
            "C 106 374 108 368 108 358 C 108 344 106 328 104 316 Z",
        .path_hand = NULL,
        .path_foot =
            "M 100 338 C 98 318 98 298 102 282 C 104 272 108 268 114 270 "
            "C 120 274 122 286 122 300 C 122 318 118 338 114 352 Z",
    },
    {
        .id = "facet_L4_5",
        .label = "L4/5 facet joint referral",
        .short_label = "L4/5 facet",
        .category = OVERLAY_SOMATIC,
        .r = 0.65f, .g = 0.65f, .b = 0.15f,
        /* Diffuse low back, gluteal, does NOT go below knee */
        .path_anterior = NULL,
        .path_posterior =
            "M 70 170 C 66 182 64 196 66 208 C 68 220 76 228 88 230 "
            "C 96 232 100 230 104 228 C 108 230 112 232 120 230 "
            "C 132 228 140 220 142 208 C 144 196 142 182 138 170 "
            "C 128 166 116 164 104 164 C 92 164 80 166 70 170 Z "
            "M 80 230 C 76 244 74 256 76 266 C 78 274 84 278 90 276 "
            "C 96 274 100 268 100 260 C 100 268 104 274 110 276 "
            "C 116 278 122 274 124 266 C 126 256 124 244 120 230 Z",
        .path_hand = NULL,
        .path_foot = NULL,
    },
    {
        .id = "sij_referral",
        .label = "SIJ referral zone",
        .short_label = "SIJ",
        .category = OVERLAY_SOMATIC,
        .r = 0.70f, .g = 0.30f, .b = 0.30f,
        /* Posterior iliac region, gluteal, posterior thigh to knee */
        .path_anterior = NULL,
        .path_posterior =
            "M 68 176 C 62 186 60 198 62 210 C 64 222 72 230 82 232 "
            "C 90 234 96 230 100 224 "
            "C 80 222 70 212 68 200 C 66 188 70 178 76 174 Z "
            "M 116 174 C 122 178 126 188 124 200 C 122 212 112 222 100 224 "
            "C 104 230 110 234 118 232 C 128 230 136 222 138 210 "
            "C 140 198 138 186 132 176 Z "
            "M 86 232 C 84 250 84 268 86 284 C 88 296 92 302 98 302 "
            "C 102 302 106 296 108 284 C 110 268 110 250 108 232 Z",
        .path_hand = NULL,
        .path_foot = NULL,
    },
    {
        .id = "cervical_disc_C5_6",
        .label = "Cervical disc C5/6 referral",
        .short_label = "C5/6 disc",
        .category = OVERLAY_SOMATIC,
        .r = 0.88f, .g = 0.60f, .b = 0.25f,
        /* Neck, shoulder, upper arm */
        .path_anterior =
            "M 88 72 C 80 76 72 80 64 86 C 56 92 52 100 54 108 "
            "C 56 116 62 120 70 120 C 76 120 82 116 86 110 "
            "C 90 104 90 96 88 88 Z "
            "M 112 72 C 120 76 128 80 136 86 C 144 92 148 100 146 108 "
            "C 144 116 138 120 130 120 C 124 120 118 116 114 110 "
            "C 110 104 110 96 112 88 Z "
            "M 54 108 C 48 114 44 122 44 132 C 44 140 48 146 54 148 "
            "C 58 148 62 144 64 138 C 66 130 66 120 64 112 Z",
        .path_posterior =
            "M 88 72 C 78 78 68 84 60 92 C 54 98 52 108 56 116 "
            "C 60 122 68 124 76 122 C 84 120 88 112 88 104 Z "
            "M 112 72 C 122 78 132 84 140 92 C 146 98 148 108 144 116 "
            "C 140 122 132 124 124 122 C 116 120 112 112 112 104 Z",
        .path_hand = NULL,
        .path_foot = NULL,
    },
    {
        .id = "trigger_upper_trap",
        .label = "Upper trapezius trigger point",
        .short_label = "Upper trap TP",
        .category = OVERLAY_SOMATIC,
        .r = 0.75f, .g = 0.45f, .b = 0.70f,
        /* Head, neck, temple referral */
        .path_anterior =
            "M 86 36 C 82 30 78 26 78 22 C 78 18 84 16 100 16 "
            "C 116 16 122 18 122 22 C 122 26 118 30 114 36 "
            "C 110 40 106 44 100 46 C 94 44 90 40 86 36 Z "
            "M 88 72 C 80 76 74 80 68 86 C 62 90 58 96 60 102 "
            "C 64 108 72 110 80 108 C 88 106 92 100 92 92 Z",
        .path_posterior =
            "M 88 72 C 80 76 72 82 66 88 C 60 94 58 102 62 108 "
            "C 66 114 74 116 82 112 C 90 108 94 100 92 90 Z",
        .path_hand = NULL,
        .path_foot = NULL,
    },
};

int SOMATIC_COUNT = sizeof(SOMATIC_OVERLAYS) / sizeof(SOMATIC_OVERLAYS[0]);
