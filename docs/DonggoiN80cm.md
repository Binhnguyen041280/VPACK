Vâng, để tôi phân tích chi tiết từng file DonggoiN_80cm25 giống như Cam1_N3_29:

  📊 Phân Tích Chi Tiết DonggoiN_80cm25

  ---
  File: log_DonggoiN_80cm25_0000_0300.txt

  1,On,
  41,Off,         <- Ts = 41 (On → Off)
  58,On,          <- Te = 58 (Off → On) → Event 1: Ts=41, Te=58, No MVD ❌
  62,Off,         <- Ts = 62 (On → Off)
  88,On,          <- Te = 88 (Off → On) → Event 2: Ts=62, Te=88, No MVD ❌
  92,Off,         <- Ts = 92 (On → Off)
  114,Off,SPXVN058693416243  <- MVD detected
  118,On,         <- Te = 118 (Off → On) → Event 3: Ts=92, Te=118, MVD ✅
  122,Off,        <- Ts = 122 (On → Off)
  136,Off,SPXVN059248047533  <- MVD detected
  139,On,         <- Te = 139 (Off → On) → Event 4: Ts=122, Te=139, MVD ✅
  142,Off,        <- Ts = 142 (On → Off)
  158,Off,SPXVN050861398373  <- MVD detected
  162,On,         <- Te = 162 (Off → On) → Event 5: Ts=142, Te=162, MVD ✅
  165,Off,        <- Ts = 165 (On → Off)
  186,Off,SPXVN057955111192  <- MVD detected
  190,On,         <- Te = 190 (Off → On) → Event 6: Ts=165, Te=190, MVD ✅
  193,Off,        <- Ts = 193 (On → Off)
  213,Off,SPXVN050861398373  <- MVD detected
  217,On,         <- Te = 217 (Off → On) → Event 7: Ts=193, Te=217, MVD ✅
  221,Off,        <- Ts = 221 (On → Off)
  242,Off,SPXVN056145093873  <- MVD detected
  246,On,         <- Te = 246 (Off → On) → Event 8: Ts=221, Te=246, MVD ✅
  250,Off,        <- Ts = 250 (On → Off)
  271,On,         <- Te = 271 (Off → On) → Event 9: Ts=250, Te=271, No MVD ❌
  274,Off,        <- Ts = 274 (On → Off)
  292,Off,SPXVN053810041542  <- MVD detected
  296,On,         <- Te = 296 (Off → On) → Event 10: Ts=274, Te=296, MVD ✅
  299,Off,        <- Ts = 299 (On → Off, pending to next file)

  → Không có MVD: 3/10 events (30%)

  ---
  File: log_DonggoiN_80cm25_0300_0600.txt

  (Pending: Ts=299)
  321,Off,SPXVN050899007633  <- MVD detected
  326,On,         <- Te = 326 (Off → On) → Event 1: Ts=299, Te=326, MVD ✅
  328,Off,        <- Ts = 328 (On → Off)
  348,Off,SPXVN053052444843  <- MVD detected
  352,On,         <- Te = 352 (Off → On) → Event 2: Ts=328, Te=352, MVD ✅
  355,Off,        <- Ts = 355 (On → Off)
  374,Off,SPXVN053810041542  <- MVD detected
  378,On,         <- Te = 378 (Off → On) → Event 3: Ts=355, Te=378, MVD ✅
  382,Off,        <- Ts = 382 (On → Off)
  398,Off,SPXVN055851181462  <- MVD detected
  401,On,         <- Te = 401 (Off → On) → Event 4: Ts=382, Te=401, MVD ✅
  405,Off,        <- Ts = 405 (On → Off)
  423,Off,SPXVN059044299733  <- MVD detected
  427,On,         <- Te = 427 (Off → On) → Event 5: Ts=405, Te=427, MVD ✅
  432,Off,        <- Ts = 432 (On → Off)
  464,On,         <- Te = 464 (Off → On) → Event 6: Ts=432, Te=464, No MVD ❌
  468,Off,        <- Ts = 468 (On → Off)
  488,On,         <- Te = 488 (Off → On) → Event 7: Ts=468, Te=488, No MVD ❌
  489,Off,SPXVN058421327193  <- MVD detected
  490,Off,        <- (duplicate Off)
  492,On,         <- Te = 492 (Off → On) → Event 8: Ts=489, Te=492, MVD ✅ (note: Ts adjusted to 489)
  496,Off,        <- Ts = 496 (On → Off)
  518,Off,SPXVN052038201513  <- MVD detected
  526,On,         <- Te = 526 (Off → On) → Event 9: Ts=496, Te=526, MVD ✅
  531,Off,        <- Ts = 531 (On → Off)
  557,On,         <- Te = 557 (Off → On) → Event 10: Ts=531, Te=557, No MVD ❌
  558,Off,SPXVN056946631972  <- MVD detected (trùng second 558)
  558,Off,        <- (duplicate Off)
  560,On,         <- Te = 560 (Off → On) → Event 11: Ts=558, Te=560, MVD ✅
  562,Off,        <- Ts = 562 (On → Off)
  578,Off,SPXVN055425672083  <- MVD detected
  585,On,         <- Te = 585 (Off → On) → Event 12: Ts=562, Te=585, MVD ✅
  590,Off,        <- Ts = 590 (On → Off, pending to next file)

  → Không có MVD: 3/12 events (25%)

  ---
  File: log_DonggoiN_80cm25_0600_0900.txt

  (Pending: Ts=590)
  607,Off,851480822554  <- MVD detected
  611,On,         <- Te = 611 (Off → On) → Event 1: Ts=590, Te=611, MVD ✅
  614,Off,        <- Ts = 614 (On → Off)
  631,On,         <- Te = 631 (Off → On) → Event 2: Ts=614, Te=631, No MVD ❌
  634,Off,        <- Ts = 634 (On → Off)
  645,On,         <- Te = 645 (Off → On) → Event 3: Ts=634, Te=645, No MVD ❌
  648,Off,        <- Ts = 648 (On → Off)
  662,Off,SPXVN054093472033  <- MVD detected
  669,On,         <- Te = 669 (Off → On) → Event 4: Ts=648, Te=669, MVD ✅
  672,Off,        <- Ts = 672 (On → Off)
  691,Off,SPXVN059643237513  <- MVD detected
  694,On,         <- Te = 694 (Off → On) → Event 5: Ts=672, Te=694, MVD ✅
  699,Off,        <- Ts = 699 (On → Off)
  713,Off,SPXVN055494933283  <- MVD detected
  722,On,         <- Te = 722 (Off → On) → Event 6: Ts=699, Te=722, MVD ✅
  725,Off,        <- Ts = 725 (On → Off)
  739,Off,SPXVN057848912542  <- MVD detected
  748,On,         <- Te = 748 (Off → On) → Event 7: Ts=725, Te=748, MVD ✅
  752,Off,        <- Ts = 752 (On → Off)
  769,Off,SPXVN050301142803  <- MVD detected
  780,On,         <- Te = 780 (Off → On) → Event 8: Ts=752, Te=780, MVD ✅
  783,Off,        <- Ts = 783 (On → Off)
  803,Off,SPXVN051029614023  <- MVD detected
  812,On,         <- Te = 812 (Off → On) → Event 9: Ts=783, Te=812, MVD ✅
  816,Off,        <- Ts = 816 (On → Off)
  835,Off,SPXVN055090513632  <- MVD detected
  838,On,         <- Te = 838 (Off → On) → Event 10: Ts=816, Te=838, MVD ✅
  843,Off,        <- Ts = 843 (On → Off)
  860,Off,SPXVN057397122803  <- MVD detected
  867,On,         <- Te = 867 (Off → On) → Event 11: Ts=843, Te=867, MVD ✅
  870,Off,        <- Ts = 870 (On → Off)
  885,Off,SPXVN058075470452  <- MVD detected
  889,On,         <- Te = 889 (Off → On) → Event 12: Ts=870, Te=889, MVD ✅
  893,Off,        <- Ts = 893 (On → Off, pending to next file)

  → Không có MVD: 2/12 events (17%)

  ---
  File: log_DonggoiN_80cm25_0900_1200.txt

  (Pending: Ts=893)
  910,Off,SPXVN050280168233  <- MVD detected
  913,On,         <- Te = 913 (Off → On) → Event 1: Ts=893, Te=913, MVD ✅
  917,Off,        <- Ts = 917 (On → Off)
  939,Off,SPXVN051841038682  <- MVD detected
  943,On,         <- Te = 943 (Off → On) → Event 2: Ts=917, Te=943, MVD ✅
  947,Off,        <- Ts = 947 (On → Off)
  978,Off,SPXVN059041602523  <- MVD detected
  983,On,         <- Te = 983 (Off → On) → Event 3: Ts=947, Te=983, MVD ✅
  987,Off,        <- Ts = 987 (On → Off)
  1010,Off,SPXVN055090513632  <- MVD detected
  1015,On,        <- Te = 1015 (Off → On) → Event 4: Ts=987, Te=1015, MVD ✅
  1020,Off,       <- Ts = 1020 (On → Off)
  1058,Off,SPXVN058374309993  <- MVD detected
  (No On after → pending to next file)

  → Không có MVD: 0/4 events (0%)

  ---
  File: log_DonggoiN_80cm25_1200_1500.txt

  (Pending: Ts=1020)
  1257,Off,       <- No MVD
  1282,On,        <- Te = 1282 (Off → On) → Event 1: Ts=1020, Te=1282, MVD ✅ (SPXVN058374309993 from
  1058)
  1285,Off,       <- Ts = 1285 (On → Off)
  1308,Off,SPXVN053147538232  <- MVD detected
  1311,On,        <- Te = 1311 (Off → On) → Event 2: Ts=1285, Te=1311, MVD ✅
  1315,Off,       <- Ts = 1315 (On → Off)
  1329,Off,SPXVN050890477683  <- MVD detected
  1334,On,        <- Te = 1334 (Off → On) → Event 3: Ts=1315, Te=1334, MVD ✅
  1338,Off,       <- Ts = 1338 (On → Off)
  1351,Off,SPXVN055090513632  <- MVD detected
  1352,On,        <- Te = 1352 (Off → On) → Event 4: Ts=1338, Te=1352, MVD ✅
  1355,Off,       <- Ts = 1355 (On → Off)
  1370,Off,SPXVN056619623202  <- MVD detected
  1373,On,        <- Te = 1373 (Off → On) → Event 5: Ts=1355, Te=1373, MVD ✅
  1375,Off,       <- Ts = 1375 (On → Off)
  1386,Off,SPXVN057392472222  <- MVD detected
  1388,On,        <- Te = 1388 (Off → On) → Event 6: Ts=1375, Te=1388, MVD ✅
  1390,Off,       <- Ts = 1390 (On → Off)
  1404,Off,SPXVN057724254952  <- MVD detected
  1407,On,        <- Te = 1407 (Off → On) → Event 7: Ts=1390, Te=1407, MVD ✅
  1408,Off,       <- Ts = 1408 (On → Off)
  1420,Off,SPXVN054265306562  <- MVD detected
  1433,Off,851410981803  <- MVD detected (note: 2 MVDs between On→Off)
  1437,On,        <- Te = 1437 (Off → On) → Event 8: Ts=1408, Te=1437, MVD ✅ (2 codes)
  1438,Off,       <- Ts = 1438 (On → Off)
  1452,Off,SPXVN054600506552  <- MVD detected
  1455,On,        <- Te = 1455 (Off → On) → Event 9: Ts=1438, Te=1455, MVD ✅
  1458,Off,       <- Ts = 1458 (On → Off)
  1470,Off,SPXVN057473244303  <- MVD detected
  1473,On,        <- Te = 1473 (Off → On) → Event 10: Ts=1458, Te=1473, MVD ✅
  1478,Off,       <- Ts = 1478 (On → Off)
  1488,Off,SPXVN058250531183  <- MVD detected
  1490,On,        <- Te = 1490 (Off → On) → Event 11: Ts=1478, Te=1490, MVD ✅
  1494,Off,       <- Ts = 1494 (On → Off, pending to next file)

  → Không có MVD: 0/11 events (0%)

  ---
  File: log_DonggoiN_80cm25_1500_1800.txt

  (Pending: Ts=1494)
  1503,On,SPXVN052620477523  <- MVD detected at On (unusual!)
  1508,On,        <- Te = 1508 (Off → On) → Event 1: Ts=1494, Te=1508, MVD ✅
  1511,Off,       <- Ts = 1511 (On → Off, no Te → pending)

  → Không có MVD: 0/1 event (0%)

  ---
  🎯 Tổng Kết DonggoiN_80cm25

  | File      | Events không MVD | Tổng events | Tỷ lệ |
  |-----------|------------------|-------------|-------|
  | 0000-0300 | 3                | 10          | 30%   |
  | 0300-0600 | 3                | 12          | 25%   |
  | 0600-0900 | 2                | 12          | 17%   |
  | 0900-1200 | 0                | 4           | 0%    |
  | 1200-1500 | 0                | 11          | 0%    |
  | 1500-1800 | 0                | 1           | 0%    |
  | TỔNG      | 8                | 50          | 16%   |

  ---
  📈 Kết Luận

  Video DonggoiN_80cm25 có tỷ lệ decode QR rất tốt:
  - Tổng events: 50
  - Events có MVD: 42 (84%)
  - Events không MVD: 8 (16%)
  - Database lưu: 43 events (bỏ qua 8 events không MVD, có 1 event có 2 MVD)

  → Tỷ lệ fail 16% là rất tốt so với Cam1_N3_29 (49%)