# Optimism Gas Rebate Bot (Velodrome v2)

This bot performs periodic stablecoin swaps (e.g., DAI ↔ USDC.e) on Optimism via Velodrome v2 to exploit gas rebate incentives. It alternates swaps and logs activity.

## Prerequisites
- Python 3.10+
- Internet access to Optimism RPC

## Install dependencies
If virtualenv creation is blocked, install with the system pip using break flag:

```
python3 -m pip install --break-system-packages -r requirements.txt
```

## Setup
Run interactive setup to create `.env`:

```
python3 setup.py
```

The script will:
- Prompt for RPC, private key, wallet (derived), tokens, gas price, etc.
- Optionally fetch the full Velodrome v2 router ABI from Optimism Etherscan
- Save values to `.env`

## Run
Continuous loop (default 10 min between swaps):

```
python3 optimism_rebate_bot.py
```

One-shot (forward then backward swap once):

```
python3 optimism_rebate_bot.py --oneshot
```

Override config via CLI if desired (examples):

```
python3 optimism_rebate_bot.py \
  --amount 10 --slippage 0.3 --sleep 600 \
  --token-a 0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1 \
  --token-b 0x7F5c764cBc14f9669B88837ca1490cCa17c31607
```

## Logging
`log.txt` lines:
- Approvals: `[timestamp] Approve SYMBOL → spender | tx: 0x... | gasUsed: ####`
- Swaps: `[timestamp] Swapped X SYMBOL → SYMBOL | tx: 0x... | gasUsed: ####`

## Notes
- Default router: `0xa062aE8A9c5e11aaA026fc2670B0D65cCc8B2858` (Velodrome v2)
- Default factory: `0xF1046053aa5682b4F9a81b5481394DA16BE5FF5a`
- Default gas price: 0.001 gwei (1,000,000 wei)
- Add price feeds and real rebate math if you need true profit calculation.
