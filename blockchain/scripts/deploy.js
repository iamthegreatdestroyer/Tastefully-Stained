/**
 * Deploy WatermarkRegistry to whichever network Hardhat is pointed at
 * (default target for this project: "localhost", i.e. the long-running
 * `blockchain` docker-compose service on port 17740/8545).
 *
 * Usage:
 *   npx hardhat run scripts/deploy.js --network localhost
 *
 * Writes the deployed address (+ chain id, deployer, ABI path) to
 * deployments/<network>.json so the Python backend (and tests) can pick
 * up the contract address without scraping stdout.
 */
const fs = require("fs");
const path = require("path");
const hre = require("hardhat");

async function main() {
  const network = hre.network.name;
  const [deployer] = await hre.ethers.getSigners();

  console.log(`Deploying WatermarkRegistry to network "${network}" as ${deployer.address}`);

  // Zero anchor fee for local/dev/CI use -- anchoring should be frictionless
  // in tests. A production/Sepolia deployment can pass a non-zero fee here
  // if the product owner decides to charge for anchoring later.
  const anchorFee = 0n;

  const WatermarkRegistry = await hre.ethers.getContractFactory("WatermarkRegistry");
  const registry = await WatermarkRegistry.deploy(anchorFee);
  await registry.waitForDeployment();

  const address = await registry.getAddress();
  const deployTx = registry.deploymentTransaction();
  const receipt = await deployTx.wait();

  console.log(`WatermarkRegistry deployed at: ${address}`);
  console.log(`  chainId: ${(await hre.ethers.provider.getNetwork()).chainId}`);
  console.log(`  deployer: ${deployer.address}`);
  console.log(`  tx: ${deployTx.hash}`);
  console.log(`  block: ${receipt.blockNumber}`);

  const outDir = path.join(__dirname, "..", "deployments");
  fs.mkdirSync(outDir, { recursive: true });

  const artifact = await hre.artifacts.readArtifact("WatermarkRegistry");
  const outFile = path.join(outDir, `${network}.json`);
  fs.writeFileSync(
    outFile,
    JSON.stringify(
      {
        network,
        chainId: Number((await hre.ethers.provider.getNetwork()).chainId),
        address,
        deployer: deployer.address,
        anchorFee: anchorFee.toString(),
        txHash: deployTx.hash,
        blockNumber: receipt.blockNumber,
        abi: artifact.abi,
      },
      null,
      2
    )
  );
  console.log(`Deployment record written to: ${outFile}`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
