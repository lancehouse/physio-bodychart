#include "../overlays.h"

const OverlayDef PERIPHERAL_OVERLAYS[] = {
    {
        .id = "median", .label = "Median nerve", .short_label = "Median",
        .category = OVERLAY_PERIPHERAL,
        .r = 0.10f, .g = 0.65f, .b = 0.80f,
        .path_anterior =
            "M 50 164 C 48 178 48 192 50 204 C 52 212 56 216 60 216 "
            "C 62 214 62 208 60 200 C 58 190 56 178 56 166 Z",
        .path_posterior = NULL,
        .path_hand =
            /* Palmar: thumb, index, middle, radial half of ring */
            "M 78 220 C 74 210 70 196 70 182 C 70 170 74 162 80 158 "
            "C 84 156 90 158 92 164 C 94 172 92 184 90 196 "
            "C 88 208 86 218 84 224 Z "
            "M 84 132 C 82 118 80 102 82 88 C 84 76 90 72 96 72 "
            "C 102 72 106 76 106 88 C 108 102 106 118 104 132 Z "
            "M 96 130 C 94 114 92 96 94 80 C 96 68 100 64 106 64 "
            "C 112 64 116 68 116 80 C 118 96 116 114 114 130 Z",
        .path_foot = NULL,
    },
    {
        .id = "ulnar", .label = "Ulnar nerve", .short_label = "Ulnar",
        .category = OVERLAY_PERIPHERAL,
        .r = 0.80f, .g = 0.50f, .b = 0.10f,
        .path_anterior =
            "M 56 168 C 54 182 54 196 56 208 C 58 216 62 220 66 218 "
            "C 70 214 70 206 68 196 C 66 184 64 170 64 160 Z",
        .path_posterior = NULL,
        .path_hand =
            /* Ulnar: little and ring fingers, hypothenar */
            "M 118 138 C 118 124 118 112 120 100 C 122 90 126 86 132 86 "
            "C 138 86 140 90 140 100 C 142 112 140 124 138 138 Z "
            "M 108 132 C 106 116 106 100 108 86 C 110 74 114 70 120 70 "
            "C 126 70 130 74 130 86 C 132 100 130 116 128 132 Z "
            "M 122 220 C 124 210 128 198 130 184 C 130 172 126 164 120 162 "
            "C 114 162 110 170 110 182 C 110 196 114 210 118 220 Z",
        .path_foot = NULL,
    },
    {
        .id = "radial", .label = "Radial nerve", .short_label = "Radial",
        .category = OVERLAY_PERIPHERAL,
        .r = 0.85f, .g = 0.75f, .b = 0.10f,
        .path_anterior =
            "M 38 112 C 36 126 36 140 38 152 C 40 160 44 164 48 162 "
            "C 52 160 54 152 54 142 C 54 130 52 118 50 110 Z",
        .path_posterior =
            "M 38 112 C 36 126 36 142 40 154 C 44 162 50 164 56 160 "
            "C 60 156 60 146 58 134 C 56 120 52 108 46 104 Z",
        .path_hand =
            /* Dorsal: radial side */
            "M 80 200 C 76 188 72 174 72 162 C 72 152 76 146 82 144 "
            "C 88 142 96 146 98 154 C 100 162 98 176 96 190 Z",
        .path_foot = NULL,
    },
    {
        .id = "femoral", .label = "Femoral nerve", .short_label = "Femoral",
        .category = OVERLAY_PERIPHERAL,
        .r = 0.20f, .g = 0.78f, .b = 0.45f,
        .path_anterior =
            /* Anterior thigh */
            "M 82 200 C 78 216 76 232 76 248 C 76 262 78 272 84 278 "
            "C 90 284 98 282 102 274 C 106 264 106 248 104 232 "
            "C 102 216 100 204 100 200 C 96 200 88 200 82 200 Z "
            "M 118 200 C 122 216 124 232 124 248 C 124 262 122 272 116 278 "
            "C 110 284 102 282 98 274 C 94 264 94 248 96 232 "
            "C 98 216 100 204 100 200 C 104 200 112 200 118 200 Z",
        .path_posterior = NULL,
        .path_hand = NULL,
        .path_foot = NULL,
    },
    {
        .id = "sciatic", .label = "Sciatic nerve", .short_label = "Sciatic",
        .category = OVERLAY_PERIPHERAL,
        .r = 0.55f, .g = 0.25f, .b = 0.85f,
        .path_anterior = NULL,
        .path_posterior =
            /* Posterior thigh */
            "M 82 200 C 80 216 80 234 82 252 C 84 268 88 280 94 284 "
            "C 100 288 106 284 110 276 C 114 266 116 250 116 234 "
            "C 116 218 114 204 112 198 C 108 198 104 198 100 198 "
            "C 96 198 92 198 88 200 Z",
        .path_hand = NULL,
        .path_foot = NULL,
    },
    {
        .id = "common_peroneal",
        .label = "Common peroneal nerve",
        .short_label = "Peroneal",
        .category = OVERLAY_PERIPHERAL,
        .r = 0.30f, .g = 0.85f, .b = 0.70f,
        .path_anterior =
            /* Lateral lower leg, dorsum of foot */
            "M 92 298 C 90 316 90 334 92 350 C 94 362 96 370 98 374 "
            "C 100 376 102 376 104 374 C 106 370 108 362 110 350 "
            "C 112 334 112 316 110 298 Z",
        .path_posterior = NULL,
        .path_hand = NULL,
        .path_foot =
            "M 104 224 C 100 208 98 190 100 176 C 102 166 108 162 114 164 "
            "C 120 168 122 178 122 190 C 122 206 120 220 118 230 Z",
    },
    {
        .id = "tibial", .label = "Tibial nerve", .short_label = "Tibial",
        .category = OVERLAY_PERIPHERAL,
        .r = 0.75f, .g = 0.35f, .b = 0.65f,
        .path_anterior = NULL,
        .path_posterior =
            "M 88 296 C 86 314 86 332 88 348 C 90 360 92 368 94 372 "
            "C 96 374 98 374 100 372 C 102 368 104 360 106 348 "
            "C 108 332 108 314 106 296 Z",
        .path_hand = NULL,
        .path_foot =
            /* Plantar foot */
            "M 70 338 C 68 316 70 294 76 276 C 80 264 86 258 94 258 "
            "C 102 258 108 266 110 278 C 114 296 114 320 112 342 Z",
    },
    {
        .id = "lat_cut_thigh",
        .label = "Lateral cutaneous nerve of thigh",
        .short_label = "Lat cut thigh",
        .category = OVERLAY_PERIPHERAL,
        .r = 0.90f, .g = 0.55f, .b = 0.20f,
        .path_anterior =
            "M 118 200 C 124 212 128 226 128 240 C 128 250 124 256 118 256 "
            "C 114 256 110 250 108 242 C 106 232 108 218 112 206 Z "
            "M 82 200 C 76 212 72 226 72 240 C 72 250 76 256 82 256 "
            "C 86 256 90 250 92 242 C 94 232 92 218 88 206 Z",
        .path_posterior = NULL,
        .path_hand = NULL,
        .path_foot = NULL,
    },
    {
        .id = "sural", .label = "Sural nerve", .short_label = "Sural",
        .category = OVERLAY_PERIPHERAL,
        .r = 0.55f, .g = 0.70f, .b = 0.30f,
        .path_anterior = NULL,
        .path_posterior =
            "M 96 330 C 94 346 94 360 96 370 C 98 378 102 382 106 380 "
            "C 110 376 112 368 112 358 C 112 346 110 332 108 322 Z",
        .path_hand = NULL,
        .path_foot =
            "M 130 338 C 132 322 132 306 128 294 C 124 286 118 286 114 292 "
            "C 110 300 110 316 114 332 Z",
    },
};

int PERIPHERAL_COUNT = sizeof(PERIPHERAL_OVERLAYS) / sizeof(PERIPHERAL_OVERLAYS[0]);
