#!/usr/bin/env bash
cd /opt/projeler/runtime-agent
set -a; . ./.env; set +a
run() { printf "\n\033[1;32m$\033[0m %s\n" "$*"; sleep 1.2; "$@"; sleep 2; }
clear
printf "\033[1mFieldcast Buyer Agent\033[0m — pays only for data it has verified is in the document\n"
sleep 2
run node buyer.mjs balance
run node buyer.mjs run demo/clean_invoice.txt --fields invoice_number,date,total
run node buyer.mjs run demo/shipping_notice.txt --fields invoice_number,date,total,vendor_tax_id
run node buyer.mjs run demo/messy_receipt.txt --fields invoice_number,date,total,vendor_tax_id
run node buyer.mjs balance
sleep 2
