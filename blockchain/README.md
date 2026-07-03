# blockchain/ — Hardhat dev/CI chain for WatermarkRegistry

Hardhat project used to compile and deploy `WatermarkRegistry.sol` (and the
trivial `Migrations.sol`) from `../contracts/` to a **local** chain for
development and CI. This is also what backs the `blockchain` service in
`../docker-compose.yml` (`npx hardhat node`, host port `17740` -> container
port `8545`, profile `blockchain`).

## Contracts

`./contracts/` in this directory contains three symlinks back to
`../contracts/`:

```
WatermarkRegistry.sol      -> ../../contracts/WatermarkRegistry.sol
Migrations.sol             -> ../../contracts/Migrations.sol
ContentProvenanceToken.sol -> ../../contracts/ContentProvenanceToken.sol
```

The actually-installed OpenZeppelin version here is v4.9.6 (see
`node_modules/@openzeppelin/contracts/package.json`; note it's currently
*extraneous* per `npm ls` -- present in `node_modules`/`package-lock.json`
but not a declared dependency in `package.json`, likely hoisted from
`hardhat-toolbox`'s own dependency tree). `ContentProvenanceToken.sol` was
previously excluded from this project because it had two real compile
errors against that v4.9.6 API: `_exists(uint256)` was missing an
`override` specifier (it shadows `ERC721._exists`), and `ERC721` /
`ERC721URIStorage` both define `supportsInterface`, which Solidity requires
the most-derived contract to resolve with an explicit override. Both are
now fixed directly in `../contracts/ContentProvenanceToken.sol` (2026-07-03)
and it's symlinked in here alongside the other two, with a small sanity
test at `test/ContentProvenanceToken.test.js` (deploy, mint, refund,
double-mint/underpayment rejection, owner-only admin functions).

It's still **not wired into any deploy path or backend code** — fixing the
compile error was the whole scope of that change. `scripts/deploy.js` only
deploys `WatermarkRegistry`; adding `ContentProvenanceToken` to the deploy
flow (and to `ethereum_anchor.py`/the Python backend, if it's ever actually
used) is a separate, larger task.

## Usage

```bash
npm install
npx hardhat compile

# Start a persistent local node (used by docker-compose's `blockchain`
# service, and by the Python backend/tests when pointed at
# http://127.0.0.1:8545 or http://localhost:17740 from outside the compose
# network):
npx hardhat node --hostname 0.0.0.0

# In another shell, deploy WatermarkRegistry to that running node:
npx hardhat run scripts/deploy.js --network localhost
# -> writes deployments/localhost.json (address, ABI, deployer, tx hash).
# This file is gitignored: a local node's state (and therefore the deployed
# address) does not survive a node restart, so it isn't a stable fact to
# commit.
```

## Pointing this at Sepolia (or any other network) later

This directory is only used to **compile and deploy** the contracts. The
Python side (`backend/watermark_engine/blockchain/ethereum_anchor.py`)
talks to any EVM JSON-RPC endpoint via its `provider_url` constructor arg —
switching from the local Hardhat node to Sepolia is a config change there
(new `provider_url`, a funded `private_key`, and Sepolia's deployed
`contract_address`), not a rebuild of this Hardhat project. If you do want
Hardhat itself to deploy directly to Sepolia (rather than deploying via a
one-off script that talks to whatever RPC URL you export), add a `sepolia`
block under `networks` in `hardhat.config.js` with that network's RPC URL
and a funded deployer private key (from the environment, never hardcoded).
