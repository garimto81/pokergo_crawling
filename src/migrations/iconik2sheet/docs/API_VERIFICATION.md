# Iconik API Verification Guide

> Iconik API 연결 검증 가이드

## 검증 결과 (2025-12-20)

### STEP 1: URL 검증

| URL | 상태 |
|-----|------|
| `https://app.iconik.io` | 200 OK |
| `https://app.iconik.io/API` | 200 OK |
| `https://api.iconik.io` | DNS 실패 (존재하지 않음) |

**결론**: Base URL `https://app.iconik.io`는 정상입니다.

### STEP 2: App-ID 검증

| 항목 | 값 |
|------|-----|
| 값 | `3655f38e-ecf5-11ef-851a-3e64ded19bdd` |
| 길이 | 36자 |
| 형식 | UUID (8-4-4-4-12) |

**결론**: App-ID 형식은 유효합니다.

### STEP 3: Auth-Token 검증

| 항목 | 값 |
|------|-----|
| 값 | `6308c20a-dd57-11f0-84c2-2a3233365a1f` |
| 길이 | 36자 |
| 형식 | UUID (8-4-4-4-12) |

**결론**: Auth-Token 형식은 유효합니다.

### STEP 4: API 연결 테스트

```
모든 엔드포인트에서 401 Unauthorized 발생
```

| 엔드포인트 | 상태 |
|------------|------|
| `/files/v1/storages/` | 401 |
| `/assets/v1/assets/` | 401 |
| `/metadata/v1/views/` | 401 |
| `/users/v1/users/me/` | 401 |

---

## 401 에러 원인 분석

### 가능한 원인

1. **App-ID와 Auth-Token 불일치**
   - App-ID와 Auth-Token이 같은 Application에서 발급된 것인지 확인
   - Iconik Admin > System Settings > Applications에서 확인

2. **Application 비활성화**
   - Application이 활성화 상태인지 확인
   - "Enabled" 옵션이 체크되어 있어야 함

3. **API 권한 부족**
   - Application에 필요한 API 권한이 부여되어 있는지 확인
   - 최소 필요 권한:
     - `assets:read`
     - `metadata:read`
     - `files:read`
     - `collections:read`

4. **토큰 만료**
   - Auth-Token이 만료되지 않았는지 확인
   - 필요시 새 토큰 발급

---

## Iconik Application 설정 확인 방법

1. Iconik 웹 콘솔 로그인: https://app.iconik.io
2. 우측 상단 프로필 > Admin으로 이동
3. System Settings > Applications 메뉴
4. 해당 Application 선택
5. 확인 항목:
   - **App-ID**: Settings 탭에서 확인
   - **Auth-Token**: Tokens 탭에서 확인
   - **Enabled**: 활성화 상태 확인
   - **Permissions**: API 권한 확인

---

## 테스트 명령어

### 환경변수 확인

```powershell
cd D:\AI\claude01\pokergo_crawling\src\migrations\iconik2sheet
python -c "
from dotenv import load_dotenv
from pathlib import Path
import os
load_dotenv(Path('.env.local'), override=True)
print('App-ID:', os.getenv('ICONIK_APP_ID'))
print('Auth-Token:', os.getenv('ICONIK_AUTH_TOKEN')[:20] + '...')
"
```

### API 연결 테스트

```powershell
python -c "
import httpx
from dotenv import load_dotenv
from pathlib import Path
import os

load_dotenv(Path('.env.local'), override=True)

headers = {
    'App-ID': os.getenv('ICONIK_APP_ID'),
    'Auth-Token': os.getenv('ICONIK_AUTH_TOKEN'),
    'Content-Type': 'application/json',
}

with httpx.Client(base_url='https://app.iconik.io/API', headers=headers, timeout=10) as client:
    response = client.get('/files/v1/storages/')
    print('Status:', response.status_code)
    if response.status_code == 200:
        print('SUCCESS!')
    else:
        print('Response:', response.text[:200])
"
```

### pytest Integration 테스트

```powershell
python -m pytest tests/integration/test_metadata_views.py::TestMetadataViews::test_get_all_views -v -s
```

---

## 해결 후 다음 단계

1. Iconik Application 설정 수정
2. `.env.local` 업데이트 (필요시)
3. API 연결 테스트 재실행
4. Integration 테스트 전체 실행
5. 커버리지 리포트 생성
