import os
import time
import asyncio
import json
import functools
import logging
import aiohttp
from web3 import Web3, AsyncWeb3
try:
    from web3.middleware import ExtraDataToPOAMiddleware as poa_middleware
except ImportError:
    try:
        from web3.middleware import geth_poa_middleware as poa_middleware
    except ImportError:
        poa_middleware = None

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("TriangularBot")

# ----------------- Configuration -----------------
RPC_URL = os.getenv("BSC_RPC_URL", "https://bsc-dataseed.binance.org/")
PRIVATE_KEY = os.getenv("PRIVATE_KEY", "")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS", "0x0000000000000000000000000000000000000000")
OWNER_ADDRESS = os.getenv("OWNER_ADDRESS", "0x0000000000000000000000000000000000000000")

# PancakeSwap Router & Factory
PANCAKE_ROUTER = "0x10ED43C718714eb63d5aA57B78B54704E256024E"
PANCAKE_FACTORY = "0xcA143Ce32Fe78f1f7019d7d551a6402fC5350c73"

# Token addresses (BSC)
WBNB = "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c"
BUSD = "0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56"
USDT = "0x55d398326f99059fF775485246999027B3197955"
CAKE = "0x0E09FaBB73Bd3Ade0a17ECC321fD13a19e81cE82"
ETH = "0x2170Ed0880ac9A755fd29B2688956BD959F933F8"   # BEP20 ETH
BTCB = "0x7130d2A12B9BCbFAe4f2634d864A1Ee1Ce3Ead9c"  # BEP20 BTC

TOKENS = [WBNB, BUSD, USDT, CAKE, ETH, BTCB]

# Minimal ABI for pairs, router, and contract
PAIR_ABI = json.loads('[{"constant":true,"inputs":[],"name":"getReserves","outputs":[{"internalType":"uint112","name":"_reserve0","type":"uint112"},{"internalType":"uint112","name":"_reserve1","type":"uint112"},{"internalType":"uint32","name":"_blockTimestampLast","type":"uint32"}],"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"token0","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"token1","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"}]')

ROUTER_ABI = json.loads('[{"inputs":[{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"}],"name":"getAmountsOut","outputs":[{"internalType":"uint256[]","name":"amounts","type":"uint256[]"}],"stateMutability":"view","type":"function"}]')

CONTRACT_ABI = json.loads('''
[
    "function executeArbitrage(address token1, address token2, address token3, uint256 amountIn, uint256 minProfit) external",
    "function totalProfit() view returns (uint256)",
    "function tradeCount() view returns (uint256)"
]
''')

# ----------------- Web3 Setup -----------------
def init_web3():
    try:
        w3_conn = Web3(Web3.HTTPProvider(RPC_URL))
        if poa_middleware:
            w3_conn.middleware_onion.inject(poa_middleware, layer=0)
        async_w3_conn = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(RPC_URL))
        if poa_middleware:
            async_w3_conn.middleware_onion.inject(poa_middleware, layer=0)
        return w3_conn, async_w3_conn
    except Exception as e:
        logger.warning(f"Web3 initialization notice: {e}")
        return None, None

w3, async_w3 = init_web3()

# ----------------- Helper Functions -----------------
@functools.lru_cache(maxsize=256)
def get_pair_address(token_a, token_b):
    """Compute PancakeSwap pair address (deterministic). Cached with LRU to avoid redundant keccak hashing in loops."""
    token0, token1 = (token_a, token_b) if token_a.lower() < token_b.lower() else (token_b, token_a)
    salt = Web3.solidity_keccak(['address', 'address'], [token0, token1])
    init_code_hash = "0x00fb7f630766e6a796048ea87d01acd3068e8ff67d078148a3fa3f4a84f69bd5"
    pair_address = Web3.to_checksum_address(
        Web3.keccak(hexstr="0xff" + PANCAKE_FACTORY[2:].lower() + salt.hex()[2:] + init_code_hash[2:])[12:].hex()
    )
    return pair_address

async def get_reserves(pair_address):
    """Fetch reserves for a pair asynchronously."""
    if not async_w3:
        return None
    contract = async_w3.eth.contract(address=pair_address, abi=PAIR_ABI)
    try:
        reserves = await contract.functions.getReserves().call()
        token0 = await contract.functions.token0().call()
        token1 = await contract.functions.token1().call()
        return {
            'token0': token0,
            'token1': token1,
            'reserve0': reserves[0],
            'reserve1': reserves[1]
        }
    except Exception:
        return None

async def get_amount_out(amount_in, reserve_in, reserve_out):
    """Calculate amount out using PancakeSwap fee (0.25%)."""
    amount_in_with_fee = amount_in * 9975  # 0.25% fee (9975/10000)
    numerator = amount_in_with_fee * reserve_out
    denominator = reserve_in * 10000 + amount_in_with_fee
    return numerator // denominator if denominator > 0 else 0

async def calculate_profit_for_path(path, amount_in):
    """Simulate a 3-leg triangular path and return profit in base currency (wei)."""
    current_amount = amount_in
    for i in range(len(path) - 1):
        token_in = path[i]
        token_out = path[i+1]
        pair_addr = get_pair_address(token_in, token_out)
        reserves = await get_reserves(pair_addr)
        if not reserves:
            return 0
        if reserves['token0'].lower() == token_in.lower():
            reserve_in = reserves['reserve0']
            reserve_out = reserves['reserve1']
        else:
            reserve_in = reserves['reserve1']
            reserve_out = reserves['reserve0']
        if reserve_in == 0 or reserve_out == 0:
            return 0
        current_amount = await get_amount_out(current_amount, reserve_in, reserve_out)
    return current_amount - amount_in

def calculate_confidence_score(gross_profit_wei, gas_cost_wei, amount_in_wei):
    """
    Calculate confidence score (0-100) and sizing multiplier for a triangular route.
    Optimizes win rate and filters marginal opportunities vulnerable to gas price shifts or MEV.
    """
    if gross_profit_wei <= gas_cost_wei:
        return 0.0, 0.0

    net_profit_wei = gross_profit_wei - gas_cost_wei
    profit_margin_pct = (net_profit_wei / amount_in_wei) * 100.0 if amount_in_wei > 0 else 0.0

    confidence = 100.0

    # Deduct if profit margin is below 0.5%
    if profit_margin_pct < 0.5:
        confidence -= 30.0
    elif profit_margin_pct < 1.0:
        confidence -= 15.0

    # Deduct if gas cost consumes > 30% of gross profit
    gas_share = (gas_cost_wei / gross_profit_wei) if gross_profit_wei > 0 else 1.0
    if gas_share > 0.5:
        confidence -= 40.0
    elif gas_share > 0.3:
        confidence -= 20.0

    confidence = max(0.0, min(100.0, confidence))

    if confidence >= 80.0:
        sizing_multiplier = 1.0
    elif confidence >= 60.0:
        sizing_multiplier = 0.5
    else:
        sizing_multiplier = 0.25

    return confidence, sizing_multiplier

async def find_best_triangular_path(amount_in=Web3.to_wei(1, 'ether')):
    """Multi-path search for best triangular arbitrage among supported tokens."""
    best_profit = 0
    best_path = None
    start = WBNB
    for t1 in TOKENS:
        if t1 == start:
            continue
        for t2 in TOKENS:
            if t2 == start or t2 == t1:
                continue
            path = [start, t1, t2, start]
            profit = await calculate_profit_for_path(path, amount_in)
            if profit > best_profit:
                best_profit = profit
                best_path = path
    return best_path, best_profit

def estimate_gas_cost(gas_price=None):
    """Estimate total gas cost for 3-leg arbitrage execution."""
    if gas_price is None:
        gas_price = w3.eth.gas_price if (w3 and w3.is_connected()) else 3000000000  # 3 gwei fallback
    gas_used = 500000  # Estimated gas usage for 3 swaps + overhead
    return gas_price * gas_used

async def send_arbitrage_transaction(path, amount_in, min_profit):
    """Call smart contract's executeArbitrage function."""
    if not w3 or not PRIVATE_KEY or PRIVATE_KEY == "":
        logger.info("[SIMULATION EXECUTION] Simulated transaction call for path: %s", [t[:6] for t in path])
        return True

    account = w3.eth.account.from_key(PRIVATE_KEY)
    contract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=CONTRACT_ABI)
    nonce = w3.eth.get_transaction_count(account.address)
    gas_price = w3.eth.gas_price
    tx = contract.functions.executeArbitrage(
        path[0], path[1], path[2], amount_in, min_profit
    ).build_transaction({
        'from': account.address,
        'nonce': nonce,
        'gas': 800000,
        'gasPrice': gas_price,
    })
    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
    logger.info("Transaction sent: %s", tx_hash.hex())
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    if receipt.status == 1:
        logger.info("Arbitrage executed successfully!")
        return True
    else:
        logger.error("Transaction failed")
        return False

def print_strategy_disclaimer():
    """Print disclaimer on realistic daily return expectations in live market environments."""
    logger.info(
        "[DISCLAIMER] High daily profit rates depend on market volatility, pool reserves, "
        "gas prices, and MEV front-running competition. The bot enforces strict profitability "
        "filters to ensure trades execute only when estimated net yield is positive after all costs."
    )

# ----------------- Main Loop -----------------
async def main():
    logger.info("Starting PancakeSwap Triangular Arbitrage Bot (Python + Solidity Hybrid)...")
    print_strategy_disclaimer()

    if w3 and w3.is_connected():
        logger.info("Connected to BSC: %s", RPC_URL)
        logger.info("Contract: %s", CONTRACT_ADDRESS)
    else:
        logger.info("Running in simulation mode (RPC connection pending)...")

    amount_in = Web3.to_wei(1, 'ether')
    min_profit_threshold = Web3.to_wei(0.001, 'ether')

    while True:
        try:
            logger.info("Scanning for triangular arbitrage...")
            path, profit = await find_best_triangular_path(amount_in)

            if path and profit > min_profit_threshold:
                gas_cost = estimate_gas_cost()
                confidence, multiplier = calculate_confidence_score(profit, gas_cost, amount_in)
                adjusted_amount_in = int(amount_in * multiplier)

                net_profit = profit - gas_cost
                if net_profit > 0 and confidence >= 50.0:
                    logger.info("Found profitable triangular path: %s", [t[:6] for t in path])
                    logger.info(
                        "Gross: %f BNB, Gas: %f BNB, Net: %f BNB, Confidence: %.1f%%",
                        Web3.from_wei(profit, 'ether'),
                        Web3.from_wei(gas_cost, 'ether'),
                        Web3.from_wei(net_profit, 'ether'),
                        confidence
                    )

                    success = await send_arbitrage_transaction(path, adjusted_amount_in, profit // 2)
                    if success:
                        logger.info("Waiting 30 sec before next scan...")
                        await asyncio.sleep(30)
                        continue
                else:
                    logger.info("Path found but net profit too low after gas or confidence below threshold.")
            else:
                logger.info("No profitable triangular opportunity found.")

            await asyncio.sleep(5)

        except KeyboardInterrupt:
            logger.info("Bot stopped by user.")
            break
        except Exception as e:
            logger.error("Error in main loop: %s", e)
            await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(main())
