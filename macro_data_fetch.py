#!/usr/bin/env python3
"""
거시경제·주식 추세 예측 체크리스트 - 매크로 데이터 자동조회 스크립트

체크리스트 V3.1의 '01 매크로' 단계에서 참고할 수 있는 공개 지표를
API 키 없이 무료 공개 소스(Yahoo Finance, Frankfurter, 미국 재무부, 뉴욕 연준)에서
가져와 JSON으로 출력합니다. 하이일드 스프레드(OAS)는 무료 키 없는 공개 API가 없어
자동조회 대상에서 제외되며 항상 수동으로 확인해야 합니다.

이 스크립트는 점수를 대신 매기지 않습니다. 원 체크리스트의 원칙대로
"근거를 함께 적는다"를 돕기 위해 원자료(수준 + 5/20/60거래일 변화)만
정리해 보여줍니다. 최종 -2~+2 점수는 사용자가 직접 판단해서 매깁니다.

출력된 JSON은 웹 앱(체크리스트 스코어카드)의
"매크로 자동조회 데이터 붙여넣기" 칸에 그대로 붙여넣으면
관련 항목의 참고 메모에 자동 반영됩니다.

사용법:
    python macro_data_fetch.py
    python macro_data_fetch.py --out data.json
"""

import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

# Windows에서 stdout이 파일/파이프로 리다이렉트되면 콘솔 코드페이지(chcp)와 무관하게
# 시스템 기본 ANSI 코드페이지(cp949 등)로 인코딩되어 한글이 깨질 수 있다.
# UTF-8로 고정해 항상 일관된 결과가 나오도록 한다.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
TIMEOUT = 10
RETRIES = 2


def _get(url, headers=None):
    last_err = None
    for attempt in range(RETRIES):
        try:
            req = urllib.request.Request(url, headers=headers or {"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except Exception as e:  # noqa: BLE001
            last_err = e
            if attempt < RETRIES - 1:
                time.sleep(1.5)
    raise last_err


def fetch_yahoo_series(symbol, range_="6mo", interval="1d"):
    """Yahoo Finance 차트 API에서 종가 시계열을 가져온다."""
    url = (
        "https://query1.finance.yahoo.com/v8/finance/chart/"
        f"{urllib.parse.quote(symbol, safe='')}?range={range_}&interval={interval}"
    )
    raw = _get(url)
    data = json.loads(raw)
    result = data["chart"]["result"][0]
    timestamps = result["timestamp"]
    closes = result["indicators"]["quote"][0]["close"]
    series = [
        (datetime.fromtimestamp(t, tz=timezone.utc).strftime("%Y-%m-%d"), c)
        for t, c in zip(timestamps, closes)
        if c is not None
    ]
    return series


def fetch_treasury_real_yield_10y(years=None):
    """미국 재무부 공식 사이트에서 10년물 실질금리(TIPS 기준) 시계열을 가져온다 (키 불필요).
    fred.stlouisfed.org는 이 환경에서 접속이 막혀 있어 대신 사용한다."""
    if years is None:
        years = [datetime.now().year]
    series = []
    for year in years:
        url = (
            "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/"
            f"daily-treasury-rates.csv/{year}/all?type=daily_treasury_real_yield_curve"
            f"&field_tdr_date_value={year}&page&_format=csv"
        )
        raw = _get(url)
        lines = raw.strip().splitlines()
        header = lines[0].split(",")
        try:
            idx10 = [h.strip().strip('"') for h in header].index("10 YR")
        except ValueError:
            continue
        for line in lines[1:]:
            parts = line.split(",")
            if len(parts) <= idx10:
                continue
            date_raw, val_raw = parts[0], parts[idx10]
            if val_raw in ("", "N/A"):
                continue
            try:
                m, d, y = date_raw.split("/")
                iso_date = f"{y}-{m.zfill(2)}-{d.zfill(2)}"
                series.append((iso_date, float(val_raw)))
            except ValueError:
                continue
    series.sort(key=lambda x: x[0])
    return series


def fetch_ny_fed_effr():
    """뉴욕 연준 공식 API에서 실효 기준금리(EFFR) 시계열을 가져온다 (키 불필요)."""
    url = "https://markets.newyorkfed.org/api/rates/unsecured/effr/last/120.json"
    raw = _get(url)
    data = json.loads(raw)
    rows = data.get("refRates", [])
    series = [(r["effectiveDate"], r["percentRate"]) for r in rows if "percentRate" in r]
    series.sort(key=lambda x: x[0])
    return series


def fetch_usdkrw_frankfurter():
    """Frankfurter(ECB 데이터 기반)에서 USD/KRW 환율 시계열(최근 6개월)을 가져온다."""
    url = "https://api.frankfurter.dev/v1/2026-02-01..?base=USD&symbols=KRW"
    try:
        raw = _get(url)
        data = json.loads(raw)
        rates = data.get("rates", {})
        series = [(d, v["KRW"]) for d, v in sorted(rates.items()) if "KRW" in v]
        if series:
            return series
    except Exception:
        pass
    # 시계열 조회 실패 시 최신값만
    url = "https://api.frankfurter.dev/v1/latest?base=USD&symbols=KRW"
    raw = _get(url)
    data = json.loads(raw)
    return [(data["date"], data["rates"]["KRW"])]


def pick_change(series, back_points=(5, 20, 60)):
    """시계열에서 최신값과 N개 데이터포인트 전 대비 변화를 계산한다."""
    if not series:
        return None
    latest_date, latest_val = series[-1]
    out = {"latest_date": latest_date, "latest": round(latest_val, 4)}
    for n in back_points:
        idx = len(series) - 1 - n
        if idx >= 0:
            ref_date, ref_val = series[idx]
            out[f"vs_{n}pts_ago"] = {
                "date": ref_date,
                "value": round(ref_val, 4),
                "change": round(latest_val - ref_val, 4),
            }
    return out


def safe_fetch(fn):
    try:
        return {"ok": True, "data": fn()}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def compute_breakeven(nominal_item, real_item):
    """10년 기대인플레이션 ≈ 명목금리 - 실질금리. 두 시계열의 발표일이 정확히 일치하지 않을 수 있어
    같은 위치(최신/N포인트 전)끼리 근사로 뺀 값이다. fred.stlouisfed.org의 T10YIE가 이 환경에서
    접속되지 않아 대신 계산한다."""
    if not (nominal_item["ok"] and nominal_item["data"] and real_item["ok"] and real_item["data"]):
        return {"ok": False, "error": "명목금리 또는 실질금리 조회 실패로 계산 불가"}
    nd, rd = nominal_item["data"], real_item["data"]
    out = {"latest_date": nd["latest_date"], "latest": round(nd["latest"] - rd["latest"], 4)}
    for k in ("vs_5pts_ago", "vs_20pts_ago", "vs_60pts_ago"):
        if k in nd and k in rd:
            out[k] = {
                "date": nd[k]["date"],
                "value": round(nd[k]["value"] - rd[k]["value"], 4),
                "change": round(out["latest"] - round(nd[k]["value"] - rd[k]["value"], 4), 4),
            }
    return {"ok": True, "data": out, "approx": True}


def build_result():
    result = {
        "fetched_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "source_note": "공개 무료 API(Yahoo Finance, Frankfurter, 미국 재무부, 뉴욕 연준)에서 조회한 참고 데이터입니다. "
        "투자 조언이 아니며, 점수는 사용자가 직접 판단해서 매깁니다.",
        "items": {},
    }

    plan = [
        ("usdkrw", "원/달러 환율 (USD/KRW)", lambda: pick_change(fetch_usdkrw_frankfurter())),
        ("vix", "VIX 지수", lambda: pick_change(fetch_yahoo_series("^VIX"))),
        ("kospi", "KOSPI 지수", lambda: pick_change(fetch_yahoo_series("^KS11"))),
        ("us10y_nominal", "미국 10년물 명목금리(%)", lambda: pick_change(fetch_yahoo_series("^TNX"))),
        ("us10y_real", "미국 10년물 실질금리(TIPS, %)",
         lambda: pick_change(fetch_treasury_real_yield_10y([datetime.now().year, datetime.now().year - 1]))),
        ("fed_funds_rate", "연준 실효 기준금리(EFFR, %)", lambda: pick_change(fetch_ny_fed_effr())),
    ]

    for key, label, fn in plan:
        print(f"  - {label} 조회 중...", file=sys.stderr)
        res = safe_fetch(fn)
        res["label"] = label
        result["items"][key] = res
        time.sleep(0.5)

    print("  - 10년 기대인플레이션(%) 계산 중...", file=sys.stderr)
    be = compute_breakeven(result["items"]["us10y_nominal"], result["items"]["us10y_real"])
    be["label"] = "10년 기대인플레이션(%, 명목-실질 근사치)"
    result["items"]["breakeven_inflation"] = be

    result["items"]["hy_oas_spread"] = {
        "ok": False,
        "error": "이 항목은 무료 키 없는 공개 API가 없어 자동조회를 지원하지 않습니다. "
        "FRED(BAMLH0A0HYM2) 웹사이트나 증권사 HTS/앱에서 직접 확인해 메모에 적어 주세요.",
        "label": "하이일드 스프레드(OAS, %)",
    }

    return result


def main():
    parser = argparse.ArgumentParser(description="매크로 체크리스트 참고 데이터 자동조회")
    parser.add_argument("--out", help="결과를 저장할 JSON 파일 경로 (생략 시 화면 출력만)")
    args = parser.parse_args()

    print("매크로 데이터를 조회하는 중입니다 (공개 무료 API, 몇 초 소요)...", file=sys.stderr)
    result = build_result()
    out_json = json.dumps(result, ensure_ascii=False, indent=2)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(out_json)
        print(f"\n저장 완료: {args.out}", file=sys.stderr)
        print("이 파일 내용을 체크리스트 웹 앱의 '자동조회 데이터 붙여넣기' 칸에 붙여넣으세요.", file=sys.stderr)
    else:
        print(out_json)


if __name__ == "__main__":
    main()
