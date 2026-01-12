// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title WatermarkRegistry
 * @author Tastefully Stained
 * @notice Registry for anchoring watermark hashes on-chain
 * @dev Provides immutable proof of content watermarking with timestamp
 * 
 * This contract stores watermark hashes with associated metadata,
 * enabling verification of content provenance through blockchain anchoring.
 */
contract WatermarkRegistry {
    // ============ Structs ============
    
    /**
     * @notice Watermark anchor record
     * @param watermarkHash SHA-256 hash of the watermark
     * @param contentHash SHA-256 hash of the content
     * @param creator Address that created the anchor
     * @param timestamp Block timestamp of anchor creation
     * @param metadataUri IPFS URI for additional metadata
     */
    struct WatermarkAnchor {
        bytes32 watermarkHash;
        bytes32 contentHash;
        address creator;
        uint256 timestamp;
        string metadataUri;
    }

    // ============ State Variables ============
    
    /// @notice Mapping from anchor ID to WatermarkAnchor
    mapping(bytes32 => WatermarkAnchor) public anchors;
    
    /// @notice Mapping from content hash to anchor ID for lookup
    mapping(bytes32 => bytes32) public contentToAnchor;
    
    /// @notice Total number of anchors created
    uint256 public totalAnchors;
    
    /// @notice Contract owner for admin functions
    address public owner;
    
    /// @notice Fee for anchoring (can be 0)
    uint256 public anchorFee;

    // ============ Events ============
    
    /**
     * @notice Emitted when a new watermark is anchored
     * @param anchorId Unique identifier for the anchor
     * @param watermarkHash Hash of the watermark
     * @param contentHash Hash of the content
     * @param creator Address that created the anchor
     * @param timestamp Block timestamp
     */
    event WatermarkAnchored(
        bytes32 indexed anchorId,
        bytes32 indexed watermarkHash,
        bytes32 indexed contentHash,
        address creator,
        uint256 timestamp
    );
    
    /**
     * @notice Emitted when anchor fee is updated
     * @param oldFee Previous fee
     * @param newFee New fee
     */
    event AnchorFeeUpdated(uint256 oldFee, uint256 newFee);

    // ============ Modifiers ============
    
    modifier onlyOwner() {
        require(msg.sender == owner, "WatermarkRegistry: caller is not owner");
        _;
    }

    // ============ Constructor ============
    
    /**
     * @notice Initialize the registry
     * @param _anchorFee Initial fee for anchoring
     */
    constructor(uint256 _anchorFee) {
        owner = msg.sender;
        anchorFee = _anchorFee;
    }

    // ============ External Functions ============
    
    /**
     * @notice Anchor a watermark hash on-chain
     * @param watermarkHash SHA-256 hash of the watermark
     * @param contentHash SHA-256 hash of the content
     * @param metadataUri IPFS URI for additional metadata
     * @return anchorId Unique identifier for this anchor
     */
    function anchorWatermark(
        bytes32 watermarkHash,
        bytes32 contentHash,
        string calldata metadataUri
    ) external payable returns (bytes32 anchorId) {
        require(msg.value >= anchorFee, "WatermarkRegistry: insufficient fee");
        require(watermarkHash != bytes32(0), "WatermarkRegistry: invalid watermark hash");
        require(contentHash != bytes32(0), "WatermarkRegistry: invalid content hash");
        
        // Generate unique anchor ID
        anchorId = keccak256(
            abi.encodePacked(
                watermarkHash,
                contentHash,
                msg.sender,
                block.timestamp,
                totalAnchors
            )
        );
        
        require(anchors[anchorId].timestamp == 0, "WatermarkRegistry: anchor exists");
        
        // Create anchor
        anchors[anchorId] = WatermarkAnchor({
            watermarkHash: watermarkHash,
            contentHash: contentHash,
            creator: msg.sender,
            timestamp: block.timestamp,
            metadataUri: metadataUri
        });
        
        // Link content to anchor
        contentToAnchor[contentHash] = anchorId;
        
        totalAnchors++;
        
        emit WatermarkAnchored(
            anchorId,
            watermarkHash,
            contentHash,
            msg.sender,
            block.timestamp
        );
        
        // Refund excess payment
        if (msg.value > anchorFee) {
            payable(msg.sender).transfer(msg.value - anchorFee);
        }
        
        return anchorId;
    }
    
    /**
     * @notice Verify if a watermark is anchored
     * @param watermarkHash Hash to verify
     * @param contentHash Content hash to verify against
     * @return isValid True if the anchor exists and matches
     * @return anchor The anchor data if found
     */
    function verifyWatermark(
        bytes32 watermarkHash,
        bytes32 contentHash
    ) external view returns (bool isValid, WatermarkAnchor memory anchor) {
        bytes32 anchorId = contentToAnchor[contentHash];
        
        if (anchorId == bytes32(0)) {
            return (false, anchor);
        }
        
        anchor = anchors[anchorId];
        isValid = (anchor.watermarkHash == watermarkHash);
        
        return (isValid, anchor);
    }
    
    /**
     * @notice Get anchor by ID
     * @param anchorId Anchor identifier
     * @return anchor The anchor data
     */
    function getAnchor(bytes32 anchorId) external view returns (WatermarkAnchor memory) {
        return anchors[anchorId];
    }
    
    /**
     * @notice Get anchor ID for content
     * @param contentHash Content hash to lookup
     * @return anchorId The anchor ID (bytes32(0) if not found)
     */
    function getAnchorByContent(bytes32 contentHash) external view returns (bytes32) {
        return contentToAnchor[contentHash];
    }

    // ============ Admin Functions ============
    
    /**
     * @notice Update anchor fee
     * @param _newFee New fee amount
     */
    function setAnchorFee(uint256 _newFee) external onlyOwner {
        uint256 oldFee = anchorFee;
        anchorFee = _newFee;
        emit AnchorFeeUpdated(oldFee, _newFee);
    }
    
    /**
     * @notice Withdraw collected fees
     */
    function withdraw() external onlyOwner {
        payable(owner).transfer(address(this).balance);
    }
    
    /**
     * @notice Transfer ownership
     * @param newOwner New owner address
     */
    function transferOwnership(address newOwner) external onlyOwner {
        require(newOwner != address(0), "WatermarkRegistry: invalid owner");
        owner = newOwner;
    }
}
