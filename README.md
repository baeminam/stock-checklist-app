# 매크로·산업·종목 스코어카드

거시경제·주식 추세 예측 체크리스트(MoneyTrend V3.1)의 채점 규칙을 그대로 옮긴 개인용 투자 판단 계산기입니다.
매크로(40%)·산업(25%)·종목(25%)·시장구조(10%) 4단계 30개 항목을 -2~+2로 채점하면 캡/베토 안전장치와 가중 총점, 실행 구간을 자동으로 계산합니다.

이 문서와 앱은 교육용 참고 자료이며 특정 종목의 매수·매도 권유가 아닙니다. 최종 판단과 책임은 사용자 본인에게 있습니다.

## GitHub Pages로 배포하기

1. 이 저장소를 GitHub에 올린 뒤 **Settings → Pages → Source: Deploy from a branch → Branch: main / (root)** 를 선택합니다.
2. 몇 분 후 `https://<사용자명>.github.io/<저장소명>/` 주소로 접속하면 됩니다.
3. `.github/workflows/update-data.yml`이 매일 자동으로 `macro_data_fetch.py`를 실행해 `data.json`을 갱신하고 커밋합니다. 페이지는 열릴 때마다 이 `data.json`을 자동으로 불러옵니다.
4. 별도 서버나 API 키 설정 없이 그대로 동작합니다 (하이일드 스프레드 제외, 아래 참고).

### 하이일드 스프레드까지 자동 조회하려면 (선택)

하이일드 스프레드(OAS)만 무료 키 없는 공개 API가 없어 기본적으로는 "조회 실패"로 표시됩니다. FRED(세인트루이스 연준)의 **무료** API 키를 등록하면 이것도 자동으로 채워집니다.

1. https://fredaccount.stlouisfed.org/apikeys 에서 무료 계정 가입 후 API 키 발급 (신용카드 불필요)
2. 저장소 **Settings → Secrets and variables → Actions → New repository secret**
3. Name: `FRED_API_KEY`, Value: 발급받은 키 → Add secret
4. **Actions → Update macro data → Run workflow**로 한 번 수동 실행하면 바로 반영됩니다 (이후로는 매일 자동 갱신에 포함됨)

이 키는 GitHub Actions(서버) 안에서만 쓰이고 브라우저로는 전송되지 않으므로 Secret으로 등록해도 안전합니다.

## 로컬에서 사용하기

- `index.html`을 더블클릭해서 브라우저로 바로 열 수 있습니다.
- 다만 로컬 파일(`file://`)에서는 브라우저 보안 정책 때문에 `data.json` 자동 불러오기가 동작하지 않습니다. "자동조회" 탭에서 아래 방법으로 수동 반영하세요.
  - `run_macro_fetch.bat` 더블클릭 → 클립보드에 자동 복사 → 앱에 Ctrl+V
  - 또는 `python macro_data_fetch.py --out data.json` 실행 후 "📂 data.json 파일 선택"으로 불러오기

## 저장 데이터

- 종목/업종별 채점 기록은 이 브라우저의 로컬 저장소(localStorage)에만 저장됩니다. 서버로 전송되지 않으며, 다른 사람과 링크를 공유해도 서로의 기록은 보이지 않습니다.
- 기록은 "저장 기록" 탭에서 JSON으로 내보내기/가져오기할 수 있습니다.

## AI 초안 채점 (선택 기능)

"AI 초안" 탭에서 본인의 API 키를 입력하면, 종목/업종명을 바탕으로 30개 항목의 초안 점수와 근거를 AI가 생성해줍니다. 두 제공사 중 선택할 수 있습니다.

| 제공사 | 비용 | 키 발급 |
|---|---|---|
| Google Gemini (기본값) | 무료 티어 제공 (분당·일일 호출 횟수 제한, 신용카드 불필요) | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) |
| Anthropic Claude | 유료 (신규 가입 시 소액 체험 크레딧이 있을 수 있음) | [console.anthropic.com](https://console.anthropic.com) |

- API 키는 이 브라우저의 로컬 저장소에만 저장되며, 선택한 제공사의 API 서버로만 전송됩니다. 이 앱을 만든 사람을 포함해 누구에게도 전달되지 않습니다.
- 무료 티어의 조건(호출 횟수 제한 등)은 제공사가 언제든 바꿀 수 있습니다.
- AI는 실시간 시세를 조회하지 않고 학습 시점 지식으로 답합니다. 반드시 초안으로만 참고하고 최신 데이터로 직접 검증한 뒤 사용하세요.

## 파일 구성

| 파일 | 설명 |
|---|---|
| `index.html` | 스코어카드 웹 앱 본체 |
| `macro_data_fetch.py` | 매크로 참고 데이터를 공개 API에서 가져오는 스크립트 |
| `run_macro_fetch.bat` | 위 스크립트를 실행하고 결과를 클립보드에 복사하는 Windows 배치 파일 |
| `data.json` | GitHub Actions가 매일 갱신하는 매크로 데이터 (자동 생성) |
| `.github/workflows/update-data.yml` | 매일 `data.json`을 자동 갱신하는 GitHub Actions 워크플로 |
