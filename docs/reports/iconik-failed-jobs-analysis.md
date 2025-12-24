# Iconik Failed Jobs 분석 리포트

**생성일**: 2025-12-24
**분석 대상**: 실패한 Iconik Jobs 44건

---

## 요약

| 에러 유형 | 건수 | 작업 타입 | 우선순위 |
|----------|------|----------|---------|
| ImageMagick 오류 | 25건 | TRANSCODE | 중 (ISG 업데이트 필요) |
| Timeout | 13건 | TRANSFER | **높음** (재시도 필요) |
| Unexpected Error | 3건 | TRANSCODE | 낮음 (수동 확인) |
| Upload Failed | 2건 | TRANSFER | 중 (권한 확인) |
| File Not Found | 1건 | TRANSFER | 낮음 (NAS 확인) |

---

## 1. ImageMagick 오류 (25건)

### 원인
ISG(Iconik Storage Gateway) 서버의 ImageMagick 버전이 v6으로, v7에서 deprecated된 `convert` 명령어를 사용하여 오류 발생.

### 에러 메시지
```
WARNING: The convert command is deprecated in IMv7, use "magick" instead
convert: no decode delegate for this image format
```

### 영향받는 파일
- `e7_winner.jpg@SynoEAStream`
- `e14_winner.jpg@SynoEAStream`
- `e3_winner.jpg@SynoEAStream`
- ... 외 22건 (WSOP 2025 이벤트 우승자 사진)

### 해결 방법

| 옵션 | 방법 | 난이도 |
|------|------|--------|
| A | ISG 서버 ImageMagick v7 업데이트 | 높음 |
| B | Iconik Support 티켓 생성 | 낮음 |
| C | 해당 Asset 썸네일/프록시 수동 재생성 | 중간 |

**권장**: 옵션 B (Iconik Support 문의)

---

## 2. Timeout (13건) - 우선 처리 필요

### 원인
대용량 파일(수십~수백GB) NAS → GCS 전송 중 시간 초과.

### 영향받는 Asset (고유 8개)

| Asset ID | 파일명 | 시도 횟수 |
|----------|--------|----------|
| `0feb0046-d5b5-11f0-9870-3ebb9ce696e6` | WSOP Paradise - Day 4 | 1회 |
| `e471d4a8-d5b4-11f0-9378-fe00f133061d` | WSOP Paradise - Day 3 | **3회** |
| `23a98206-d5b5-11f0-ae5b-4e47c42e6298` | WSOP Paradise - Day 1C | **2회** |
| `3a9b8e14-d5b5-11f0-9147-9a8d2ee5d8bb` | WSOP Paradise - Day 1D | 1회 |
| `6faeb796-d5b7-11f0-b939-26e53bf6b4d7` | WSOP Paradise - Day 1B | 1회 |
| `f6413e12-d5b4-11f0-8140-420ecbbe6b56` | WSOP Paradise - Final Day | 1회 |
| `f9161478-d5b4-11f0-bec9-867586061df4` | WSOP Cyprus Main Event | 1회 |
| `8fea767c-d638-11f0-8012-3e6e7d5e74e6` | WSOP London Main Event | 1회 |

### 해결 방법

1. **Iconik UI에서 재시도**:
   - Asset 선택 → Actions → Retry Transfer
   - 네트워크 안정적인 시간대(새벽) 권장

2. **API로 재시도** (추후 스크립트 구현 가능):
   ```
   POST /API/files/v1/transfers/jobs/state/
   ```

---

## 3. Unexpected Error (3건)

### 영향받는 파일

| Asset ID | 파일명 | 추정 원인 |
|----------|--------|----------|
| `885ccc50-5b3d-11f0-...` | ESPN 2007 WSOP SEASON 5 SHOW 15.mov | 구형 MOV 코덱 |
| `ec33b2a2-5d6b-11f0-...` | WSOP_2004_6.mxf | MXF 포맷 미지원 |
| `44a05664-d5a6-11f0-...` | 2022 WSOP Event #39 | 파일 손상 가능 |

### 해결 방법

1. NAS에서 원본 파일 재생 테스트
2. FFmpeg로 표준 포맷(H.264 MP4)으로 변환 후 재업로드
3. 변환 불가 시 원본만 보관

---

## 4. Upload Failed (2건)

### 원인
GGMillions/Super High Roller 폴더 GCS 업로드 실패.

### 영향받는 파일
- Super High Roller Poker FINAL TABLE with Frank Crivello
- Super High Roller Poker FINAL TABLE with Robert Flink

### 해결 방법

1. GCS 버킷 권한 확인
2. 폴더명 특수문자 확인 (공백, 한글 등)
3. Iconik Support 문의

---

## 5. File Not Found (1건)

### 영향받는 파일
- `WSOPE08_Episode_1_H264` (Asset: `88fdc862-d60a-11f0-...`)

### 해결 방법

1. NAS 경로 확인: `/mnt/storage/ARCHIVE/WSOP/...`
2. 파일명 변경/이동 여부 확인
3. 파일 없으면 Iconik에서 해당 Asset 삭제

---

## 조회 명령어

```powershell
cd D:\AI\claude01\pokergo_crawling\src\migrations\iconik2sheet

# 실패한 작업 조회
python -m scripts.check_jobs --status failed

# 최근 30일 실패 작업
python -m scripts.check_jobs --status failed --days 30

# CSV 내보내기
python -m scripts.check_jobs --status failed --output csv --output-file failed_jobs.csv
```

---

## 생성된 파일

| 파일 | 내용 |
|------|------|
| `failed_jobs_analysis.json` | 전체 분석 데이터 (JSON) |
| `failed_timeout_jobs.csv` | Timeout 작업 목록 (재시도용) |
| `failed_imagemagick_jobs.csv` | ImageMagick 오류 목록 |

---

## 다음 단계

- [ ] Timeout 작업 8개 재시도 (Iconik UI)
- [ ] ImageMagick 오류 관련 Iconik Support 티켓 생성
- [ ] File Not Found 파일 NAS 확인
- [ ] 재시도 후 본 리포트 업데이트
