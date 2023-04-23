from coin_seller.coin_seller import CoinSeller
from json import load
from multiprocessing import (
    Process,
    freeze_support,
)

with open('./data/accounts.json', 'r', encoding='utf-8-sig') as file:
    config = load(file)

accounts_data = [account for account in config['accounts']]


def main() -> None:
    freeze_support()
    for account in accounts_data:
        coin_seller = CoinSeller(account['name'], account['api_key'], account['api_secret'], account['proxy'])
        process = Process(target=coin_seller.run)
        process.start()


if __name__ == '__main__':
    main()
