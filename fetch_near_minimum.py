import requests
from datetime import date, datetime, timedelta
from urllib.parse import urlencode

BASE_URL = "https://iss.moex.com/iss/"     # оставь как в твоём проекте                             

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
    valtoday_idx = data["marketdata"]["columns"].index("VALTODAY")

    result = []
    securities_rows = data["securities"]["data"]
    market_rows = data["marketdata"]["data"]
    for sec_row, market_row in zip(securities_rows, market_rows):
        secid = sec_row[secid_idx]
        volume = market_row[valtoday_idx]
        result.append((secid, volume))

    return result


def get_min_price(secid, start, end, count_batch = 100):
    """Минимальный дневной LOW за последние 4 года (GAZP → TQBR)."""
    if count_batch > 100:
        count_batch = 100

    url = (
        BASE_URL
        + f"history/engines/stock/markets/shares/boards/TQBR/"
        + f"securities/{secid}.json"
    )

    lows, start = [], 0
    # print(f'start_date 1 {start}')
    # print(f'start_date 1 {start.strftime("%Y-%m-%d")}')
    # print(f'end_date 1 {end.strftime("%Y-%m-%d")}')
    while True:
        params = {
            "from": start,
            "till": end,
            "iss.meta": "off",
            "iss.only": "history",
            "history.columns": "CLOSE",
            "limit": count_batch,
            "start": start,
        }

        full_url = f"{url}?{urlencode(params)}"
        # print("GET", full_url)

        data  = fetch_json(url, params)
        rows  = data["history"]["data"]          # [[LOW], ...]
        # print(f'rows {len(rows)}')
        if not rows:                             # страницы кончились
            break
        lows.extend(row[0] for row in rows if row[0] is not None)
        if len(rows) < count_batch:                     # последняя страница
            break
        start += count_batch                            # следующая порция
    return min(lows) if lows else None


def get_current_price(secid: str, board: str = "TQBR") -> float | None:
    """
    Возвращает текущую цену бумаги (LAST).  
    Если LAST отсутствует (например, биржа закрыта), берёт PREVCLOSE.
    Печатает фактически отправляемый HTTP-запрос.
    """
    url = (
        BASE_URL
        + f"engines/stock/markets/shares/boards/{board}/"
        + f"securities/{secid}.json"
    )

    params = {
        "iss.meta": "off",
        "iss.only": "marketdata",
        "marketdata.columns": "SECID,LAST,PREVCLOSE",
    }

    full_url = f"{url}?{urlencode(params)}"
    # print("GET", full_url)

    data    = fetch_json(url, params)
    cols    = data["marketdata"]["columns"]
    values  = data["marketdata"]["data"][0]

    # Индексы нужных колонок
    idx_last       = cols.index("LAST")       if "LAST"       in cols else None
    idx_prevclose  = cols.index("PREVCLOSE")  if "PREVCLOSE"  in cols else None

    last_price = values[idx_last] if idx_last is not None else None
    if last_price is None:                    # биржа закрыта → используем предыдущий close
        last_price = values[idx_prevclose] if idx_prevclose is not None else None

    return float(last_price) if last_price is not None else None

def main():
    start_date = (date.today() - timedelta(days=4 * 365)).isoformat()
    print(f'start_date {start_date}')
    end_date   = date.today().isoformat()
    print(f'end_date {end_date}')

    limit_top = 100
    securities = get_top_securities(limit_top)
    count_index_current = len(securities)
    print(f'top {limit_top} = {count_index_current} штук')
    if count_index_current == 0:
        raise Exception('не получили не одной компании из топов')
    result = []
    result_more = []
    for i, (secid, volume) in enumerate(securities):
        print(f'secid {secid} {i+1}/{count_index_current}')
        try:
            min_price = get_min_price(secid, start_date, end_date)
            print(f'min_price {min_price}')
            current_price = get_current_price(secid)
            print(f'current_price {current_price}')
            if current_price is None:
                continue
        except Exception:
            # raise Exception('не смогли получить минимальное и текущее значение {secid}')
            print('не смогли получить минимальное и текущее значение {secid}')
            # continue
        if min_price == 0:
            # print(f'минимальная цена {secid} = 0')
            continue
        diff = (current_price - min_price) / min_price
        if diff <= 0.15:
            print(f'diff у {secid} = {diff}')
            result.append((secid, diff, current_price, min_price, volume))
        elif diff <= 1:
            print(f'diff у {secid} = {diff}')
            result_more.append((secid, diff, current_price, min_price, volume))
        else:
            print(f'diff у {secid} = {diff}')

    result.sort(key=lambda x: x[1])
    print(len(result))
    for secid, diff, current, min_price, volume in result:
        print(f"{secid}: {diff*100:.2f}% above min ({current} vs {min_price}) volume {volume}")
    print(f'\n\n diff меньше 1\n')
    result_more.sort(key=lambda x: x[1])
    print(len(result_more))
    for secid, diff, current, min_price, volume in result_more:
        print(f"{secid}: {diff*100:.2f}% above min ({current} vs {min_price}) volume {volume}")


if __name__ == "__main__":
    main()
