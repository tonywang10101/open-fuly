import os
from dotenv import load_dotenv

load_dotenv()

BF_API_PK = os.getenv("BF_API_PK")
BF_API_SAK = os.getenv("BF_API_SAK")


from bfxapi import Client, REST_HOST
from bfxapi.types import (
    PlatformStatus,
    FundingCurrencyBook,
    FundingStatistic,
    Notification,
)
from bfxapi.rest.exceptions import GenericError
from typing import List, Tuple

# Doc: https://github.com/bitfinexcom/bitfinex-api-py
bfx = Client(rest_host=REST_HOST, api_key=BF_API_PK, api_secret=BF_API_SAK)
import time
from pprint import pprint
import datetime
import numpy as np


def get_abailable_balance(wallet_type: str, currency: str) -> float:
    """
    Sample Return
    ```
    Wallet(
        wallet_type='funding',
        currency='UST',
        balance=244058.19339195,
        unsettled_interest=0,
        available_balance=1e-06,
        last_change=None,
        trade_details=None
    )
    ```
    """
    for wallet in bfx.rest.auth.get_wallets():
        # if wallet.wallet_type == 'funding' and wallet.currency == 'UST':
        if wallet.wallet_type == wallet_type and wallet.currency == currency:
            return wallet.available_balance  # wallet.balance
    raise ValueError(f"No available balance for {currency} in {wallet_type}")


def get_p4_price_range() -> Tuple[float, float]:
    """get P4 price range"""
    # print(">>>>>>>>>>>>>>>>>> get_f_book P4")
    f_book: List[FundingCurrencyBook] = bfx.rest.public.get_f_book(
        currency="fUST", precision="P4", len=250
    )
    accm_amount = 0
    order_books = [{"rate": 0.02, "accm_amount": 0}]
    for book in f_book:
        if book.amount > 0:
            pert_rate = book.rate * 100
            accm_amount += book.amount
            if len(order_books) == 0:
                order_books.append({"rate": pert_rate, "accm_amount": accm_amount})
            elif pert_rate > order_books[-1]["rate"]:
                order_books.append({"rate": pert_rate, "accm_amount": accm_amount})
            else:
                order_books[-1]["accm_amount"] = accm_amount

    # print(f'rate: {book.rate*100}, amount: {auum_amount}')
    if order_books[0]["accm_amount"] > 1000000:
        print("no good order ... consirder frr")
        print(">>>>>>>>>>>>>>>>>> get_funding_stats")
        funding_statics: List[FundingStatistic] = bfx.rest.public.get_funding_stats(
            symbol="fUST"
        )
        frr = funding_statics[-1].frr * 100
        print(f"FRR = {frr:.8f}")
        print("<<<<<<<<<<<<<<<<<< ")
        if order_books[0]["rate"] < 0.1:
            # TODO: check p2 or p1
            return (frr, 0.1)
        else:
            return (0.1, order_books[0]["rate"])
    else:
        # find gap
        target_gap_end_index = 0
        accm_amount = [order_books[i]["accm_amount"] for i in range(len(order_books))]
        gap_diff = np.diff(accm_amount)
        # mean_diff = np.mean(gap_diff)
        std_diff = np.std(gap_diff)
        # print(f'[DEBUG] mean_diff: {mean_diff:,}')
        # print(f'[DEBUG] std_diff: {std_diff:,}')

        # accm_mean = np.mean(accm_amount)
        # accm_std = np.std(accm_amount)
        # print(f'[DEBUG] accm_mean: {accm_mean:,}')
        # print(f'[DEBUG] accm_std: {accm_std:,}')

        for i, order_book in enumerate(order_books):
            gap = order_book["accm_amount"] - order_book["accm_amount"]
            if gap > std_diff or order_book["accm_amount"] > 3000000:
                target_gap_end_index = i
                break

        lower_rate_bound = order_books[target_gap_end_index - 1]["rate"]
        upper_rate_bound = order_books[target_gap_end_index]["rate"]
        # print(f'[DEBUG] Target Gap: {lower_rate_bound} ~ {upper_rate_bound}')
        return (lower_rate_bound, upper_rate_bound)


def get_p2_price_range(lower, upper) -> Tuple[float, float]:
    """get price range for P2"""
    f_book: List[FundingCurrencyBook] = bfx.rest.public.get_f_book(
        currency="fUST", precision="P3", len=250
    )
    accm_amount = 0
    order_books = [{"rate": 0.02, "accm_amount": 0}]
    for book in f_book:
        if book.amount > 0:
            pert_rate = book.rate * 100
            accm_amount += book.amount
            if pert_rate < lower:
                continue
            if len(order_books) == 0:
                order_books.append({"rate": pert_rate, "accm_amount": accm_amount})
            elif pert_rate > order_books[-1]["rate"]:
                order_books.append({"rate": pert_rate, "accm_amount": accm_amount})
            else:
                order_books[-1]["accm_amount"] = accm_amount

    if order_books[0]["accm_amount"] > 1000000:
        if order_books[0]["rate"] < 0.027:
            return (0.027, order_books[0]["rate"])
        else:
            return (order_books[0]["rate"], upper)
    else:
        # find gap
        target_gap_end_index = 0
        accm_amount = [order_books[i]["accm_amount"] for i in range(len(order_books))]
        gap_diff = np.diff(accm_amount)
        # mean_diff = np.mean(gap_diff)
        std_diff = np.std(gap_diff)
        # print(f'[DEBUG] mean_diff: {mean_diff:,}')
        # print(f'[DEBUG] std_diff: {std_diff:,}')

        # accm_mean = np.mean(accm_amount)
        # accm_std = np.std(accm_amount)
        # print(f'[DEBUG] accm_mean: {accm_mean:,}')
        # print(f'[DEBUG] accm_std: {accm_std:,}')

        for i, order_book in enumerate(order_books):
            gap = order_book["accm_amount"] - order_book["accm_amount"]
            if gap > std_diff or order_book["accm_amount"] > 1000000:
                target_gap_end_index = i
                break

        lower_rate_bound = max(0.027, order_books[target_gap_end_index - 1]["rate"])
        upper_rate_bound = max(0.027, order_books[target_gap_end_index]["rate"])
        # print(f'[DEBUG] Target Gap: {lower_rate_bound} ~ {upper_rate_bound}')
        return (lower_rate_bound, upper_rate_bound)


def cancel_orders():
    """cancel all orders"""
    print("[DEBUG] Canceling all orders")
    cancel_status: Notification = bfx.rest.auth.cancel_all_funding_offers(
        currency="fUST"
    )
    if cancel_status.status != "SUCCESS":
        raise ValueError("Canceling orders failed")


def put_orders(balance, lower, upper, unit=1000):
    """put orders between bound"""
    print(f"[DEBUG] balance: {balance}, lower: {lower}, upper: {upper}, cut: {unit}")
    unit = max(unit, 150)
    num_cut = balance // unit + 1
    incremental = (upper - lower) / num_cut
    order_idx = 0
    while balance > 150:
        target_amount = min(balance, unit)
        target_rate = (lower + order_idx * incremental) / 100
        target_period = 120 if target_rate > 0.087 / 100 else 2
        print(
            f"[DEBUG] Putting ${target_amount} on {target_rate} with {target_period} days"
        )
        try:

            result: Notification = bfx.rest.auth.submit_funding_offer(
                type="LIMIT",
                symbol="fUST",
                amount=target_amount,
                rate=target_rate,
                period=120,
            )
            pprint(result)
        except GenericError as e:
            print(f"[ERROR] When submit funding odder get `{e}`")
            break
        balance -= unit
        order_idx += 1


if __name__ == "__main__":
    # Strategy for USDT
    while True:
        print(datetime.datetime.now())
        platformStatus: PlatformStatus = bfx.rest.public.get_platform_status()
        if platformStatus.status != 1:
            raise ValueError("Bitfinex Platform Not Working !")

        usdt_balance = get_abailable_balance(wallet_type="funding", currency="UST")
        UST_LOWER_BOUNDARY_FOR_FUNDING = 150
        print(f"[LOG] {datetime.datetime.now()}")
        print(f"[DEBUG] UST balance: {usdt_balance:,.2f}")
        if usdt_balance < UST_LOWER_BOUNDARY_FOR_FUNDING:
            print(f"[WARNING] UST balance less then {UST_LOWER_BOUNDARY_FOR_FUNDING}")
        else:
            lower_rate_bound, upper_rate_bound = get_p4_price_range()
            print(f"[DEBUG](p4): ({lower_rate_bound:.4f},{upper_rate_bound:.4f})")
            lower_rate_bound, upper_rate_bound = get_p2_price_range(
                lower_rate_bound, upper_rate_bound
            )
            print(f"[DEBUG](p2): ({lower_rate_bound:.4f},{upper_rate_bound:.4f})")
            cancel_orders()
            put_orders(usdt_balance, lower_rate_bound, upper_rate_bound, unit=500)
        print("----\n")
        time.sleep(300)

############################################
# Other APIs for funding currency          #
############################################

# print(">>>>>>>>>>>>>>>>>> get_f_book P0")
# f_book: List[FundingCurrencyBook] = bfx.rest.public.get_f_book(currency='fUST', precision="P0", len=100)
# pprint(f_book)
# print("<<<<<<<<<<<<<<<<<< ")
# print(">>>>>>>>>>>>>>>>>> get_f_book P1")
# f_book: List[FundingCurrencyBook] = bfx.rest.public.get_f_book(currency='fUST', precision="P1", len=100)
# pprint(f_book)
# print("<<<<<<<<<<<<<<<<<< ")
# print(">>>>>>>>>>>>>>>>>> get_f_book P2")
# f_book: List[FundingCurrencyBook] = bfx.rest.public.get_f_book(currency='fUST', precision="P2", len=100)
# pprint(f_book)
# print("<<<<<<<<<<<<<<<<<< ")
# print(">>>>>>>>>>>>>>>>>> get_f_book P3")
# f_book: List[FundingCurrencyBook] = bfx.rest.public.get_f_book(currency='fUST', precision="P3", len=100)
# pprint(f_book)
# print("<<<<<<<<<<<<<<<<<< ")

# Below are some api might needed in futures
# # Not so useful for now
# print(">>>>>>>>>>>>>>>>>> get_f_ticker")
# pprint(bfx.rest.public.get_f_ticker(symbol='fUST'))
# print("<<<<<<<<<<<<<<<<<< ")


# # # Too many information
# print(">>>>>>>>>>>>>>>>>> get_f_raw_book")
# pprint(bfx.rest.public.get_f_raw_book(currency='fUST', len=100))
# print("<<<<<<<<<<<<<<<<<< ")

# FRR might be useful


# # Don't know why no info
# print(">>>>>>>>>>>>>>>>>> get_candles_hist")
# pprint(bfx.rest.public.get_candles_hist(symbol='fUST', tf='15m'))
# print("<<<<<<<<<<<<<<<<<< ")
