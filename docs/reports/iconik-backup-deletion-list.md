# Iconik Backup 삭제 대상 리스트

**생성일**: 2025-12-24 | **상태**: Dry-run 완료 (삭제 대기)

---

## 요약

| 항목 | 값 |
|------|---|
| Master_Catalog Backup 파일 | 184개 |
| 고유 Backup Stem | 183개 |
| **Iconik 매칭 Asset (삭제 대상)** | **192개** |
| Skipped Subclips | 0개 |

---

## ⚠️ Subclip 영향 분석

**경고: 67개의 삭제 대상이 174개의 Subclip과 연결되어 있습니다!**

| 항목 | 값 |
|------|---|
| Subclip 보유 삭제 대상 | 67개 |
| 영향받는 Subclip 수 | **174개** |
| Subclip 없는 삭제 대상 | 125개 (안전) |

### Subclip 보유 삭제 대상 목록

| Parent Asset | Subclip 수 |
|--------------|-----------|
| 2016 World Series of Poker - Main Event Show 01 - GMPO 2074 | 7 |
| 2016 World Series of Poker - Main Event Show 05 - GMPO 2076 | 7 |
| WSOP_2005_23 | 7 |
| WSOP_2005_18 | 6 |
| 2016 World Series of Poker - Main Event Show 04 - GMPO 2078 | 5 |
| 2016 World Series of Poker - Main Event Show 08 - GMPO 2053 | 5 |
| WSOP_2004_9 | 5 |
| WSOP_2004_15 | 5 |
| WSOP_2004_17 | 5 |
| WSOP_2004_18 | 5 |
| WSOP_2004_22 | 5 |
| WSOP_2005_17 | 5 |
| 2016 World Series of Poker - Main Event Show 09 - GMPO 2054 | 4 |
| 2016 World Series of Poker - Main Event Show 13 - GMPO 2058 | 4 |
| 2016 World Series of Poker - Main Event Show 03 - GMPO 2075 | 4 |
| WSOP_2004_19 | 4 |
| WSOP_2005_22 | 4 |
| WSOP_2005_29 | 4 |
| WSOP_2008_31 | 4 |
| WSOP_1983 | 3 |
| WSOP_1988 | 3 |
| WSOP_2003_Best_Of_Moneymaker | 1 |
| WSOP_2004_3 | 3 |
| WSOP_2004_4 | 2 |
| WSOP_2004_11 | 1 |
| WSOP_2004_12 | 1 |
| WSOP_2004_13 | 2 |
| WSOP_2004_16 | 3 |
| WSOP_2004_20 | 2 |
| WSOP_2004_21 | 2 |
| WSOP_2005_01 | 3 |
| WSOP_2005_04 | 1 |
| WSOP_2005_09 | 1 |
| WSOP_2005_10 | 2 |
| WSOP_2005_11 | 1 |
| WSOP_2005_12 | 3 |
| WSOP_2005_15 | 1 |
| WSOP_2005_19 | 1 |
| WSOP_2005_20 | 2 |
| WSOP_2005_24 | 1 |
| WSOP_2005_26 | 3 |
| WSOP_2005_30 | 1 |
| WSOP_2005_31 | 3 |
| WSOP_2005_32 | 1 |
| WSOP_2007_26 | 1 |
| WSOP_1973 | 1 |
| WSOP_1987 | 1 |
| WSOP_1989 | 1 |
| WSOP_1995 | 1 |
| WSOP_1997 | 1 |
| WSOP_1998 | 1 |
| WSOP_2000 | 1 |
| 기타 | ~30 |

### 권장 조치

1. **삭제 전 Subclip 먼저 삭제** - Orphan 방지
2. **Primary 파일로 교체** - Backup 대신 Primary를 Parent로 재연결
3. **Subclip 백업 후 삭제** - 메타데이터 보존

---

## 삭제 대상 리스트 (192개)

| # | Asset ID | Title |
|---|----------|-------|
| 1 | a08ec76a-57d7-11f0-8a19-42fef03c9a63 | WSOP_2005_07 |
| 2 | e4a7a04a-57da-11f0-a91a-9e2846c90c6f | WSOP_2005_14 |
| 3 | 3b13b048-5d55-11f0-85d0-7efea5c4aa07 | 2004 WSOP Tounament of Champs_Generic_ESM000101145 |
| 4 | 71157882-57d5-11f0-b419-6e5e3011b544 | WSOP_2005_02 |
| 5 | a52b9b74-5b1d-11f0-a23d-b6caf89df468 | WSOP_2007_25 |
| 6 | 7134d6e8-5d55-11f0-911f-12d30d25bcdd | 2004 WSOP Tournament of Champs_Generic_ESM000101143 |
| 7 | 97eb100e-d5eb-11f0-8370-6af5648c593e | HyperDeck_0031-001 |
| 8 | 458a472e-4146-11f0-b7ad-6ad99968209b | 2016 World Series of Poker - Main Event Show 06 - GMPO 2079 |
| 9 | 80ece4b0-57db-11f0-aedd-fa5b825ffce4 | WSOP_2005_15 |
| 10 | 16607338-fa6a-11ef-a85c-fe1076a5917b | E06_GOG_final_edit_클린본_20231111 |
| 11 | 16d44afe-57d7-11f0-bdd8-8e1b6284e201 | WSOP_2005_06 |
| 12 | 2aa601e8-d5e6-11f0-a3cb-4aede2dbe50d | €10,350 WSOPE MAIN EVENT NLH European Championship - Day 4 (1)-002 |
| 13 | 85dfa6ca-57da-11f0-89e6-ea88d8a5ef19 | WSOP_2005_13 |
| 14 | 12ff699c-d62e-11f0-b9c8-629c3f8f9786 | HyperDeck_0029-001 (1) |
| 15 | e6f0961c-41ec-11f0-a7f8-2aec84cf8b41 | wsop-1981-me-nobug |
| 16 | a6d0386a-41f3-11f0-a8c1-d618d54661d9 | wsop-1983-me-nobug |
| 17 | 67f83ffc-d776-11f0-bb1b-a651cba70f0c | 3_2025 WSOPE #2 €350 No-Limit Hold'em King's Million Part3_NC |
| 18 | 466581f2-420b-11f0-bfd7-2e73e3cd24e2 | wsop-1989-me_nobug |
| 19 | 56a42078-5732-11f0-9375-9e8c10fbcfe1 | WSOP 2005 Show 30 ME 10 Generic_ESM000101827 |
| 20 | ee3155c8-57e1-11f0-99ca-1af05b80abe7 | WSOP_2005_28 |
| 21 | 853bfa44-4145-11f0-a2ae-7e3541aaf691 | 2016 World Series of Poker - Main Event Show 04 - GMPO 2078 |
| 22 | 0f0a231a-d6f9-11f0-ac99-0ae2260bcba7 | HyperDeck_0025-001 |
| 23 | 71de1798-d64b-11f0-92d5-8a5c0bf35cf8 | HyperDeck_0015-003 |
| 24 | eef7795a-57dd-11f0-8faf-aa1880655da4 | WSOP_2005_20 |
| 25 | a65f0e94-5d5d-11f0-9f20-ce6143467bb9 | WSOP_2004_16 |
| 26 | 2006454e-d5ce-11f0-874a-56cf93cd0767 | HyperDeck_0010-004 |
| 27 | cda8a8ca-4200-11f0-8f40-4e41fe7acf31 | wsop-1998-me-nobug |
| 28 | 6f08eb0c-4130-11f0-9a77-7605aa31b7b5 | WSOP14_ME21-Final_4CH |
| 29 | c447fc02-5d55-11f0-bb4d-ea88d8a5ef19 | 2004 WSOP Tournament of Champs_Generic_ESM000101144 |
| 30 | e73537de-57d8-11f0-b419-6e5e3011b544 | WSOP_2005_10 |
| 31 | cd78d7ee-5d62-11f0-ba8f-a29e68e70975 | WSOP_2004_4 |
| 32 | da2aed88-5731-11f0-be30-9e7ddb877ce2 | WSOP 2005 Show 18 5k limit Omaha Generic_ESM000101815 |
| 33 | 71850c66-d803-11f0-99fa-c6d071c46e23 | 3_2025 WSOPE #7 €550 No-Limit Hold'em Colossus Part3_NC |
| 34 | ecabd06c-5731-11f0-a0f2-ee5f227c3bab | WSOP 2005 Show 19 Generic_ESM000101816 |
| 35 | 89c035be-58bd-11f0-8d66-72d1de2b60ff | WSOP_2006_22 |
| 36 | 6d648784-5d5f-11f0-9934-32aecca5456c | WSOP_2004_19 |
| 37 | f6247e8e-57de-11f0-abfb-025387567097 | WSOP_2005_22 |
| 38 | c297b514-4149-11f0-b177-6a57efc7c17b | 2016 World Series of Poker - Main Event Show 15 - GMPO 2080 |
| 39 | bdf83c2e-4147-11f0-95d7-42de95d589a4 | 2016 World Series of Poker - Main Event Show 09 - GMPO 2054 |
| 40 | 1cddb640-d5ce-11f0-8051-e23d64dc1d05 | HyperDeck_0012-002 |
| 41 | e993b862-4143-11f0-bcd8-fac8fdb68851 | WSOP16_GCC_P2_Final |
| 42 | 903de18e-57e1-11f0-9f44-0a764e476bcd | WSOP_2005_27 |
| 43 | ce2e4f86-d777-11f0-b7e2-3a4b6137a789 | 2_2025 WSOPE #2 €350 No-Limit Hold'em King's Million Part2_NC |
| 44 | d6a0b26e-412f-11f0-a210-82b2cbeab841 | WSOP14_ME21-Final_4CH |
| 45 | 7458fd74-d648-11f0-b9c8-629c3f8f9786 | HyperDeck_0017 |
| 46 | 683642c0-4149-11f0-8419-ba042a144df0 | 2016 World Series of Poker - Main Event Show 14 - GMPO 2059 |
| 47 | 18dc6ca0-d5f4-11f0-b7bf-ca2fa222b966 | HyperDeck_0028 |
| 48 | d29e3340-e016-11f0-8d42-9e88bee73267 | HyperDeck_0014-004 |
| 49 | 76e3ce04-57e3-11f0-910b-1ae360319bba | WSOP_2005_31 |
| 50 | ffddfbe8-4114-11f0-88a9-a2a091b9da91 | WSOP_2003_Best_Of_Memorable_Moments |
| 51 | f18dd082-d64b-11f0-bce4-b243b783c07a | HyperDeck_0016-002 |
| 52 | f20d3ff4-d5e0-11f0-9b45-2a9be484b5e7 | HyperDeck_0011-002 |
| 53 | ec33b2a2-5d63-11f0-81d4-867d5c2b67ce | WSOP_2004_6 |
| 54 | fea6450e-57e0-11f0-a28b-12d30d25bcdd | WSOP_2005_26 |
| 55 | 5244b9ac-5732-11f0-a522-e217841fc7b9 | WSOP 2005 Show 29 ME 9 Generic_ESM000101826 |
| 56 | b5b14c18-41ec-11f0-a40e-8eeac603a422 | WSOP_1995 |
| 57 | 4f776b80-fa66-11ef-95e2-2a0f3b4dc8a2 | E03_GOG_final_edit_클린본_20231110 |
| 58 | 2be36178-41e8-11f0-97e1-a2a8ca16bb4d | wsop-1973-me-nobug |
| 59 | 04b8b352-4209-11f0-b5ba-ae0ac4d3b491 | wsop-1993-me-nobug |
| 60 | f622b2f8-4149-11f0-882b-969b6c98bcc0 | 2016 World Series of Poker - Main Event Show 16 - GMPO 2119 |
| 61 | 74a06c5c-57d8-11f0-90c7-1e14b506146e | WSOP_2005_09 |
| 62 | 583c5650-41f5-11f0-bd79-aa8d52d8b58c | WSOP_1983 |
| 63 | a07092ee-d5e1-11f0-b0a2-d64fd99fe528 | HyperDeck_0010-001 |
| 64 | 6f9aad8e-4145-11f0-91b5-66023ec40b23 | 2016 World Series of Poker - Main Event Show 03 - GMPO 2075 |
| 65 | 4ef32dbc-5d61-11f0-aeb6-fa82d69c69c1 | WSOP_2004_22-MPEG-2 6.2Mbps 2-pass |
| 66 | b866959e-d814-11f0-ade4-aea5a4d71df8 | E07_GOG_final_edit_클린본_20231109 |
| 67 | f9727c0a-d64e-11f0-848b-1eb4e18c1e51 | 3_2025 WSOPE #10 €10,000 Pot-Limit Omaha Mystery Bounty Final Day Part 3_NC |
| 68 | 816865d2-d660-11f0-b7e2-3a4b6137a789 | €10,350 WSOPE MAIN EVENT NLH European Championship - Day 2 [BRACELET EVENT #14] (1)-003 |
| 69 | a2fcce52-53b3-11f0-aa40-7af1ae59a77d | WSOP_2010_31-1 |
| 70 | ad18460c-519a-11f0-9124-76f74a494400 | WSOP_2007_26 |
| 71 | 1d19798c-5d65-11f0-8d3f-d692e7d457b6 | WSOP_2004_9 |
| 72 | a5bf0356-d5ab-11f0-ba8f-62dcd18f0da3 | HyperDeck_0007-003 |
| 73 | a5bf0356-d5ab-11f0-ba8f-62dcd18f0da3 | HyperDeck_0007-003 (duplicate) |
| 74 | 8da32f5c-41f1-11f0-a537-5effc22045cf | WSOP_1987 |
| 75 | 50e8dd44-57dd-11f0-82ab-a68b68db5d72 | WSOP_2005_19 |
| 76 | 8fea5d72-57df-11f0-972a-766ded2e0b4a | WSOP_2005_23 |
| 77 | 10f6b176-d815-11f0-aec8-b2ef52435643 | E06_GOG_final_edit_클린본_20231111 |
| 78 | c609800e-5d61-11f0-9375-9e8c10fbcfe1 | WSOP_2004_22 |
| 79 | 3cb63096-5d5b-11f0-b419-6e5e3011b544 | WSOP_2004_11 |
| 80 | 1a6625d0-5d5d-11f0-8a92-ee5f227c3bab | WSOP_2004_15 |
| 81 | 9a7347fc-4148-11f0-b815-aa8d52d8b58c | 2016 World Series of Poker - Main Event Show 12 - GMPO 2057 |
| 82 | e44f3fd0-57db-11f0-a79f-aa1880655da4 | WSOP_2005_16 |
| 83 | 71ac1cac-57de-11f0-aa46-aab65ccbf419 | WSOP_2005_21 |
| 84 | f3fff19e-53b3-11f0-aa97-b253fb187dff | WSOP_2010_31-2 |
| 85 | f2711fda-d7cd-11f0-8e3a-96d258c521c3 | HyperDeck_0011-001 |
| 86 | 11cdb0de-57e3-11f0-baf5-7275f6802e6b | WSOP_2005_30 |
| 87 | 6453a0a4-4139-11f0-93b8-323f9afefe26 | WSOP15_ME10_FINAL_4CH |
| 88 | 03002a9e-fa70-11ef-ad97-12bc69e7c751 | E11_GOG_final_edit_클린본_20231201 |
| 89 | a0a104de-4143-11f0-8e42-d2249c4cffd4 | WSOP16_GCC_P01 |
| 90 | f0d1d9fe-57d4-11f0-8c64-025387567097 | WSOP_2005_01 |
| 91 | a0a104de-4143-11f0-8e42-d2249c4cffd4 | WSOP16_GCC_P01 (duplicate) |
| 92 | 1827c506-d5cd-11f0-b4cb-e23d64dc1d05 | HyperDeck_0013-001 |
| 93 | 948c1400-57d6-11f0-abfb-025387567097 | WSOP_2005_05 |
| 94 | 323c8022-5d63-11f0-bb74-aefdc172c6d4 | WSOP_2004_5 |
| 95 | 502b25cc-d64c-11f0-a4c3-12b48362ead4 | 4_2025 WSOPE #10 €10,000 Pot-Limit Omaha Mystery Bounty Final Day Part 4_NC |
| 96 | 422fdda0-5195-11f0-8e97-b253fb187dff | WSOP_2008_31 |
| 97 | c2e197fe-57d5-11f0-8e4c-9e8c10fbcfe1 | WSOP_2005_03 |
| 98 | c5b6be68-412e-11f0-aff4-6649334dd966 | WSOP_2013_ME28_FINAL_4CH |
| 99 | 0215480a-fa6e-11ef-a059-9a476dd0d83d | E09_GOG_final_edit_클린본_20231114 |
| 100 | f16d7ffa-57dc-11f0-9767-daf4d579ff22 | WSOP_2005_18 |
| 101 | d4847a88-5d5e-11f0-b8aa-36ddf8181078 | WSOP_2004_18 |
| 102 | 39951ea6-d630-11f0-88a3-26c65155f291 | HyperDeck_0028 |
| 103 | 258fbb2c-41fd-11f0-be09-02f388773434 | WSOP_2002_1 |
| 104 | bd790aba-5d5f-11f0-b65d-ea88d8a5ef19 | WSOP_2004_2 |
| 105 | ab7778ec-d802-11f0-b36a-e6962d2c0985 | 1_2025 WSOPE #7 €550 No-Limit Hold'em Colossus Part1_NC |
| 106 | 2c6818a2-53b1-11f0-8a62-fa75e68441df | WSOP_2009_31-1 |
| 107 | 552cdf78-d7cf-11f0-8872-e28b54200bb5 | HyperDeck_0009-002 |
| 108 | e87b0aa0-57d9-11f0-8685-8624814f79a9 | WSOP_2005_12 |
| 109 | c05f7630-d6f7-11f0-b740-163bc42afaea | HyperDeck_0027-005 |
| 110 | 8c164f46-d5e6-11f0-9870-d64fd99fe528 | HyperDeck_0032-001 |
| 111 | 7ec635dc-57dc-11f0-85f2-d692e7d457b6 | WSOP_2005_17 |
| 112 | 284b576a-4205-11f0-90cc-3e7c8ad85b9b | wsop-1997-me-nobug |
| 113 | a63bf3ca-412c-11f0-bd79-aa8d52d8b58c | WSOP_2012_Show_28_FINAL_4CH |
| 114 | 7f275470-4148-11f0-862a-6ad99968209b | 2016 World Series of Poker - Main Event Show 11 - GMPO 2056 |
| 115 | ba06e62c-5d64-11f0-b0c3-060d1ca8231a | WSOP_2004_8 |
| 116 | 1cda7dd4-4115-11f0-a2ae-7e3541aaf691 | WSOP_2003_Best_Of_Moneymaker |
| 117 | 7ad70d94-57e0-11f0-9755-26387d952cb7 | WSOP_2005_25 |
| 118 | 6a2656ee-412e-11f0-84c6-9aa89359856a | WSOP_2013_ME27_FINAL_4CH |
| 119 | 92de87f4-420b-11f0-a07d-42de95d589a4 | WSOP_1989 |
| 120 | 35627986-d5f0-11f0-8823-268aecdfbcb5 | €1,140,000 for 1st €10,350 WSOPE MAIN EVENT NLH European Championship - Final Table |
| 121 | 81faeaea-d64e-11f0-91a6-ce3f07438f66 | 2_2025 WSOPE #10 €10,000 Pot-Limit Omaha Mystery Bounty Final Day Part 2_NC |
| 122 | 74ba2e9e-d6f9-11f0-a844-daa42736885c | HyperDeck_0026-002 |
| 123 | 5c51d274-5d5c-11f0-b8da-bedbafc4127c | WSOP_2004_13 |
| 124 | b05dac74-4201-11f0-9f11-82380587b853 | WSOP_1998 |
| 125 | e2472aa0-57df-11f0-8e0d-3efc3307dae4 | WSOP_2005_24 |
| 126 | ca4d8e86-d5ab-11f0-94e7-82061948f2ec | HyperDeck_0009-005 |
| 127 | 4eddff9c-fa64-11ef-9ff6-4a9c76dc1939 | E01_GOG_final_edit_클린본 |
| 128 | 8127c380-fa72-11ef-a825-32fc60871275 | E12_GOG_final_edit_클린본_20240703 |
| 129 | 97ea029a-d5eb-11f0-8043-fef41b386939 | HyperDeck_0030-002 |
| 130 | 6f087402-d7cf-11f0-b3a9-56408206396d | HyperDeck_0010-003 |
| 131 | 0e8dfe4a-4147-11f0-8a66-ca284c67c5e7 | 2016 World Series of Poker - Main Event Show 08 - GMPO 2053 |
| 132 | 16a70724-412a-11f0-afb5-5a52f45bb1f4 | WSOP_2011_31_ME25 |
| 133 | 067e39d0-5197-11f0-9330-62d61e441c58 | WSOP_2008_31 |
| 134 | c9be14e6-4130-11f0-96c0-66023ec40b23 | WSOP14_ME22_FINAL_4CH |
| 135 | 21e429b4-5d5e-11f0-8c1c-8e1b6284e201 | WSOP_2004_17 |
| 136 | c2cd0a50-58c0-11f0-b7f4-f2dd968c1dcd | WSOP 2006 Show 17 ME 7_ES0700167797_GMPO 743 |
| 137 | 2a0226c8-d815-11f0-99fa-c6d071c46e23 | E12_GOG_final_edit_클린본_20231130 |
| 138 | 9ef381e8-fa67-11ef-8411-c2e1d5e7481a | E04_GOG_final_edit_클린본_20231107 |
| 139 | 841a7852-57d9-11f0-9bed-7efea5c4aa07 | WSOP_2005_11 |
| 140 | 3be1c89c-5d60-11f0-b7f4-f2dd968c1dcd | WSOP_2004_20 |
| 141 | 335b8a4e-4142-11f0-afa4-0e3a73021ac1 | WSOP15_NC02_FINAL_4CH |
| 142 | b051d10c-fa6b-11ef-892f-f29d62211f10 | E07_GOG_final_edit_클린본_20231109 |
| 143 | e87c13ba-d5f0-11f0-a019-e64555e132ed | HyperDeck_0029-001 |
| 144 | 1922649c-d6fa-11f0-be3f-3e41412b2a1c | HyperDeck_0024-004 |
| 145 | b6b8b8ba-4144-11f0-a07d-42de95d589a4 | 2016 World Series of Poker - Main Event Show 02 - GMPO 2077 |
| 146 | 2b83d066-4146-11f0-a3a0-c2667a2931d2 | 2016 World Series of Poker - Main Event Show 05 - GMPO 2076 |
| 147 | ad9cece0-5d5c-11f0-ace2-fa5b825ffce4 | WSOP_2004_14 |
| 148 | 8c9f0aac-fa72-11ef-b5ef-127c37ca4cc4 | E12_GOG_final_edit_클린본_20231130 |
| 149 | 6cf31c9c-d5ab-11f0-8959-da255105e631 | HyperDeck_0005-001 |
| 150 | 25d992b2-d805-11f0-b5b6-4aa9832109ec | 2_2025 WSOPE #7 €550 No-Limit Hold'em Colossus Part2_NC |
| 151 | 99a9c732-4144-11f0-8b02-aa83eaf65964 | 2016 World Series of Poker - Main Event Show 01 - GMPO 2074 |
| 152 | bdd06f82-5731-11f0-86d6-4a1d44b0bd21 | WSOP 2005 Show 17 NLHM Generic_ESM000101814 |
| 153 | 5168d138-412c-11f0-bd11-62b84aa0c789 | WSOP_2012_Show_27_FINAL_4CH |
| 154 | 479f3ca8-57d6-11f0-aa46-aab65ccbf419 | WSOP_2005_04 |
| 155 | 00490002-d5ce-11f0-8b6b-ba32cfebb41a | HyperDeck_0011-003 |
| 156 | c44d413a-fa68-11ef-8b0a-5e1863287c10 | E05_GOG_final_edit_클린본_20231107 |
| 157 | 7b4c4a1c-57e2-11f0-b308-12d30d25bcdd | WSOP_2005_29 |
| 158 | d63a71bc-4147-11f0-9dd5-b2bf2caeafeb | 2016 World Series of Poker - Main Event Show 10 - GMPO 2055 |
| 159 | 37482b7e-41f3-11f0-b152-6649a251e265 | wsop-1988-me_nobug |
| 160 | 4cd10052-5732-11f0-99da-ce6143467bb9 | WSOP 2005 Show 28 ME 8 Generic_ESM000101825 |
| 161 | 23d40176-57d8-11f0-bafb-f2dd968c1dcd | WSOP_2005_08 |
| 162 | bd12554e-5199-11f0-b999-d2827a6a04d5 | WSOP_2005_32 |
| 163 | 02edcf70-41ec-11f0-a07d-42de95d589a4 | 1995 WSOP VHS DUB |
| 164 | f07bb330-5d60-11f0-8e4c-9e8c10fbcfe1 | WSOP_2004_21 |
| 165 | 00b88e9c-58bd-11f0-85db-fa82d69c69c1 | WSOP_2006_21 |
| 166 | e8df523e-4209-11f0-8e35-6ece03aa0542 | WSOP_1993 |
| 167 | f92c08ee-53b1-11f0-bb98-96c11adf7cd9 | WSOP_2009_31-2 |
| 168 | a719f962-4141-11f0-a62e-0e3a73021ac1 | WSOP15_NC01_FINAL_4CH |
| 169 | 5c27f56e-5d5a-11f0-80c3-32aecca5456c | WSOP_2004_1 |
| 170 | 42c84a06-4149-11f0-b35e-fac8fdb68851 | 2016 World Series of Poker - Main Event Show 13 - GMPO 2058 |
| 171 | 68500db4-412a-11f0-bcd8-fac8fdb68851 | WSOP_2011_32_ME26 |
| 172 | 31fc176c-5732-11f0-9f21-c69524c968bb | WSOP 2005 Show 23 ME 3 Generic_ESM000101820 |
| 173 | 2c76a434-41f6-11f0-bce8-9aa89359856a | WSOP_1983 |
| 174 | 7a6cc662-41f3-11f0-95a3-927b8c1d965c | WSOP_1988 |
| 175 | e749c62a-4114-11f0-a70d-82380587b853 | WSOP_2003_Best_Of_Amazing_Bluffs |
| 176 | ac657644-4114-11f0-bec4-76f4ca44effd | WSOP_2003_Best_Of_Amazing_All-Ins |
| 177 | e45c9efe-4201-11f0-93b8-323f9afefe26 | wsop-2000-me-nobug |
| 178 | e81a584a-5d5b-11f0-9be4-32bb6c3e5e1f | WSOP_2004_12 |
| 179 | b7109c36-d629-11f0-b8cd-fa2a61c490b6 | €10,350 WSOPE MAIN EVENT NLH European Championship - Day 3 -003 |
| 180 | af1a67ec-d5ab-11f0-85e9-c2515febece1 | HyperDeck_0008-002 |
| 181 | e419e800-d777-11f0-8576-12b48362ead4 | 1_2025 WSOPE #2 €350 No-Limit Hold'em King's Million Part1_NC |
| 182 | f0846fec-41eb-11f0-9994-b2bf2caeafeb | wsop-1995-me-nobug |
| 183 | 62d65d64-d5ab-11f0-b914-befbc3e6bec5 | HyperDeck_0006-004 |
| 184 | f7ccf9e4-4205-11f0-bbb0-beff46978308 | WSOP_1997 |
| 185 | 1f34afa8-4130-11f0-ab80-ca844ab83b64 | WSOP14_ME22_FINAL_4CH |
| 186 | ea77fe9a-41fd-11f0-ab6b-5a3137a5aa2f | WSOP_2002_2 |
| 187 | 3ec99808-5d62-11f0-8d2b-7e29f83ab89f | WSOP_2004_3 |
| 188 | 49c0777a-5d64-11f0-841b-76fd35d3b0b4 | WSOP_2004_7 |
| 189 | d8494bf8-fa6c-11ef-bad5-66b651a8daef | E08_GOG_final_edit_클린본_20231111 |
| 190 | f0347ee2-4146-11f0-9d5c-c29d2249658b | 2016 World Series of Poker - Main Event Show 07 - GMPO 2052 |
| 191 | 3cc48848-fa65-11ef-83a6-a2a5d7d755c4 | E02_GOG_final_edit_클린본_20231031 |
| 192 | 167a0b12-d64d-11f0-9117-3efadd4e929a | 1_2025 WSOPE #10 €10,000 Pot-Limit Omaha Mystery Bounty Final Day Part 1_NC |

---

## 카테고리별 분류

### WSOP Classic (1973-2002) - 27개

| Era | Title Pattern | Count |
|-----|---------------|-------|
| Classic | wsop-1973-me-nobug ~ wsop-2000-me-nobug | 11 |
| Classic | WSOP_1983 ~ WSOP_2002_2 | 16 |

### WSOP Boom Era (2003-2010) - 62개

| Year | Title Pattern | Count |
|------|---------------|-------|
| 2003 | WSOP_2003_Best_Of_* | 4 |
| 2004 | WSOP_2004_* | 22 |
| 2005 | WSOP_2005_* | 32 |
| 2006 | WSOP_2006_* | 2 |
| 2007 | WSOP_2007_* | 2 |

### WSOP HD Era (2011-2025) - 57개

| Year | Title Pattern | Count |
|------|---------------|-------|
| 2011-2016 | WSOP11 ~ WSOP16_* | 24 |
| 2025 | 2025 WSOPE* | 11 |
| GOG | E01~E12_GOG_final_edit_* | 12 |

### HyperDeck (기타) - 30개

| Title Pattern | Count |
|---------------|-------|
| HyperDeck_* | 30 |

### 중복 Asset - 2개

- `a5bf0356-d5ab-11f0-ba8f-62dcd18f0da3` (HyperDeck_0007-003)
- `a0a104de-4143-11f0-8e42-d2249c4cffd4` (WSOP16_GCC_P01)

---

## 삭제 실행 방법

```powershell
cd src/migrations/iconik2sheet

# 실제 삭제 실행
python -m scripts.cleanup_backups --execute

# 프롬프트에서 "DELETE" 입력
```

---

## 관련 파일

| 파일 | 용도 |
|------|------|
| `docs/reports/iconik-backup-deletion-list.csv` | CSV 형식 리스트 |
| `docs/prds/PRD-ICONIK-BACKUP-CLEANUP.md` | PRD 문서 |
| `data/cleanup_logs/backup_cleanup_*.log` | 실행 로그 |
