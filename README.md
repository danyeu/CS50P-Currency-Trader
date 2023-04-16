# Currency Trader

### Overview
* "Currency Trader" is a Python application in which users can try to profit by buying and selling foreign currencies with prop money.

### Tech
* The app is coded in Python 3.11 and the latest version of Python is recommended for end users.
    * Non-standard libraries required: requests, inputimeout (+pytest for unit tests.)
    * Throughout the app, floating point values are generally avoided due to the importance of precision in finance.
        * Currency quantities and exchange rates are handled as a tuple pair of integers, with custom functions to handle their addition, multiplication, division, etc. without the involvement of floats.
        * When rounding is needed, precautions are taken to round to the worst output in terms of quantities or exchange rates for the user, so as to not create arbitrage opportunities.
* SQLite manages the databases of currencies owned and transaction history.
* Live exchange rates are obtained through CurrenyBeacon's API (https://currencybeacon.com/).

### Usage
* The app includes 7 main menu options which can be accessed by inputting the respective number via standard input.

##### 1. Portfolio
* Displays quantities owned of all currencies, and the whole portfolio's total equivalent value in USD and the equivalent percentage return.
* The base currency is USD, meaning that all transactions involve either buying or selling USD.
* Foreign currencies available are EUR, GBP, JPY, CNY.
* A brand new portfolio starts with USD 10,000.00
    * Purchasing foreign currencies costs USD, and selling foreign currencies returns USD.
* **Tech**:
    * All data is stored in an SQLite database.
    * Currency quantities are stored as a pair of integers representing the quantity (whole number) and sub-quantity (decimal values) of the currency. All currencies have a maximum precision of up to two decimal places (i.e. 100 sub-quantity = 1 quantity).
        * E.g. (123,4) = 123.04, (123,45) = 123.45
    * Exchange rates are stored similarly but with a maximum precision of up to four decimal places (i.e. 10,000 sub-quantity = 1 quantity).
        * E.g. (123,4) = 123.0004, (123,4567) = 123.4567 foreign currency per 1 USD.

##### 2. FX Rates
* Displays current exchange rates for all foreign currencies as quantity foreign currency per 1 USD.
    * The rates displayed are for buying foreign currencies.
* **Tech**:
    * These are live exchange rates obtained from CurrenyBeacon's API in JSON format.
        * The API key is a global variable at the top of the code.
    * Rates are received as floats from the API, but are converted to a pair of ints with rounding depending on whether the trade instruction is to buy or sell (user receives worse rounding).

##### 3. Buy FX / 4. Sell FX
* Allows the user to purchase foreign currency with USD, or purchase USD with foreign currency.
* The user is asked for the foreign currency, and quantity of USD or foreign currency to spend.
* A trade quote is then displayed and is valid for 10 seconds before it expires.
* **Tech**:
    * Regex validates the user enters a valid quantity up to a maximum precision of 2 decimal places.
        * Any number of leading zeros in quantity, and trailing zeros in sub-quantity are allowed.
    * Other validation includes the currency inputted, and whether there are sufficient funds.
    * The exchange rate received is rounded down to 4 decimal places when buying foreign currency, and rounded up when selling.
        * This gives the user the worse exchange rate which is expected (although bid-ask spreads are not explicitly implemented in this app.)
    * With all transactions, the quantity of currency received is rounded down to 2 decimal places.
        * This again is a conservative measure to prevent arbitrage.

##### 5. History
* Displays all transactions made.
* **Tech**:
    * Queries the history database and prints all transactions in a user-friendly format.

##### 6. Reset
* Resets all persistent databases to default values (i.e. starting with USD 10,000.00 only).
* **Tech**:
    * Drops all tables and re-initiates them with default values.

##### 7. Exit
* Exits the app.