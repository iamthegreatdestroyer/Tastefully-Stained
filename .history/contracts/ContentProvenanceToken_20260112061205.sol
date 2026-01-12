// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/token/ERC721/extensions/ERC721URIStorage.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/Counters.sol";

/**
 * @title ContentProvenanceToken
 * @author Tastefully Stained
 * @notice NFT representing content provenance and watermark proof
 * @dev ERC721 token that can be minted upon watermark anchoring
 * 
 * Each token represents proof of content ownership and watermarking,
 * linking to the watermark anchor and C2PA manifest on IPFS.
 */
contract ContentProvenanceToken is ERC721, ERC721URIStorage, Ownable {
    using Counters for Counters.Counter;
    
    // ============ State Variables ============
    
    Counters.Counter private _tokenIds;
    
    /// @notice Mapping from token ID to anchor ID
    mapping(uint256 => bytes32) public tokenToAnchor;
    
    /// @notice Mapping from anchor ID to token ID
    mapping(bytes32 => uint256) public anchorToToken;
    
    /// @notice Watermark registry contract address
    address public watermarkRegistry;
    
    /// @notice Minting fee
    uint256 public mintFee;

    // ============ Events ============
    
    /**
     * @notice Emitted when a provenance token is minted
     * @param tokenId Token ID
     * @param anchorId Associated anchor ID
     * @param owner Token owner
     */
    event ProvenanceTokenMinted(
        uint256 indexed tokenId,
        bytes32 indexed anchorId,
        address indexed owner
    );

    // ============ Constructor ============
    
    /**
     * @notice Initialize the provenance token contract
     * @param _watermarkRegistry Address of WatermarkRegistry contract
     * @param _mintFee Fee for minting tokens
     */
    constructor(
        address _watermarkRegistry,
        uint256 _mintFee
    ) ERC721("Content Provenance Token", "CPT") {
        watermarkRegistry = _watermarkRegistry;
        mintFee = _mintFee;
    }

    // ============ External Functions ============
    
    /**
     * @notice Mint a provenance token for an anchored watermark
     * @param anchorId Anchor ID from WatermarkRegistry
     * @param tokenUri IPFS URI for token metadata
     * @return tokenId The minted token ID
     */
    function mintProvenanceToken(
        bytes32 anchorId,
        string calldata tokenUri
    ) external payable returns (uint256 tokenId) {
        require(msg.value >= mintFee, "ContentProvenanceToken: insufficient fee");
        require(anchorToToken[anchorId] == 0, "ContentProvenanceToken: already minted");
        
        // TODO: Verify anchor exists in registry
        
        _tokenIds.increment();
        tokenId = _tokenIds.current();
        
        _safeMint(msg.sender, tokenId);
        _setTokenURI(tokenId, tokenUri);
        
        tokenToAnchor[tokenId] = anchorId;
        anchorToToken[anchorId] = tokenId;
        
        emit ProvenanceTokenMinted(tokenId, anchorId, msg.sender);
        
        // Refund excess
        if (msg.value > mintFee) {
            payable(msg.sender).transfer(msg.value - mintFee);
        }
        
        return tokenId;
    }
    
    /**
     * @notice Get anchor ID for a token
     * @param tokenId Token ID
     * @return anchorId The associated anchor ID
     */
    function getAnchorId(uint256 tokenId) external view returns (bytes32) {
        require(_exists(tokenId), "ContentProvenanceToken: nonexistent token");
        return tokenToAnchor[tokenId];
    }
    
    /**
     * @notice Get token ID for an anchor
     * @param anchorId Anchor ID
     * @return tokenId The associated token ID (0 if not minted)
     */
    function getTokenId(bytes32 anchorId) external view returns (uint256) {
        return anchorToToken[anchorId];
    }
    
    /**
     * @notice Total supply of tokens
     */
    function totalSupply() external view returns (uint256) {
        return _tokenIds.current();
    }

    // ============ Admin Functions ============
    
    /**
     * @notice Update mint fee
     * @param _newFee New fee amount
     */
    function setMintFee(uint256 _newFee) external onlyOwner {
        mintFee = _newFee;
    }
    
    /**
     * @notice Update registry address
     * @param _newRegistry New registry address
     */
    function setWatermarkRegistry(address _newRegistry) external onlyOwner {
        watermarkRegistry = _newRegistry;
    }
    
    /**
     * @notice Withdraw collected fees
     */
    function withdraw() external onlyOwner {
        payable(owner()).transfer(address(this).balance);
    }

    // ============ Overrides ============
    
    function _burn(uint256 tokenId) internal override(ERC721, ERC721URIStorage) {
        super._burn(tokenId);
    }
    
    function tokenURI(uint256 tokenId) public view override(ERC721, ERC721URIStorage) returns (string memory) {
        return super.tokenURI(tokenId);
    }
    
    function _exists(uint256 tokenId) internal view returns (bool) {
        return _ownerOf(tokenId) != address(0);
    }
}
