#!/usr/bin/env python3
"""
기술적분석 탭의 '한글 종목 사전' 종목들에 대해 일별 시세(OHLCV)를 받아
kr_stocks/<종목코드>.json 으로 저장하는 스크립트.

Twelve Data 무료 플랜은 KRX(한국거래소) 종목의 시계열 데이터를 지원하지 않는다
(Pro/Venture 플랜부터 제공). 반면 네이버 금융의 공개 시세 API는 무료이지만
브라우저 보안 정책(CORS) 때문에 웹페이지에서 직접 호출할 수 없다.

그래서 이 스크립트를 GitHub Actions(서버)에서 매일 실행해 결과를 저장소에
커밋해 두면, 웹페이지는 같은 저장소의 정적 파일을 같은 출처(same-origin)로
불러오기만 하면 되어 CORS 제약 없이 한국 종목 차트를 무료로 볼 수 있다.

이 스크립트가 다루는 종목 목록은 index.html의 KR_STOCK_LIST와 반드시 같아야
한다(하나를 바꾸면 다른 쪽도 함께 바꿀 것).

사용법:
    python kr_stocks_fetch.py --out-dir kr_stocks
"""

import argparse
import json
import re
import sys
import time
import urllib.request
from datetime import datetime, timedelta

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
TIMEOUT = 12
RETRIES = 2

# index.html의 KR_STOCK_LIST와 동일한 목록 (종목코드, 종목명)
KR_STOCK_LIST = [
    ("005930", "삼성전자"), ("005935", "삼성전자우"), ("000660", "SK하이닉스"), ("373220", "LG에너지솔루션"),
    ("207940", "삼성바이오로직스"), ("005380", "현대차"), ("000270", "기아"), ("068270", "셀트리온"),
    ("005490", "POSCO홀딩스"), ("035420", "NAVER"), ("035720", "카카오"), ("051910", "LG화학"),
    ("006400", "삼성SDI"), ("105560", "KB금융"), ("055550", "신한지주"), ("086790", "하나금융지주"),
    ("028260", "삼성물산"), ("012330", "현대모비스"), ("066570", "LG전자"), ("096770", "SK이노베이션"),
    ("316140", "우리금융지주"), ("003670", "POSCO퓨처엠"), ("009830", "한화솔루션"), ("003550", "LG"),
    ("034730", "SK"), ("329180", "HD현대중공업"), ("032830", "삼성생명"), ("000810", "삼성화재"),
    ("015760", "한국전력"), ("033780", "KT&G"), ("034020", "두산에너빌리티"), ("011200", "HMM"),
    ("003490", "대한항공"), ("017670", "SK텔레콤"), ("030200", "KT"), ("051900", "LG생활건강"),
    ("090430", "아모레퍼시픽"), ("251270", "넷마블"), ("259960", "크래프톤"), ("036570", "엔씨소프트"),
    ("097950", "CJ제일제당"), ("011170", "롯데케미칼"), ("010950", "S-Oil"), ("241560", "두산밥캣"),
    ("042700", "한미반도체"), ("009540", "HD한국조선해양"), ("028050", "삼성엔지니어링"), ("000720", "현대건설"),
    ("006360", "GS건설"), ("000150", "두산"), ("006800", "미래에셋증권"), ("005940", "NH투자증권"),
    ("138040", "메리츠금융지주"), ("005830", "DB손해보험"), ("086280", "현대글로비스"), ("010120", "LS ELECTRIC"),
    ("018880", "한온시스템"), ("016360", "삼성증권"), ("024110", "기업은행"), ("138930", "BNK금융지주"),
    ("139130", "DGB금융지주"), ("069960", "현대백화점"), ("004170", "신세계"), ("139480", "이마트"),
    ("000120", "CJ대한통운"), ("180640", "한진칼"), ("069620", "대웅제약"), ("000100", "유한양행"),
    ("185750", "종근당"), ("128940", "한미약품"), ("006280", "녹십자"), ("096530", "씨젠"),
    ("293490", "카카오게임즈"), ("086520", "에코프로"), ("247540", "에코프로비엠"), ("196170", "알테오젠"),
    ("028300", "HLB"), ("058470", "리노공업"), ("263750", "펄어비스"), ("253450", "스튜디오드래곤"),
    ("035900", "JYP Ent."), ("041510", "에스엠"), ("122870", "와이지엔터테인먼트"), ("068760", "셀트리온제약"),
]

ROW_RE = re.compile(
    r'\["(\d{8})",\s*([\d.]+),\s*([\d.]+),\s*([\d.]+),\s*([\d.]+),\s*(\d+)'
)


def _get(url):
    last_err = None
    for attempt in range(RETRIES):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except Exception as e:  # noqa: BLE001
            last_err = e
            if attempt < RETRIES - 1:
                time.sleep(1.5)
    raise last_err


def fetch_symbol_series(symbol):
    end = datetime.now()
    start = end - timedelta(days=560)  # 약 1.5년치 (거래일 기준 260일 이상 확보)
    url = (
        "https://api.finance.naver.com/siseJson.naver"
        f"?symbol={symbol}&requestType=1"
        f"&startTime={start.strftime('%Y%m%d')}&endTime={end.strftime('%Y%m%d')}&timeframe=day"
    )
    raw = _get(url)
    rows = []
    for m in ROW_RE.finditer(raw):
        date_raw, o, h, l, c, v = m.groups()
        iso = f"{date_raw[0:4]}-{date_raw[4:6]}-{date_raw[6:8]}"
        rows.append({
            "date": iso,
            "open": float(o), "high": float(h), "low": float(l), "close": float(c),
            "volume": int(v),
        })
    rows.sort(key=lambda r: r["date"])
    return rows


def main():
    parser = argparse.ArgumentParser(description="한글 종목 사전의 일별 시세를 미리 받아 저장")
    parser.add_argument("--out-dir", default="kr_stocks", help="저장할 폴더 (기본: kr_stocks)")
    args = parser.parse_args()

    import os
    os.makedirs(args.out_dir, exist_ok=True)

    ok, fail = 0, 0
    for symbol, name in KR_STOCK_LIST:
        print(f"  - {symbol} {name} 조회 중...", file=sys.stderr)
        try:
            series = fetch_symbol_series(symbol)
            if not series:
                raise ValueError("빈 응답")
            payload = {
                "symbol": symbol,
                "instrument_name": name,
                "exchange": "KRX",
                "currency": "KRW",
                "fetched_at": datetime.now().astimezone().isoformat(timespec="seconds"),
                "series": series,
            }
            out_path = os.path.join(args.out_dir, f"{symbol}.json")
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False)
            ok += 1
        except Exception as e:  # noqa: BLE001
            print(f"    실패: {type(e).__name__}: {e}", file=sys.stderr)
            fail += 1
        time.sleep(0.3)

    print(f"\n완료: 성공 {ok}건, 실패 {fail}건 -> {args.out_dir}/", file=sys.stderr)


if __name__ == "__main__":
    main()
