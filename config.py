from datetime import datetime
from pathlib import Path

""" https://www.bybit.com/app/user/api-management - link to create API-key and API-secret """

""" Coin to sell """
COIN = 'SUI'

MIN_PRICE: float = 2
list_time = datetime(year=2023, month=5, day=3, hour=15, minute=0, second=0)
COEFFICIENT = 1
""" time.is - website to watch time
If they lag behind - (how far behind) 
If they're in a hurry (how much hurry) """

correction = 0
list_time = list_time.timestamp() + correction
project_root = Path(__file__).parent
