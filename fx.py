import requests
from inputimeout import inputimeout, TimeoutOccurred
import sys, sqlite3, re
from datetime import datetime
from decimal import Decimal, ROUND_DOWN, ROUND_UP

"""
Python 3.11
tuple (qty, subqty) guide:
    subqty to 2 digits for quantities of currencies:
        E.g. (12,34) = 12.34, (12,3) = 12.03
    subqty to 4 digits for fx exchange rates:
        E.g. (12,3456) = 12.3456, (12,3) = 12.0003
"""

if __name__ == "__main__":
    # https://currencybeacon.com/signup
    API_KEY = ""

    # https://currencybeacon.com/supported-currencies
    BASE_CURRENCY = "USD"
    FX_CURRENCIES = ["EUR", "GBP", "JPY", "CNY"]
    CURRENCIES = [BASE_CURRENCY] + FX_CURRENCIES

    # new users start with (10000,0) = 10000.00 BASE_CURRENCY
    BASE_START_QTY = 10000
    BASE_START_SUBQTY = 0


def main():
    print("=== Currency Trader ===")
    # check if portfolio and history tables already exist, if not, create them
    try:
        cursor.execute("SELECT * FROM portfolio LIMIT 1")
        cursor.execute("SELECT * FROM history LIMIT 1")
        print("Welcome back\n")
    except sqlite3.OperationalError:
        reset_portfolio()

    # main menu
    while True:
        print(
            "=== Main Menu ===",
            "1. Portfolio",
            "2. FX Rates",
            "3. Buy FX",
            "4. Sell FX",
            "5. History",
            "6. Reset",
            "7. Exit",
            sep="\n"
        )
        # validate menu choice
        while True:
            menu = input("\tChoice: ").strip()
            if menu in [str(x) for x in range(1, 8)]:
                print()
                break

        # call menu functions
        if menu == "1":
            print_portfolio()
        elif menu == "2":
            print_rates()
        elif menu == "3":
            buy_fx()
        elif menu == "4":
            sell_fx()
        elif menu == "5":
            print_history()
        elif menu == "6":
            # reset all portfolio holdings and history to default values
            print("=== Reset Portfolio ===")
            print("Portfolio will be wiped")
            while True:
                confirmed = input("Confirm (y/n): ").strip().lower()
                if confirmed in ["y", "yes"]:
                    reset_portfolio()
                    break
                elif confirmed in ["n", "no"]:
                    print("Cancelled\n")
                    break
        elif menu == "7":
            db.close()
            print("Goodbye!")
            break


def create_tables():
    """Creates default portfolio and history tables"""
    # create new table: portfolio: contains details of all holdings
    cursor.execute("CREATE TABLE portfolio (currency TEXT, qty INTEGER, subqty INTEGER)")

    # initialise table data: portfolio: all currencies except base start with 0.00
    portfolio = [(currency, 0, 0) for currency in FX_CURRENCIES]
    # base currency is the first in the database
    portfolio.insert(0, (BASE_CURRENCY, BASE_START_QTY, BASE_START_SUBQTY))
    cursor.executemany("INSERT INTO portfolio VALUES (?,?,?)", portfolio)

    # create new table: history: contains details of all transactions
    # all entries (excluding id) to be TEXT
    cursor.execute(
        "CREATE TABLE history (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, currency TEXT, delta_fx TEXT, delta_base TEXT)")

    # initialise table data: history: initial history entry is the addition of the starting base amount only
    cursor.execute("INSERT INTO history (date, delta_base) VALUES (?,?)",
                   (datetime.now(), tuple2dp_to_str((BASE_START_QTY, BASE_START_SUBQTY))))

    db.commit()


def drop_tables():
    """Drops portfolio and history tables"""
    cursor.execute("DROP TABLE IF EXISTS portfolio")
    cursor.execute("DROP TABLE IF EXISTS history")
    db.commit()


def get_portfolio() -> dict[str, tuple[int, int]]:
    """
    Gets portfolio from database and returns as dict
    :return: Portfolio as dict {key = currency, value = (qty, subqty)} with subqty to 2 digits
    """
    # get portfolo from database
    cursor.execute("SELECT currency, qty, subqty FROM portfolio")
    portfolio_list = cursor.fetchall()
    # return portfolio as dict
    return {row[0]: (row[1], row[2]) for row in portfolio_list}


def update_portfolio(currency: str, delta_fx: tuple[int, int], delta_base: tuple[int, int]):
    """
    Updates portfolio and history tables in database with passed currency transaction details
    :param currency: FX currency (not base) as string E.g. "JPY"
    :param delta_fx: Change in fx as (qty, subqty) where 1 qty = 100 subqty (+ve = buy, -ve = sell)
    :param delta_base: Change in base as (qty, subqty) where 1 qty = 100 subqty (+ve = buy, -ve = sell)
    """
    # get old fx quantity
    cursor.execute("SELECT qty, subqty FROM portfolio WHERE currency = ?", (currency,))
    fx_old = cursor.fetchone()
    # new fx quantity = old + delta
    fx_new = tuple2dp_add(fx_old, delta_fx)

    # get old base quantity
    cursor.execute("SELECT qty, subqty FROM portfolio WHERE currency = ?", (BASE_CURRENCY,))
    base_old = cursor.fetchone()
    # new base quantity = old + delta
    base_new = tuple2dp_add(base_old, delta_base)

    # update portfolio and history tables
    cursor.execute("UPDATE portfolio SET qty = ?, subqty = ? WHERE currency = ?", (fx_new[0], fx_new[1], currency))
    cursor.execute("UPDATE portfolio SET qty = ?, subqty = ? WHERE currency = ?",
                   (base_new[0], base_new[1], BASE_CURRENCY))
    cursor.execute("INSERT INTO history (date, currency, delta_fx, delta_base) VALUES (?,?,?,?)",
                   (datetime.now(), currency, tuple2dp_to_str(delta_fx), tuple2dp_to_str(delta_base)))
    db.commit()


def get_rates(fx_instruction) -> dict[str, tuple[int, int]]:
    """
    Gets fx rates from API and returns as dict
    :param fx_instruction: Instruction for the fx currency as "buy" or "sell" only
    :return: FX rates in fx per base as dict {key = currency, value = (qty, subqty)} where 1 qty = 10000 subqty
    """
    # fx_instruction must be "buy" or "sell", we get the worse 4dp rounded rate based on the instruction
    if fx_instruction not in ["buy", "sell"]:
        raise ValueError("get_rates takes argument 'buy' or 'sell' only")

    # API url to return JSON format
    url = "https://api.currencybeacon.com/v1/latest?api_key=" + API_KEY \
          + "&base=" + BASE_CURRENCY + "&symbols=" + ",".join(FX_CURRENCIES)

    # API call and error handling
    try:
        data = requests.get(url).json()
    except Exception:
        sys.exit("API timeout")
    if data["meta"]["code"] != 200:
        sys.exit(f"API error code {data['meta']['code']}")

    # creation of dictionary and rate data error handling
    rates = {}
    for currency in data["response"]["rates"]:
        rate = data["response"]["rates"][currency]
        if not isinstance(rate, (float, int)):
            sys.exit(f"API returned non-numeric rate. 1 {BASE_CURRENCY} = {currency} {rate}")
        if data["response"]["rates"][currency] <= 0:
            sys.exit(f"API returned non-positive rate. 1 {BASE_CURRENCY} = {currency} {rate}")

        # return the worse 4dp rounded rate based on the instruction
        if fx_instruction == "buy":
            rates[currency] = (int(rate), int(str(Decimal(rate).quantize(Decimal("0.0001"), rounding=ROUND_DOWN))[-4:]))
        else:
            rates[currency] = (int(rate), int(str(Decimal(rate).quantize(Decimal("0.0001"), rounding=ROUND_UP))[-4:]))

    return rates


def portfolio_value() -> float:
    """
    Gets portfolio and returns its value in base currency as if all fx holdings were to be sold at current fx rates
    :return: Portfolio value in BASE_CURRENCY as float
    """
    # get portfolio and rates
    portfolio = get_portfolio()
    rates = get_rates("sell")

    # calculate and return portfolio value
    value = 0
    for currency in portfolio:
        if currency == BASE_CURRENCY:
            value += portfolio[currency][0] + (portfolio[currency][1] / 100)
        else:
            value += (portfolio[currency][0] + (portfolio[currency][1] / 100)) / (
                    rates[currency][0] + rates[currency][1] / 10000)
    return value


def portfolio_return(base_float: float | int) -> str:
    """
    Returns percentage return as str given portfolio value as float
    :param base_float: Portfolio value in BASE_CURRENCY as a float or int
    :return: Percentage return to 2 decimal places as string E.g. "11.11%"
    """
    return f"{((base_float / (BASE_START_QTY + BASE_START_SUBQTY / 100)) - 1) * 100:.2f}%"


def get_quantity_owned(currency: str) -> tuple[int, int]:
    """Gets and returns quantity of currency currently owned in portfolio
    :param currency: Currency to be queried
    :return: Quantity of currency owned as (qty, subqty) where 1 qty = 100 subqty
    """
    cursor.execute("SELECT qty, subqty FROM portfolio WHERE currency = ?", (currency,))
    return cursor.fetchone()


def base_text(number: float | int | tuple[int, int]) -> str:
    """Returns the number as a base currency formatted str
    :param number: float, int or (qty, subqty) with subqty to 2 digits
    :return: Base currency formatted str to 2 decimal places E.g. "USD X.XX"
    """
    if isinstance(number, (float, int)):
        return f"{BASE_CURRENCY} {number:.2f}"
    elif isinstance(number, tuple):
        return f"{BASE_CURRENCY} {(number[0] + number[1] / 100):.2f}"


# returns fx received for base spent
def fx_received(fx_rate: tuple[int, int], base_spent: tuple[int, int]) -> tuple[int, int]:
    """Returns quantity fx received for a given fx rate and quantity base spent
    :param fx_rate: FX rate in fx per base as (qty, subqty) where 1 qty = 10000 subqty
    :param base_spent: Quantity base spent as (qty, subqty) where 1 qty = 100 subqty
    :return: Quantity fx received as (qty, subqty) where 1 qty = 100 subqty
    """
    # error handling
    if not isinstance(fx_rate, tuple) or not isinstance(base_spent, tuple):
        raise TypeError
    if not len(fx_rate) == len(base_spent) == 2:
        raise ValueError
    for i in [fx_rate[0], fx_rate[1], base_spent[0], base_spent[1]]:
        if not isinstance(i, int):
            raise TypeError
        if i < 0:
            raise ValueError
    if fx_rate[0] == fx_rate[1] == 0 or fx_rate[1] > 9999 or base_spent[1] > 99:
        raise ValueError
    # fx_received_1e8 = (base_spent * fx_rate) * 1e8
    fx_received_1e8 = (base_spent[0] * 10000 + base_spent[1] * 100) * (fx_rate[0] * 10000 + fx_rate[1])
    # fx_received_1e8_str is padded to allow string splicing in all cases
    fx_received_1e8_str = "0" * 9 + str(fx_received_1e8)

    # fx_qty is anything except the last 8 digits (which represent all decimals)
    fx_qty = int(fx_received_1e8_str[:-8])
    # fx_subqty is the first two digits (indexes -8,-7), i.e. the quantity received is always rounded down to 2dps
    fx_subqty = int(fx_received_1e8_str[-8:-6])

    return (fx_qty, fx_subqty)


# returns base received for fx spent
def base_received(fx_rate: tuple[int, int], fx_spent: tuple[int, int]) -> tuple[int, int]:
    """Returns quantity base received a given fx rate and quantity fx spent
    :param fx_rate: FX rate in fx per base as (qty, subqty) where 1 qty = 10000 subqty
    :param fx_spent: Quantity fx spent as (qty, subqty) where 1 qty = 100 subqty
    :return: Quantity base received as (qty, subqty) where 1 qty = 100 subqty
    """
    # error handling
    if not isinstance(fx_rate, tuple) or not isinstance(fx_spent, tuple):
        raise TypeError
    if not len(fx_rate) == len(fx_spent) == 2:
        raise ValueError
    for i in [fx_rate[0], fx_rate[1], fx_spent[0], fx_spent[1]]:
        if not isinstance(i, int):
            raise TypeError
        if i < 0:
            raise ValueError
    if fx_rate[0] == fx_rate[1] == 0 or fx_rate[1] > 9999 or fx_spent[1] > 99:
        raise ValueError
    # fx_rate_1e4 = fx_rate * 1e4,  fx_spent_1e8 = fx_spent * 1e8
    fx_rate_1e4 = (fx_rate[0] * 10000 + fx_rate[1])
    fx_spent_1e8 = (fx_spent[0] * 10000 + fx_spent[1] * 100) * 10000

    # start with just base_qty received via integer division
    base_qty = (fx_spent[0] * 10000 + fx_spent[1] * 100) // fx_rate_1e4
    base_subqty = 0

    # add 1 to base_subqty received until doing so would cause implied fx_spent to exceed actual fx_spent
    while base_subqty < 100:
        base_subqty += 1
        fx_spent_implied_1e8 = (base_qty * 10000 + base_subqty * 100) * fx_rate_1e4
        if fx_spent_implied_1e8 > fx_spent_1e8:
            return (base_qty, base_subqty - 1)


# returns None for non-numbers, or any number more precise than 2 decimal places
# otherwise, returns a qty, subqty tuple of ints
def str_to_tuple2dp(s: str) -> tuple[int, int]:
    """Returns (qty, subqty) tuple given valid string of decimal number, ValueError otherwise
    :param s: String of decimal number with max precision to 2 decimal places (excluding trailing zeroes)
    :return: Number as (qty, subqty) where 1 qty = 100 subqty
    """
    # regex to catch all string form decimal numbers with max precision of 2 dps
    # allows leading and trailing 0 (even after 2 dps), decimals, ints, but not "." as 0
    if re.search(r"^([0-9]+\.?|[0-9]*\.[0-9]{1,2}0*)$", s):
        # cleaning to allow splitting and splicing in all valid cases
        if "." in s:
            s = "0" + s + "00"
        else:
            s += ".00"
        # qty = everything before the decimal place
        # subqty = first two digits after the decimal place
        qty = int(s.split(".")[0])
        subqty = int(s.split(".")[1][:2])
        return (qty, subqty)

    # fails regex
    raise ValueError("non-numeric or precision exceeds 2 decimal places")


def tuple2dp_to_str(quantity: tuple[int, int], decimal_places: int = 2) -> str:
    """Returns string of decimal number of (qty,subqty) with subqty to decimal_places digits (default 2)
    :param quantity: (qty, subqty) with subqty to decimal_places digits
    :param decimal_places: Precision of subqty where subqty has actual value subqty/(10**decimal_places)
    :return: Decimal quantity as string E.g. "12.05" when quantity=(12,5) and decimal_places=2
    """
    # invalid decimal_places: must be >= 1
    if decimal_places <= 0:
        raise ValueError("decimal_places is non-positive")
    # invalid tuples: all items not non-negative or non-positive
    if quantity[0] < 0 < quantity[1] or quantity[0] > 0 > quantity[1]:
        raise ValueError("items not all non-negative or non-positive")

    # in string form, pad subqty to decimal_places
    if quantity[1] < 0:
        # in string form, remove negative sign from subqty only
        return f"{quantity[0]}.{-quantity[1]:{'0'}{decimal_places}}"
    return f"{quantity[0]}.{quantity[1]:{'0'}{decimal_places}}"


def tuple2dp_greaterthan(a: tuple[int, int], b: tuple[int, int]) -> bool:
    """
    Returns whether a > b
    :param a: (qty, subqty) where 1 qty = 100 subqty
    :param b: (qty, subqty) where 1 qty = 100 subqty
    :return: True or False whether a > b
    """
    return a[0] * 100 + a[1] > b[0] * 100 + b[1]


def tuple2dp_add(a: tuple[int, int], b: tuple[int, int]) -> tuple[int, int]:
    """
    Returns a + b as (qty, subqty)
    :param a: (qty, subqty) where 1 qty = 100 subqty
    :param b: (qty, subqty) where 1 qty = 100 subqty
    :return: a + b as (qty, subqty) where 1 qty = 100 subqty
    """
    # invalid tuple: all items not non-negative or non-positive
    for t in [a, b]:
        if (t[0] < 0 < t[1]) or (t[0] > 0 > t[1]):
            raise ValueError("items not all non-negative or non-positive")

    # add qty and subqty separately
    c_qty = a[0] + b[0]
    c_subqty = a[1] + b[1]
    # handle cases where subqty impacts qty
    if c_qty == 0:
        if c_subqty <= -100:
            c_qty -= 1
            c_subqty += 100
        elif c_subqty >= 100:
            c_qty += 1
            c_subqty -= 100
    elif c_qty > 0:
        if c_subqty < 0:
            c_qty -= 1
            c_subqty += 100
        elif c_subqty >= 100:
            c_qty += 1
            c_subqty -= 100
    elif c_qty < 0:
        if c_subqty > 0:
            c_qty += 1
            c_subqty -= 100
        elif c_subqty <= -100:
            c_qty -= 1
            c_subqty += 100

    return (c_qty, c_subqty)


# ===Main Menu Options===

def print_portfolio():
    """Print all portfolio holdings, base equivalent value, and percentage return"""
    portfolio = get_portfolio()
    print("=== Portfolio ===")
    for currency in portfolio:
        print(f"{currency}: {tuple2dp_to_str(portfolio[currency])}")
    value = portfolio_value()
    print(f"Value: {base_text(value)}")
    print(f"Return: {portfolio_return(value)}\n")


def print_rates():
    """Print fx rates in fx per base for all fx currencies"""
    rates = get_rates("buy")
    print("=== FX Rates ===")
    for currency in rates:
        print(f"1 {BASE_CURRENCY} = {currency} {tuple2dp_to_str(rates[currency], decimal_places=4)}")
    print()


def buy_fx():
    """Process of buying fx for base"""
    print("=== Buy FX ===")

    # user to input valid fx currency
    print(f"Currencies available: {', '.join(FX_CURRENCIES)}")
    fx_selected = input("\tCurrency to buy: ").strip().upper()
    if fx_selected not in FX_CURRENCIES:
        print("\tInvalid currency\n")
        return

    # (qty, subqty) of base currently owned
    base_owned = get_quantity_owned(BASE_CURRENCY)
    print(f"{BASE_CURRENCY} available: {tuple2dp_to_str(base_owned)}")

    # user to input valid amount of base to spend
    try:
        base_spent = str_to_tuple2dp(input(f"\tQuantity of {BASE_CURRENCY} to spend: ").strip())
    except ValueError:
        print("\tInvalid quantity: non-numeric or too precise\n")
        return
    if base_spent[0] == base_spent[1] == 0:
        print("\tInvalid quantity: zero\n")
        return
    if tuple2dp_greaterthan(base_spent, base_owned):
        print("\tInsufficient funds\n")
        return

    # get fx received for base spent and ask user to confirm within 10 seconds
    fx_bought = fx_received(get_rates("buy")[fx_selected], base_spent)
    print("Quote expires in 10 seconds")
    print(f"\tBuy {fx_selected} {tuple2dp_to_str(fx_bought)} for {BASE_CURRENCY} {tuple2dp_to_str(base_spent)}")
    try:
        confirmed = inputimeout("\t\tConfirm (y/n): ", timeout=10).strip().lower()
    except TimeoutOccurred:
        print("\t\tQuote expired\n")
        return
    if confirmed in ["y", "yes"]:
        update_portfolio(fx_selected, fx_bought, (-base_spent[0], -base_spent[1]))
        print("\t\tConfirmed\n")
    elif confirmed in ["n", "no"]:
        print("\t\tCancelled\n")
    else:
        print("\t\tInvalid confirmation\n")


def sell_fx():
    """Process of selling fx for base"""
    print("=== Sell FX ===")

    # user to input valid fx currency
    print(f"Currencies available: {', '.join(FX_CURRENCIES)}")
    fx_selected = input("\tCurrency to sell: ").strip().upper()
    if fx_selected not in FX_CURRENCIES:
        print("\tInvalid currency\n")
        return

    # (qty, subqty) of fx currently owned
    fx_owned = get_quantity_owned(fx_selected)
    print(f"{fx_selected} available: {tuple2dp_to_str(fx_owned)}")

    # user to input valid amount of fx to sell
    try:
        fx_spent = str_to_tuple2dp(input(f"\tQuantity of {fx_selected} to sell: ").strip())
    except ValueError:
        print("\tInvalid quantity: non-numeric or too precise\n")
        return
    if fx_spent[0] == fx_spent[1] == 0:
        print("\tInvalid quantity: zero\n")
        return
    if tuple2dp_greaterthan(fx_spent, fx_owned):
        print("\tInsufficient funds\n")
        return

    # get base received for fx spent and ask user to confirm within 10 seconds
    base_bought = base_received(get_rates("sell")[fx_selected], fx_spent)
    print("Quote expires in 10 seconds")
    print(f"\tBuy {BASE_CURRENCY} {tuple2dp_to_str(base_bought)} for {fx_selected} {tuple2dp_to_str(fx_spent)}")
    try:
        confirmed = inputimeout("\t\tConfirm (y/n): ", timeout=10).strip().lower()
    except TimeoutOccurred:
        print("\t\tQuote expired\n")
        return
    if confirmed in ["y", "yes"]:
        update_portfolio(fx_selected, (-fx_spent[0], -fx_spent[1]), base_bought)
        print("\t\tConfirmed\n")
    elif confirmed in ["n", "no"]:
        print("\t\tCancelled\n")
    else:
        print("\t\tInvalid confirmation\n")


def reset_portfolio():
    """Wipes all tables and prints confirmation message"""
    drop_tables()
    create_tables()
    print(f"You start with {base_text((BASE_START_QTY, BASE_START_SUBQTY))}\n")


def print_history():
    """Prints history of all transactions"""
    # get all transactions
    cursor.execute("SELECT date, currency, delta_fx, delta_base FROM history")
    history = cursor.fetchall()

    # print all transactions (special for first transaction = starting base amount)
    print("=== History ===")
    for i, row in enumerate(history, 1):
        if i == 1:
            print(f"{row[0]}\tStarting: \t{BASE_CURRENCY} {row[3]}")
            continue
        print(f"{row[0]}\t{row[1]} {row[2]}\t{BASE_CURRENCY} {row[3]}")
    print()


if __name__ == "__main__":
    # initialise database and its cursor
    try:
        db = sqlite3.connect('db')
        cursor = db.cursor()
    except Exception:
        sys.exit("Could not open/create database")
    main()