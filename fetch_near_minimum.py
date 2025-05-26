import requests
from datetime import datetime, timedelta

BASE_URL = "https://iss.moex.com/iss/"


def fetch_json(url, params=None):
    resp = requests.get(url, params=params)
    resp.raise_for_status()
    return resp.json()


def get_top_securities(limit=200):
    params = {
        "iss.meta": "off",
        "iss.only": "securities,marketdata",
        "sort_column": "VALTODAY",
        "sort_order": "desc",
        "limit": limit,
    }
    url = BASE_URL + "engines/stock/markets/shares/boards/TQBR/securities.json"
    data = fetch_json(url, params)

    secid_idx = data["securities"]["columns"].index("SECID")
    secids = [row[secid_idx] for row in data["securities"]["data"]]
    return secids


def get_min_price(secid, start, end):
    url = (
        BASE_URL
        + f"history/engines/stock/markets/shares/boards/TQBR/securities/{secid}.json"
    )
    params = {
        "from": start.strftime("%Y-%m-%d"),
        "till": end.strftime("%Y-%m-%d"),
        "iss.meta": "off",
        "iss.only": "history",
        "history.columns": "CLOSE",
    }
    data = fetch_json(url, params)
    close_idx = data["history"]["columns"].index("CLOSE")
    closes = [row[close_idx] for row in data["history"]["data"] if row[close_idx] is not None]
    return min(closes)


def get_current_price(secid):
    url = (
        BASE_URL
        + f"engines/stock/markets/shares/boards/TQBR/securities/{secid}.json"
    )
    params = {
        "iss.meta": "off",
        "iss.only": "marketdata",
        "marketdata.columns": "CLOSE",
    }
    data = fetch_json(url, params)
    close_idx = data["marketdata"]["columns"].index("CLOSE")
    close_price = data["marketdata"]["data"][0][close_idx]
    return close_price


def main():
    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=365 * 4)

    securities = get_top_securities()
    result = []
    for secid in securities:
        try:
            min_price = get_min_price(secid, start_date, end_date)
            current_price = get_current_price(secid)
        except Exception:
            continue
        if min_price == 0:
            continue
        diff = (current_price - min_price) / min_price
        if diff <= 0.15:
            result.append((secid, diff, current_price, min_price))

    result.sort(key=lambda x: x[1])

    for secid, diff, current, min_price in result[:20]:
        print(f"{secid}: {diff*100:.2f}% above min ({current} vs {min_price})")


if __name__ == "__main__":
    main()
