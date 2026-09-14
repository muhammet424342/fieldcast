// Deploy AgentBudgetVault from the Dynamic server wallet (no new private key is created).
//
//   node contracts/script/deploy-vault.mjs --network arbitrum-sepolia --dry-run
//   node contracts/script/deploy-vault.mjs --network arbitrum-one
//
// Needs: forge build (for the artifact), DYNAMIC_ENVIRONMENT_ID, DYNAMIC_AUTH_TOKEN, state/wallet.json,
// and a little ETH on the target chain in the agent wallet for gas.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { createPublicClient, http, formatEther, formatUnits, getAddress } from "viem";
import { arbitrum, arbitrumSepolia } from "viem/chains";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, "..", "..");

const NETWORKS = {
  "arbitrum-one": { chain: arbitrum, rpc: "https://arb1.arbitrum.io/rpc", usdc: "0xaf88d065e77c8cC2239327C5EDb3A432268e5831" },
  "arbitrum-sepolia": { chain: arbitrumSepolia, rpc: "https://sepolia-rollup.arbitrum.io/rpc", usdc: "0x75faf114eafb1BDbe2F0316DF893fd58CE46AA4d" },
};

const arg = (name, fallback) => {
  const i = process.argv.indexOf(`--${name}`);
  return i > -1 ? process.argv[i + 1] : fallback;
};
const networkName = arg("network", "arbitrum-sepolia");
const dryRun = process.argv.includes("--dry-run");
const net = NETWORKS[networkName];
if (!net) throw new Error(`unknown network ${networkName}`);

// Owner is the builder's ops wallet (not the agent); the seller gate is the only allowed payee.
const OWNER = getAddress(arg("owner", "0x3f425d6ffd2855585483d65da684651e330759e0"));
const PAYEE = getAddress(arg("payee", "0x3f425d6ffd2855585483d65da684651e330759e0"));
const PER_CALL = BigInt(arg("per-call", "20000")); // 0.02 USDC
const DAILY = BigInt(arg("daily", "100000")); // 0.10 USDC
const FLOAT = BigInt(arg("float", "30000")); // 0.03 USDC

const artifact = JSON.parse(
  fs.readFileSync(path.join(ROOT, "contracts", "out", "AgentBudgetVault.sol", "AgentBudgetVault.json"), "utf8"),
);
const wallet = JSON.parse(fs.readFileSync(path.join(ROOT, "state", "wallet.json"), "utf8"));
const AGENT = getAddress(wallet.address);

const pc = createPublicClient({ chain: net.chain, transport: http(net.rpc) });
const eth = await pc.getBalance({ address: AGENT });
console.log(`network   ${networkName} (chainId ${net.chain.id})`);
console.log(`agent     ${AGENT}  ${formatEther(eth)} ETH`);
console.log(`owner     ${OWNER}`);
console.log(`payee     ${PAYEE}`);
console.log(`caps      perCall ${formatUnits(PER_CALL, 6)} · daily ${formatUnits(DAILY, 6)} · float ${formatUnits(FLOAT, 6)} USDC`);

const args = [net.usdc, OWNER, AGENT, PER_CALL, DAILY, FLOAT, [PAYEE]];
console.log(`bytecode  ${(artifact.bytecode.object.length - 2) / 2} bytes`);
if (dryRun) {
  console.log("dry run: nothing sent");
  process.exit(0);
}
if (eth === 0n) throw new Error("agent wallet has no ETH on this chain for gas");

const { DynamicEvmWalletClient } = await import("@dynamic-labs-wallet/node-evm");
const client = new DynamicEvmWalletClient({ environmentId: process.env.DYNAMIC_ENVIRONMENT_ID });
await client.authenticateApiToken(process.env.DYNAMIC_AUTH_TOKEN);
const wc = await client.getWalletClient({
  walletMetadata: wallet.walletMetadata,
  externalServerKeyShares: wallet.externalServerKeyShares,
  chain: net.chain,
  rpcUrl: net.rpc,
});

const hash = await wc.deployContract({ abi: artifact.abi, bytecode: artifact.bytecode.object, args, account: wc.account, chain: net.chain });
console.log(`deploy tx ${hash}`);
const receipt = await pc.waitForTransactionReceipt({ hash });
if (receipt.status !== "success") throw new Error(`deploy failed: ${receipt.status}`);
const vault = receipt.contractAddress;
console.log(`vault     ${vault}  (block ${receipt.blockNumber})`);

const out = path.join(ROOT, "state", `vault-${networkName}.json`);
fs.writeFileSync(
  out,
  JSON.stringify({ network: networkName, chainId: net.chain.id, vault, deployTx: hash, owner: OWNER, agent: AGENT, payee: PAYEE, usdc: net.usdc, perCall: String(PER_CALL), daily: String(DAILY), float: String(FLOAT) }, null, 2),
);
console.log(`saved     ${out}`);
console.log(`next: send USDC to the vault; the payee is already allowed`);
