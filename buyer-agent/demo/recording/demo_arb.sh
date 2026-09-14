#!/usr/bin/env bash
# Arbitrum Sepolia demo: the agent spends only what AgentBudgetVault releases to it.
cd /opt/projeler/runtime-agent
set -a; . ./.env; set +a
export PAY_NETWORK=arbitrum-sepolia VAULT_ADDRESS=0x2c48d7f3bd378d64b0ebe7f85d3ae94fcf3d004c
export PATH=$PATH:/root/.foundry/bin
R=https://sepolia-rollup.arbitrum.io/rpc
USDC=0x75faf114eafb1BDbe2F0316DF893fd58CE46AA4d
AGENT=0x126c57A501226D0f6dfc63E093A9aa928425333d
run() { printf "\n\033[1;32m$\033[0m %s\n" "$*"; sleep 1.2; "$@"; sleep 2; }
usdc() { cast call "$@" --rpc-url $R | awk '{printf "%.2f", $1/1e6}'; }
vault_status() {
  echo "vault $VAULT_ADDRESS (Arbitrum Sepolia)"
  echo "  caps      per call $(usdc $VAULT_ADDRESS 'perCallCap()(uint256)') · daily $(usdc $VAULT_ADDRESS 'dailyCap()(uint256)') · agent float $(usdc $VAULT_ADDRESS 'floatCap()(uint256)') USDC"
  echo "  spent     today $(usdc $VAULT_ADDRESS 'spentToday()(uint256)') USDC"
  echo "  balances  vault $(usdc $USDC 'balanceOf(address)(uint256)' $VAULT_ADDRESS) · agent $(usdc $USDC 'balanceOf(address)(uint256)' $AGENT) USDC"
}
clear
printf "\033[1mFieldcast Buyer Agent on Arbitrum\033[0m — pays only for verified data, only from an on-chain budget\n"
sleep 2
run vault_status
run node buyer.mjs run demo/shipping_notice.txt --fields invoice_number,date,total,vendor_tax_id
run node buyer.mjs run demo/messy_receipt.txt --fields invoice_number,date,total,vendor_tax_id
run vault_status
sleep 2
