import os
from decimal import Decimal
from dotenv import load_dotenv

load_dotenv()

# Load from environment if present; fall back to hardcoded defaults
RPC_URL: str = os.getenv("RPC_URL", "https://mainnet.optimism.io")
PRIVATE_KEY: str = os.getenv("PRIVATE_KEY", "")
WALLET_ADDRESS: str = os.getenv("WALLET_ADDRESS", "")

# Sleep interval between trades (seconds)
SLEEP_INTERVAL: int = int(os.getenv("SLEEP_INTERVAL", "600"))

# Velodrome v2 Router (Optimism) — official deployment per Velodrome repo
# Note: User message listed 0xa132...F9c9 which is not the Velodrome v2 router. Make configurable.
VELO_ROUTER_ADDRESS: str = os.getenv(
    "VELO_ROUTER_ADDRESS",
    "0xa062aE8A9c5e11aaA026fc2670B0D65cCc8B2858",
)

# Velodrome PoolFactory (needed for Route.factory)
VELO_POOL_FACTORY: str = os.getenv(
    "VELO_POOL_FACTORY",
    "0xF1046053aa5682b4F9a81b5481394DA16BE5FF5a",
)

# Default tokens on Optimism
# DAI:  0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1
# USDC.e (bridged): 0x7F5c764cBc14f9669B88837ca1490cCa17c31607
TOKEN_IN_ADDRESS: str = os.getenv(
    "TOKEN_IN_ADDRESS",
    "0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1",
)
TOKEN_OUT_ADDRESS: str = os.getenv(
    "TOKEN_OUT_ADDRESS",
    "0x7F5c764cBc14f9669B88837ca1490cCa17c31607",
)

# Swap amount in units of TOKEN_IN (human, not wei). Can be overridden by CLI.
SWAP_AMOUNT: str = os.getenv("SWAP_AMOUNT", "10")  # e.g., 10 DAI

# Slippage tolerance as percent (e.g., 0.3 means 0.3%)
SLIPPAGE_PERCENT: Decimal = Decimal(os.getenv("SLIPPAGE_PERCENT", "0.3"))

# Fixed assumed rebate per tx in USD (placeholder)
ASSUMED_REBATE_USD: Decimal = Decimal(os.getenv("ASSUMED_REBATE_USD", "0.25"))

# Gas price to use (wei). 0.001 gwei = 1_000_000 wei
GAS_PRICE_WEI: int = int(os.getenv("GAS_PRICE_WEI", str(1_000_000)))

# Chain ID for Optimism mainnet
CHAIN_ID: int = int(os.getenv("CHAIN_ID", "10"))