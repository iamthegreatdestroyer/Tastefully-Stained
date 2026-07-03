/**
 * Hardhat configuration for Tastefully Stained blockchain anchoring.
 *
 * Two networks are configured:
 *   - "hardhat": the built-in in-process network used by `hardhat test`.
 *   - "localhost": the long-running Hardhat node started by the
 *     `blockchain` service in docker-compose.yml (`npx hardhat node`,
 *     exposed on host port 17740 -> container port 8545). This is the
 *     network the Python backend talks to during local dev/CI.
 *
 * Sepolia is intentionally NOT configured here. Real testnet deployment
 * is a follow-up step for a human with a funded wallet; when that happens,
 * add a "sepolia" network block here (or, more likely, just point the
 * Python-side ETHEREUM_RPC_URL / ETHEREUM_PRIVATE_KEY env vars at Sepolia --
 * the backend's EthereumAnchor class talks to any EVM JSON-RPC endpoint,
 * this Hardhat project is only used to compile/deploy for local dev.
 */
require("@nomicfoundation/hardhat-toolbox");

/** @type import('hardhat/config').HardhatUserConfig */
module.exports = {
  solidity: {
    version: "0.8.20",
    settings: {
      optimizer: {
        enabled: true,
        runs: 200,
      },
    },
  },
  paths: {
    // ./contracts/*.sol here are individual symlinks back to the repo
    // root's contracts/ directory (see README.md "Contracts" section for
    // the full list and why this isn't a single whole-directory symlink),
    // so .sol sources are not duplicated. Hardhat refuses `sources` paths
    // outside the project root (HH1007), hence symlinks instead of a
    // relative "../contracts".
    sources: "./contracts",
    artifacts: "./artifacts",
    cache: "./cache",
  },
  networks: {
    hardhat: {
      chainId: 31337,
    },
    // Use this when running `npx hardhat ...` *inside* the ts-blockchain
    // container (e.g. `docker exec ts-blockchain npx hardhat run
    // scripts/deploy.js --network localhost`), where the node's own RPC
    // port is reachable directly at 8545.
    localhost: {
      url: "http://127.0.0.1:8545",
      chainId: 31337,
    },
    // Use this when running `npx hardhat ...` from the host (or from
    // anywhere outside the ts-blockchain container), talking to the
    // node via the port docker-compose publishes it on
    // (docker-compose.yml: "17740:8545").
    dockerHost: {
      url: "http://127.0.0.1:17740",
      chainId: 31337,
    },
  },
};
