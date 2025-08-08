import argparse
import json
import math
import os
import sys
import time
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Tuple

from eth_account import Account
from eth_account.signers.local import LocalAccount
from web3 import Web3
from web3.contract import Contract
from web3.exceptions import ContractLogicError

import config as cfg


ERC20_ABI = [
    {"constant": False, "inputs": [
        {"name": "_spender", "type": "address"}, {"name": "_value", "type": "uint256"}
    ], "name": "approve", "outputs": [{"name": "", "type": "bool"}], "type": "function"},
    {"constant": True, "inputs": [{"name": "_owner", "type": "address"}, {"name": "_spender", "type": "address"}],
     "name": "allowance", "outputs": [{"name": "remaining", "type": "uint256"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "decimals", "outputs": [{"name": "", "type": "uint8"}], "type": "function"},
    {"constant": True, "inputs": [{"name": "_owner", "type": "address"}],
     "name": "balanceOf", "outputs": [{"name": "balance", "type": "uint256"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "symbol", "outputs": [{"name": "", "type": "string"}], "type": "function"},
]

MAX_UINT256 = (1 << 256) - 1


def load_router_abi(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def now_ts() -> int:
    return int(time.time())


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def human_to_wei(amount_human: Decimal, decimals: int) -> int:
    scale = Decimal(10) ** Decimal(decimals)
    return int((amount_human * scale).to_integral_value(rounding="ROUND_DOWN"))


def wei_to_human(amount_wei: int, decimals: int) -> Decimal:
    return Decimal(amount_wei) / Decimal(10 ** decimals)


class RebateBot:
    def __init__(
        self,
        rpc_url: str,
        private_key: str,
        wallet_address: str,
        router_address: str,
        pool_factory_address: str,
        token_a_address: str,
        token_b_address: str,
        gas_price_wei: int,
        chain_id: int,
        log_path: str = "log.txt",
    ) -> None:
        self.web3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": 60}))
        if not self.web3.is_connected():
            raise RuntimeError("Failed to connect to RPC")

        self.account: LocalAccount = Account.from_key(private_key)
        derived = self.account.address
        if wallet_address and wallet_address.lower() != derived.lower():
            print("Warning: WALLET_ADDRESS does not match derived address from PRIVATE_KEY. Using derived.")
        self.wallet = derived

        self.router_address = Web3.to_checksum_address(router_address)
        self.pool_factory_address = Web3.to_checksum_address(pool_factory_address)
        self.token_a_address = Web3.to_checksum_address(token_a_address)
        self.token_b_address = Web3.to_checksum_address(token_b_address)
        self.gas_price_wei = gas_price_wei
        self.chain_id = chain_id
        self.log_path = log_path

        router_abi = load_router_abi(os.path.join(os.path.dirname(__file__), "velodrome_router_abi.json"))
        self.router: Contract = self.web3.eth.contract(address=self.router_address, abi=router_abi)

        self.token_a: Contract = self.web3.eth.contract(address=self.token_a_address, abi=ERC20_ABI)
        self.token_b: Contract = self.web3.eth.contract(address=self.token_b_address, abi=ERC20_ABI)

        self.dec_a = int(self.token_a.functions.decimals().call())
        self.dec_b = int(self.token_b.functions.decimals().call())
        self.sym_a = str(self.token_a.functions.symbol().call())
        self.sym_b = str(self.token_b.functions.symbol().call())

    def log(self, message: str) -> None:
        line = f"[{now_iso()}] {message}\n"
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(line)
        print(line, end="")

    def _build_tx(self) -> Dict[str, Any]:
        nonce = self.web3.eth.get_transaction_count(self.wallet)
        return {
            "from": self.wallet,
            "nonce": nonce,
            "gasPrice": self.gas_price_wei,
            # Gas limit set generously; OP auto-rebates part; adjust dynamically if desired
            "gas": 600000,
            "chainId": self.chain_id,
        }

    def ensure_allowance(self, token: Contract, spender: str, required: int) -> Tuple[bool, str]:
        current = int(token.functions.allowance(self.wallet, spender).call())
        if current >= required and current > 0:
            return True, ""
        tx = token.functions.approve(spender, MAX_UINT256).build_transaction(self._build_tx())
        signed = self.account.sign_transaction(tx)
        tx_hash = self.web3.eth.send_raw_transaction(signed.rawTransaction)
        rcpt = self.web3.eth.wait_for_transaction_receipt(tx_hash)
        success = rcpt.status == 1
        gas_used = rcpt.gasUsed
        self.log(f"Approve {token.functions.symbol().call()} → {spender} | tx: {tx_hash.hex()} | gasUsed: {gas_used}")
        return success, tx_hash.hex()

    def quote_out(self, amount_in_wei: int, from_token: str, to_token: str, stable: bool) -> int:
        route = [{
            "from": Web3.to_checksum_address(from_token),
            "to": Web3.to_checksum_address(to_token),
            "stable": stable,
            "factory": self.pool_factory_address,
        }]
        amounts = self.router.functions.getAmountsOut(amount_in_wei, route).call()
        return int(amounts[-1])

    def swap_exact_tokens_for_tokens(
        self, amount_in_wei: int, amount_out_min_wei: int, from_token: str, to_token: str, stable: bool
    ) -> Tuple[bool, str, int]:
        route = [{
            "from": Web3.to_checksum_address(from_token),
            "to": Web3.to_checksum_address(to_token),
            "stable": stable,
            "factory": self.pool_factory_address,
        }]
        deadline = now_ts() + 60 * 5
        tx = self.router.functions.swapExactTokensForTokens(
            amount_in_wei,
            amount_out_min_wei,
            route,
            self.wallet,
            deadline,
        ).build_transaction(self._build_tx())

        signed = self.account.sign_transaction(tx)
        tx_hash = self.web3.eth.send_raw_transaction(signed.rawTransaction)
        rcpt = self.web3.eth.wait_for_transaction_receipt(tx_hash)
        success = rcpt.status == 1
        return success, tx_hash.hex(), int(rcpt.gasUsed)

    def estimate_profit_usd(self, gas_used: int, gas_price_wei: int, assumed_rebate_usd: Decimal) -> Decimal:
        # Simple placeholder: profit = rebate - gas_cost_approx_usd (not actually priced vs USD here)
        # Without a price feed, return rebate only. Extend later to use an oracle.
        return assumed_rebate_usd

    def run_once(
        self,
        amount_human: Decimal,
        forward: bool = True,
        slippage_percent: Decimal = Decimal("0.3"),
        prefer_stable_pool: bool = True,
    ) -> None:
        from_token = self.token_a if forward else self.token_b
        to_token = self.token_b if forward else self.token_a
        from_dec = self.dec_a if forward else self.dec_b
        to_dec = self.dec_b if forward else self.dec_a
        from_sym = self.sym_a if forward else self.sym_b
        to_sym = self.sym_b if forward else self.sym_a

        amount_in_wei = human_to_wei(amount_human, from_dec)

        # Ensure sufficient allowance
        ok, _ = self.ensure_allowance(from_token, self.router_address, amount_in_wei)
        if not ok:
            self.log(f"Approval failed for {from_sym}")
            return

        # Quote and compute minOut
        try:
            quoted_out = self.quote_out(amount_in_wei, from_token.address, to_token.address, prefer_stable_pool)
        except ContractLogicError as e:
            self.log(f"Quote failed: {e}")
            return
        except Exception as e:
            self.log(f"Quote error: {e}")
            return

        slippage_fraction = (Decimal(100) - slippage_percent) / Decimal(100)
        min_out = int(Decimal(quoted_out) * slippage_fraction)

        # Execute swap
        try:
            success, txh, gas_used = self.swap_exact_tokens_for_tokens(
                amount_in_wei, min_out, from_token.address, to_token.address, prefer_stable_pool
            )
            if success:
                out_human = wei_to_human(min_out, to_dec)
                profit_est = self.estimate_profit_usd(gas_used, self.gas_price_wei, cfg.ASSUMED_REBATE_USD)
                self.log(
                    f"Swapped {amount_human} {from_sym} → {to_sym} | tx: {txh} | gasUsed: {gas_used}"
                )
            else:
                self.log(f"Swap failed | tx: {txh} | gasUsed: {gas_used}")
        except ContractLogicError as e:
            self.log(f"Swap reverted: {e}")
        except Exception as e:
            self.log(f"Swap error: {e}")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Optimism gas rebate bot using Velodrome v2 router")
    p.add_argument("--rpc", default=cfg.RPC_URL)
    p.add_argument("--private-key", default=cfg.PRIVATE_KEY)
    p.add_argument("--wallet", default=cfg.WALLET_ADDRESS)
    p.add_argument("--router", default=cfg.VELO_ROUTER_ADDRESS)
    p.add_argument("--factory", default=cfg.VELO_POOL_FACTORY)
    p.add_argument("--token-a", default=cfg.TOKEN_IN_ADDRESS, help="First token address, e.g., DAI")
    p.add_argument("--token-b", default=cfg.TOKEN_OUT_ADDRESS, help="Second token address, e.g., USDC")
    p.add_argument("--amount", default=cfg.SWAP_AMOUNT, help="Amount of token for each leg (human units)")
    p.add_argument("--slippage", default=str(cfg.SLIPPAGE_PERCENT), help="Slippage percent, e.g., 0.3")
    p.add_argument("--sleep", default=str(cfg.SLEEP_INTERVAL), help="Sleep seconds between swaps")
    p.add_argument("--gas-price-wei", default=str(cfg.GAS_PRICE_WEI))
    p.add_argument("--chain-id", default=str(cfg.CHAIN_ID))
    p.add_argument("--log", default="log.txt")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    if not args.private_key:
        print("PRIVATE_KEY missing (set in config.py or via CLI/env)")
        sys.exit(1)

    bot = RebateBot(
        rpc_url=args.rpc,
        private_key=args.private_key,
        wallet_address=args.wallet,
        router_address=args.router,
        pool_factory_address=args.factory,
        token_a_address=args.token_a,
        token_b_address=args.token_b,
        gas_price_wei=int(args.gas_price_wei),
        chain_id=int(args.chain_id),
        log_path=args.log,
    )

    amount = Decimal(str(args.amount))
    slippage = Decimal(str(args.slippage))
    sleep_s = int(args.sleep)

    # Alternate direction each loop (A->B then B->A)
    forward = True
    while True:
        try:
            bot.run_once(amount_human=amount, forward=forward, slippage_percent=slippage)
        except Exception as e:
            bot.log(f"Unhandled error in loop: {e}")
        forward = not forward
        time.sleep(sleep_s)


if __name__ == "__main__":
    main()