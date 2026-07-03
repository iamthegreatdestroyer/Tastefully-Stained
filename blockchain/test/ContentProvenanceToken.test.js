/**
 * Minimal sanity test for ContentProvenanceToken.
 *
 * Scope: confirm the contract deploys and the core mint path works after
 * fixing its compile errors (missing `override` on `_exists`, and the
 * ERC721/ERC721URIStorage `supportsInterface` diamond-inheritance conflict
 * -- see ../contracts/ContentProvenanceToken.sol and blockchain/README.md).
 *
 * This contract is not yet wired into any deploy script or backend code
 * (see README.md), so this is intentionally a small smoke test, not a full
 * suite -- mirroring the scope of the fix itself.
 */
const { expect } = require("chai");
const { ethers } = require("hardhat");
const { loadFixture } = require("@nomicfoundation/hardhat-toolbox/network-helpers");

describe("ContentProvenanceToken", function () {
  async function deployFixture() {
    const [owner, minter] = await ethers.getSigners();

    const mintFee = ethers.parseEther("0.01");
    // watermarkRegistry address is just stored/settable on this contract;
    // it isn't cross-called yet (see the "TODO: Verify anchor exists in
    // registry" in mintProvenanceToken), so any address is fine here.
    const fakeRegistryAddress = owner.address;

    const ContentProvenanceToken = await ethers.getContractFactory("ContentProvenanceToken");
    const token = await ContentProvenanceToken.deploy(fakeRegistryAddress, mintFee);
    await token.waitForDeployment();

    return { token, owner, minter, mintFee, fakeRegistryAddress };
  }

  it("deploys with the expected name, symbol, owner, and registry/fee state", async function () {
    const { token, owner, mintFee, fakeRegistryAddress } = await loadFixture(deployFixture);

    expect(await token.name()).to.equal("Content Provenance Token");
    expect(await token.symbol()).to.equal("CPT");
    expect(await token.owner()).to.equal(owner.address);
    expect(await token.watermarkRegistry()).to.equal(fakeRegistryAddress);
    expect(await token.mintFee()).to.equal(mintFee);
    expect(await token.totalSupply()).to.equal(0);
  });

  it("mints a provenance token, tracks anchor<->token mapping, and refunds overpayment", async function () {
    const { token, minter, mintFee } = await loadFixture(deployFixture);

    const anchorId = ethers.keccak256(ethers.toUtf8Bytes("test-anchor-1"));
    const tokenUri = "ipfs://bafy-test-manifest";
    const overpay = mintFee + ethers.parseEther("0.005");

    const balanceBefore = await ethers.provider.getBalance(minter.address);

    const tx = await token.connect(minter).mintProvenanceToken(anchorId, tokenUri, {
      value: overpay,
    });
    const receipt = await tx.wait();
    const gasCost = receipt.gasUsed * receipt.gasPrice;

    // Exercises supportsInterface (ERC721/ERC721URIStorage diamond fix) and
    // tokenURI (ERC721/ERC721URIStorage override) along the way.
    expect(await token.ownerOf(1)).to.equal(minter.address);
    expect(await token.tokenURI(1)).to.equal(tokenUri);
    expect(await token.getAnchorId(1)).to.equal(anchorId);
    expect(await token.getTokenId(anchorId)).to.equal(1);
    expect(await token.totalSupply()).to.equal(1);
    expect(await token.supportsInterface("0x80ac58cd")).to.equal(true); // ERC721
    expect(await token.supportsInterface("0x5b5e139f")).to.equal(true); // ERC721Metadata

    // Refund of the 0.005 ETH overpayment (minus gas) should land back on minter.
    const balanceAfter = await ethers.provider.getBalance(minter.address);
    const expectedBalance = balanceBefore - mintFee - gasCost;
    expect(balanceAfter).to.equal(expectedBalance);
  });

  it("rejects underpayment and double-minting the same anchor", async function () {
    const { token, minter, mintFee } = await loadFixture(deployFixture);
    const anchorId = ethers.keccak256(ethers.toUtf8Bytes("test-anchor-2"));

    await expect(
      token.connect(minter).mintProvenanceToken(anchorId, "ipfs://x", {
        value: mintFee - 1n,
      })
    ).to.be.revertedWith("ContentProvenanceToken: insufficient fee");

    await token.connect(minter).mintProvenanceToken(anchorId, "ipfs://x", { value: mintFee });

    await expect(
      token.connect(minter).mintProvenanceToken(anchorId, "ipfs://y", { value: mintFee })
    ).to.be.revertedWith("ContentProvenanceToken: already minted");
  });

  it("restricts admin functions to the owner", async function () {
    const { token, minter } = await loadFixture(deployFixture);

    await expect(
      token.connect(minter).setMintFee(ethers.parseEther("1"))
    ).to.be.revertedWith("Ownable: caller is not the owner");
  });
});
