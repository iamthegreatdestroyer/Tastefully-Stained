# blockchain/ — Hardhat dev/CI chain for WatermarkRegistry

Hardhat project used to compile and deploy `WatermarkRegistry.sol` (and the
trivial `Migrations.sol`) from `../contracts/` to a **local** chain for
development and CI. This is also what backs the `blockchain` service in
`../docker-compose.yml` (`npx hardhat node`, host port `17740` -> container
port `8545`, profile `blockchain`).

## Why only two of the three contracts

`./contracts/` in this directory contains two symlinks:

```
WatermarkRegistry.sol -> ../../contracts/WatermarkRegistry.sol
Migrations.sol        -> ../../contracts/Migrations.sol
```

`../contracts/ContentProvenanceToken.sol` is **deliberately not symlinked
in** (and therefore not compiled by this project). It's an ERC721 written
against OpenZeppelin v4's API (imports the now-removed `utils/Counters.sol`)
and, independent of that, has real compile errors against v4 too (missing
`override` specifiers, an unresolved `supportsInterface` diamond-inheritance
conflict between `ERC721` and `ERC721URIStorage`). It was never wired into
any deploy path or backend code — the blockchain anchoring work this
project supports only needs `WatermarkRegistry`. Fixing
`ContentProvenanceToken.sol` is a separate task; do that in `../contracts/`
directly (it's not specific to this Hardhat setup) and then symlink it in
here alongside the other two once it compiles.

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
