import json
import os
import sys
from getpass import getpass
from typing import Optional

import requests
from eth_account import Account

DEFAULTS = {
    "RPC_URL": "https://mainnet.optimism.io",
    "SLEEP_INTERVAL": "600",
    "VELO_ROUTER_ADDRESS": "0xa062aE8A9c5e11aaA026fc2670B0D65cCc8B2858",
    "VELO_POOL_FACTORY": "0xF1046053aa5682b4F9a81b5481394DA16BE5FF5a",
    "TOKEN_IN_ADDRESS": "0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1",  # DAI
    "TOKEN_OUT_ADDRESS": "0x7F5c764cBc14f9669B88837ca1490cCa17c31607",  # USDC.e
    "SWAP_AMOUNT": "10",
    "SLIPPAGE_PERCENT": "0.3",
    "ASSUMED_REBATE_USD": "0.25",
    "GAS_PRICE_WEI": "1000000",  # 0.001 gwei
    "CHAIN_ID": "10",
}

ABI_API_URL = "https://api-optimistic.etherscan.io/api"


def prompt(prompt_text: str, default: Optional[str] = None, secret: bool = False) -> str:
    if secret:
        value = getpass(f"{prompt_text} ")
        if not value and default is not None:
            return default
        return value
    else:
        if default is None:
            return input(f"{prompt_text} ").strip()
        entered = input(f"{prompt_text} [{default}] ").strip()
        return entered or default


def is_address(addr: str) -> bool:
    return addr.startswith("0x") and len(addr) == 42


def fetch_router_abi(address: str, api_key: Optional[str]) -> Optional[list]:
    try:
        params = {
            "module": "contract",
            "action": "getabi",
            "address": address,
        }
        if api_key:
            params["apikey"] = api_key
        resp = requests.get(ABI_API_URL, params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") == "1":
            abi_json = json.loads(data.get("result", "[]"))
            if isinstance(abi_json, list):
                return abi_json
    except Exception as e:
        print(f"Failed to fetch ABI: {e}")
    return None


def write_env(env_path: str, values: dict) -> None:
    lines = [f"{k}={v}" for k, v in values.items()]
    with open(env_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main() -> None:
    print("== Optimism Rebate Bot Setup ==")

    rpc = prompt("RPC_URL", DEFAULTS["RPC_URL"])    
    priv = prompt("PRIVATE_KEY (input hidden)", secret=True)
    if not priv:
        print("PRIVATE_KEY is required.")
        sys.exit(1)

    acct = Account.from_key(priv)
    derived_wallet = acct.address
    print(f"Derived wallet from private key: {derived_wallet}")
    wallet = prompt("WALLET_ADDRESS (press enter to use derived)", default=derived_wallet)
    if wallet.lower() != derived_wallet.lower():
        print("Warning: WALLET_ADDRESS differs from derived address; the bot will use the derived address at runtime.")

    sleep_interval = prompt("SLEEP_INTERVAL (seconds)", DEFAULTS["SLEEP_INTERVAL"])    
    router = prompt("Velodrome v2 Router address", DEFAULTS["VELO_ROUTER_ADDRESS"])    
    factory = prompt("Velodrome PoolFactory address", DEFAULTS["VELO_POOL_FACTORY"])    

    token_a = prompt("Token A (from) address (e.g., DAI)", DEFAULTS["TOKEN_IN_ADDRESS"])    
    token_b = prompt("Token B (to) address (e.g., USDC.e)", DEFAULTS["TOKEN_OUT_ADDRESS"])    
    swap_amount = prompt("SWAP_AMOUNT (human units of Token A)", DEFAULTS["SWAP_AMOUNT"])    
    slippage = prompt("SLIPPAGE_PERCENT (e.g., 0.3)", DEFAULTS["SLIPPAGE_PERCENT"])    
    gas_price = prompt("GAS_PRICE_WEI (e.g., 1000000 for 0.001 gwei)", DEFAULTS["GAS_PRICE_WEI"])    
    chain_id = prompt("CHAIN_ID (Optimism=10)", DEFAULTS["CHAIN_ID"])    

    # Optional: fetch full ABI
    fetch_choice = prompt("Fetch full router ABI from Optimism Etherscan? (y/N)", "N")
    if fetch_choice.lower() == "y":
        api_key = prompt("Optimism Etherscan API key (press enter if none)", "")
        abi = fetch_router_abi(router, api_key or None)
        if abi:
            with open(os.path.join(os.path.dirname(__file__), "velodrome_router_abi.json"), "w", encoding="utf-8") as f:
                json.dump(abi, f, indent=2)
            print("Saved full router ABI to velodrome_router_abi.json")
        else:
            print("Failed to fetch ABI; keeping existing ABI file.")

    env_values = {
        "RPC_URL": rpc,
        "PRIVATE_KEY": priv,
        "WALLET_ADDRESS": wallet,
        "SLEEP_INTERVAL": sleep_interval,
        "VELO_ROUTER_ADDRESS": router,
        "VELO_POOL_FACTORY": factory,
        "TOKEN_IN_ADDRESS": token_a,
        "TOKEN_OUT_ADDRESS": token_b,
        "SWAP_AMOUNT": swap_amount,
        "SLIPPAGE_PERCENT": slippage,
        "ASSUMED_REBATE_USD": DEFAULTS["ASSUMED_REBATE_USD"],
        "GAS_PRICE_WEI": gas_price,
        "CHAIN_ID": chain_id,
    }

    env_path = os.path.join(os.path.dirname(__file__), ".env")
    write_env(env_path, env_values)
    print(f"Wrote environment to {env_path}")

    print("\nNext steps:")
    print("  1) Review .env")
    print("  2) Run the bot in a loop: python3 optimism_rebate_bot.py")
    print("     or run once: python3 optimism_rebate_bot.py --oneshot")


if __name__ == "__main__":
    main()