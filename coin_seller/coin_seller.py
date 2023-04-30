from pybit.exceptions import InvalidRequestError
from datetime import datetime
from loguru import logger
from pybit import spot
from math import floor
from json import dumps
from time import (
    time,
    sleep,
)

from config import (
    COIN,
    list_time,
    COEFFICIENT,
    project_root,
    MIN_PRICE,
)

from asyncio import (
    AbstractEventLoop,
    coroutine,
    run,
)


class Result:
    def __init__(self, order_id: str, balance: str, price: float) -> None:
        self.balance = balance
        self.order_id = order_id
        self.price = price


class CoinSeller:
    def __init__(self, name: str, api_key: str, api_secret: str, proxy: str) -> None:
        self.account_name = name
        self.session_auth = spot.HTTP(
            endpoint='https://api.bybit.com',
            api_key=api_key,
            api_secret=api_secret)
        self.session_auth.client.proxies.update({'https': proxy, 'http': proxy})
        self.balance_before_selling = None
        self.balance_after_selling = None

    async def start(self) -> None:
        logger.info('Waiting for listing...')
        last_time = 0
        while True:
            now = floor(time())
            if list_time > now and last_time != now:
                logger.info(f'Time before sending requests: {round(list_time - now)} seconds')
            last_time = now
            if list_time < now:
                await self.check_balance()
                break

    async def check_price_and_qty(self, balance: str) -> None:
        no_orders = True
        while no_orders:
            try:
                logger.info('Looking for the best price...')
                check = self.session_auth.best_bid_ask_price(
                    symbol=f'{COIN}USDT')
                price = (round(float(check['result']['bidPrice']) * COEFFICIENT, 4))
                logger.info(f'Best price found: {price}')
                if MIN_PRICE >= price:
                    continue
                await self.sell_tokens(price, balance)
                no_orders = False
            except InvalidRequestError as ex:
                logger.info(f'It seems that there is no orders yet: {ex}')
                sleep(0.2)
                continue

    async def check_balance(self) -> None:
        balance_request = self.session_auth.get_wallet_balance()
        names = [name['coinName'] for name in balance_request['result']['balances']]
        balance_check = [balance['total'] for balance in balance_request['result']['balances']]
        zip_balances = list(zip(names, balance_check))
        logger.info(f'Checking balance... | {self.account_name}')
        for name, balance in zip_balances:
            if name == COIN:
                self.balance_before_selling = float(balance)
                logger.info(f'{balance, COIN} | {self.account_name}')
                await self.check_price_and_qty(balance)

    async def cancel_order(self, order_id: str, balance: str, price: float) -> None:
        try:
            self.session_auth.cancel_active_order(orderId=order_id)
            logger.info(f'Order deleted | {self.account_name}')
            await self.check_price_and_qty(balance)
        except InvalidRequestError:
            logger.success(f'Completed. | {self.account_name}')
            result = Result(order_id, balance, price)
            self.process_results([result])

    async def check_balance_after_selling(self, order_id: str, price: float) -> None:

        balance_request = self.session_auth.get_wallet_balance()
        names = [name['coinName'] for name in balance_request['result']['balances']]
        balance_check = [balance['total'] for balance in balance_request['result']['balances']]
        zip_balances = list(zip(names, balance_check))
        logger.info(f'Checking balance... | {self.account_name}')
        for name, balance in zip_balances:
            if name == COIN and float(balance) > 10:
                logger.info(balance, COIN, '|', self.account_name)
                await self.cancel_order(order_id, balance, price)
            elif name == COIN and float(balance) < 10:
                logger.info(f'Completed. | {self.account_name}')
                result = Result(order_id, balance, price)
                self.balance_after_selling = float(balance)
                self.process_results([result])

    async def sell_tokens(self, price: float, balance: str) -> None:
        n_digits = 2
        factor = 10 ** n_digits
        try:
            qty = floor(float(balance) * factor) / factor
            req = self.session_auth.place_active_order(
                symbol=f'{COIN}USDT',
                side='Sell',
                type='LIMIT',
                price=price,
                qty=qty,
                timeInForce="GTC",
                recvWindow=10000)
            order_id = req['result']['orderId']
            logger.info(f'An order for {qty} coins at price of {price} placed')
            await self.check_balance_after_selling(order_id, price)
        except InvalidRequestError as ex:
            logger.error(ex)
            await self.check_price_and_qty(balance)

    def process_results(self, results: list[Result]) -> None:
        requests_data = []
        for result in results:
            try:
                requests_data.append({
                    'Account name': self.account_name,
                    'Price': result.price,
                    'Balance before selling': self.balance_before_selling,
                    'Balance after selling': float(result.balance),
                    'Order id': result.order_id,
                    'Result': f'You sold {self.balance_before_selling - self.balance_after_selling} tokens',
                })
            except AttributeError:
                continue

        data = {
            'requests_data': requests_data,
        }
        json_text = dumps(data, indent=4, ensure_ascii=False)
        self.write_to_file(json_text)

    def write_to_file(self, data: str) -> None:
        filename = self.account_name + '-' + datetime.now().strftime('%Y-%m-%d %H-%M-%S.json')
        directory = project_root / 'logs'
        path = directory / filename
        directory.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as file:
            file.write(data)

    def run(self) -> None:
        start_event_loop(self.start())


def start_event_loop(coroutine: coroutine) -> AbstractEventLoop:
    try:
        return run(coroutine)
    except RuntimeError as ex:
        logger.info(f'Something went wrong | {ex}')
