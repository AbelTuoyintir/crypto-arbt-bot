import os
import time
import asyncio
import json
import aiohttp
from web3 import Web3, AsyncWeb3
from web3.middleware import geth_poa_middleware
from dotenv import load_dotenv
import numpy as np

load_dotenv()

# ----------------- Configuration -----------------
RPC_URL = os.getenv("BSC_RPC_URL")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")
OWNER_ADDRESS = os.getenv("OWNER_ADDRESS")

# PancakeSwap Router & Factory
PANCAKE_ROUTER = "0x10ED43C718714eb63d5aA57B78B54704E256024E"
PANCAKE_FACTORY = "0xcA143Ce32Fe78f1f7019d7d551a6402fC5350c73"

# Token addresses (BSC)
WBNB = "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c"
BUSD = "0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56"
USDT = "0x55d398326f99059fF775485246999027B3197955"
CAKE = "0x0E09FaBB73Bd3Ade0a17ECC321fD13a19e81cE82"
ETH = "0x2170Ed0880ac9A755fd29B2688956BD959F933F8"  # BEP20 ETH
BTCB = "0x7130d2A12B9BCbFAe4f2634d864A1Ee1Ce3Ead9c"  # BEP20 BTC

TOKENS = [WBNB, BUSD, USDT, CAKE, ETH, BTCB]

# Minimal ABI for pairs, router, and our contract
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
w3 = Web3(Web3.HTTPProvider(RPC_URL))
w3.middleware_onion.inject(geth_poa_middleware, layer=0)  # BSC requires PoA middleware
if not w3.is_connected():
    raise Exception("Failed to connect to BSC node")

account = w3.eth.account.from_key(PRIVATE_KEY)
contract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=CONTRACT_ABI)

async_w3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(RPC_URL))
async_w3.middleware_onion.inject(geth_poa_middleware, layer=0)

# ----------------- Helper Functions -----------------
def get_pair_address(token_a, token_b):
    """Compute PancakeSwap pair address (deterministic)."""
    token0, token1 = (token_a, token_b) if token_a.lower() < token_b.lower() else (token_b, token_a)
    salt = Web3.solidity_keccak(['address', 'address'], [token0, token1])
    # PancakeSwap init code hash
    init_code_hash = "0x00fb7f630766e6a796048ea87d01acd3068e8ff67d078148a3fa3f4a84f69bd5"
    pair_address = Web3.to_checksum_address(
        Web3.keccak(hexstr="0xff" + PANCAKE_FACTORY[2:].lower() + salt.hex()[2:] + init_code_hash[2:])[12:].hex()
    )
    return pair_address

async def get_reserves(pair_address):
    """Fetch reserves for a pair."""
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
    except Exception as e:
        return None

async def get_amount_out(amount_in, reserve_in, reserve_out):
    """Calculate amount out using PancakeSwap fee (0.25%)."""
    amount_in_with_fee = amount_in * 9975  # 0.25% fee (9975/10000)
    numerator = amount_in_with_fee * reserve_out
    denominator = reserve_in * 10000 + amount_in_with_fee
    return numerator // denominator

async def calculate_profit_for_path(path, amount_in):
    """Simulate a triangular path and return profit in WBNB."""
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

async def find_best_triangular_path(amount_in=Web3.to_wei(1, 'ether')):
    """Brute-force search for best triangular arbitrage among supported tokens."""
    best_profit = 0
    best_path = None
    # Only consider paths that start and end with WBNB
    start = WBNB
    # Iterate over all combinations of 2 intermediate tokens
    for t1 in TOKENS:
        if t1 == start: continue
        for t2 in TOKENS:
            if t2 == start or t2 == t1: continue
            path = [start, t1, t2, start]
            profit = await calculate_profit_for_path(path, amount_in)
            if profit > best_profit:
                best_profit = profit
                best_path = path
    return best_path, best_profit

def estimate_gas_cost(gas_price=None):
    """Estimate gas cost for arbitrage execution."""
    if gas_price is None:
        gas_price = w3.eth.gas_price
    # Estimated gas usage for 3 swaps + overhead
    gas_used = 500000
    return gas_price * gas_used

async def send_arbitrage_transaction(path, amount_in, min_profit):
    """Call contract's executeArbitrage function."""
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
    print(f"Transaction sent: {tx_hash.hex()}")
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    if receipt.status == 1:
        print("Arbitrage executed successfully!")
        return True
    else:
        print("Transaction failed")
        return False

# ----------------- Main Loop -----------------
async def main():
    print("Starting PancakeSwap Arbitrage Bot (Python + Solidity Hybrid)...")
    print(f"Connected to BSC: {RPC_URL}")
    print(f"Contract: {CONTRACT_ADDRESS}")

    # Optional: check contract stats
    profit_wei = contract.functions.totalProfit().call()
    trades = contract.functions.tradeCount().call()
    print(f"Contract stats: Total profit = {Web3.from_wei(profit_wei, 'ether')} BNB, Trades = {trades}")

    # Main scanning loop
    amount_in = Web3.to_wei(1, 'ether')  # Trade size (can be dynamic)
    min_profit_threshold = Web3.to_wei(0.001, 'ether')  # 0.001 BNB minimum

    while True:
        try:
            print(f"\n[{time.strftime('%H:%M:%S')}] Scanning for triangular arbitrage...")
            path, profit = await find_best_triangular_path(amount_in)
            
            if path and profit > min_profit_threshold:
                # Check if profit > gas cost
                gas_cost = estimate_gas_cost()
                net_profit = profit - gas_cost
                if net_profit > 0:
                    print(f"Found profitable path: {[t[:6] for t in path]}")
                    print(f"Gross profit: {Web3.from_wei(profit, 'ether')} BNB, Gas: {Web3.from_wei(gas_cost, 'ether')} BNB, Net: {Web3.from_wei(net_profit, 'ether')} BNB")
                    
                    # Execute trade
                    success = await send_arbitrage_transaction(path, amount_in, profit // 2)  # Allow some slippage
                    if success:
                        print("Waiting 30 sec before next scan...")
                        await asyncio.sleep(30)
                        continue
                else:
                    print(f"Profit {Web3.from_wei(profit, 'ether')} BNB too low after gas.")
            else:
                print("No profitable opportunity found.")
            
            await asyncio.sleep(5)  # Scan every 5 seconds

        except KeyboardInterrupt:
            print("Bot stopped by user.")
            break
        except Exception as e:
            print(f"Error in main loop: {e}")
            await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(main())