// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title Migrations
 * @notice Truffle/Hardhat migrations tracking contract
 */
contract Migrations {
    address public owner;
    uint256 public lastCompletedMigration;

    modifier restricted() {
        require(msg.sender == owner, "Restricted to owner");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    function setCompleted(uint256 completed) public restricted {
        lastCompletedMigration = completed;
    }
}
