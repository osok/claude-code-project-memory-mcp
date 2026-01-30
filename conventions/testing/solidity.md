# Solidity Testing Conventions

## Test Structure

```
test/
├── TokenVault.test.ts        # Main contract tests
├── Token.test.ts
├── integration/
│   └── FullFlow.test.ts
├── helpers/
│   ├── fixtures.ts           # Test setup
│   ├── constants.ts
│   └── utils.ts
└── mocks/
    └── MockToken.sol
```

## Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Test file | `{Contract}.test.ts` | `TokenVault.test.ts` |
| Describe | Contract name | `describe("TokenVault")` |
| Context | `when/with` prefix | `context("when user has balance")` |
| It | Describes behavior | `it("should transfer tokens")` |

## Test Framework

| Purpose | Tool | Notes |
|---------|------|-------|
| Framework | Hardhat + Chai | Standard |
| Time manipulation | hardhat-network-helpers | Block time |
| Gas reporting | hardhat-gas-reporter | Gas tracking |
| Coverage | solidity-coverage | Code coverage |
| Fuzzing | Foundry (optional) | Property testing |

## Test Commands

| Action | Command |
|--------|---------|
| Run all | `npx hardhat test` |
| Run file | `npx hardhat test test/TokenVault.test.ts` |
| Coverage | `npx hardhat coverage` |
| Gas report | `REPORT_GAS=true npx hardhat test` |

## Unit Tests (TypeScript)

```typescript
// test/TokenVault.test.ts
import { expect } from "chai";
import { ethers } from "hardhat";
import { loadFixture, time } from "@nomicfoundation/hardhat-network-helpers";
import { TokenVault, MockERC20 } from "../typechain-types";
import { SignerWithAddress } from "@nomicfoundation/hardhat-ethers/signers";

describe("TokenVault", function () {
  // Fixture for consistent test setup
  async function deployVaultFixture() {
    const [owner, user1, user2] = await ethers.getSigners();

    // Deploy mock token
    const MockToken = await ethers.getContractFactory("MockERC20");
    const token = await MockToken.deploy("Test Token", "TEST", 18);

    // Deploy vault
    const TokenVault = await ethers.getContractFactory("TokenVault");
    const vault = await TokenVault.deploy(
      await token.getAddress(),
      100, // 1% fee
      owner.address
    );

    // Mint tokens to users
    const amount = ethers.parseEther("1000");
    await token.mint(user1.address, amount);
    await token.mint(user2.address, amount);

    // Approve vault
    await token.connect(user1).approve(await vault.getAddress(), amount);
    await token.connect(user2).approve(await vault.getAddress(), amount);

    return { vault, token, owner, user1, user2 };
  }

  describe("Deployment", function () {
    it("should set the correct token", async function () {
      const { vault, token } = await loadFixture(deployVaultFixture);

      expect(await vault.token()).to.equal(await token.getAddress());
    });

    it("should set the correct owner", async function () {
      const { vault, owner } = await loadFixture(deployVaultFixture);

      expect(await vault.owner()).to.equal(owner.address);
    });

    it("should set the correct deposit fee", async function () {
      const { vault } = await loadFixture(deployVaultFixture);

      expect(await vault.depositFee()).to.equal(100);
    });

    it("should revert with zero token address", async function () {
      const [owner] = await ethers.getSigners();
      const TokenVault = await ethers.getContractFactory("TokenVault");

      await expect(
        TokenVault.deploy(ethers.ZeroAddress, 100, owner.address)
      ).to.be.revertedWithCustomError(TokenVault, "ZeroAddress");
    });

    it("should revert with fee too high", async function () {
      const { token } = await loadFixture(deployVaultFixture);
      const [owner] = await ethers.getSigners();
      const TokenVault = await ethers.getContractFactory("TokenVault");

      await expect(
        TokenVault.deploy(await token.getAddress(), 1001, owner.address)
      ).to.be.revertedWithCustomError(TokenVault, "FeeTooHigh");
    });
  });

  describe("Deposit", function () {
    it("should deposit tokens correctly", async function () {
      const { vault, token, user1 } = await loadFixture(deployVaultFixture);
      const amount = ethers.parseEther("100");

      await vault.connect(user1).deposit(amount);

      // 1% fee = 1 token
      const expectedBalance = ethers.parseEther("99");
      expect(await vault.balanceOf(user1.address)).to.equal(expectedBalance);
    });

    it("should emit Deposited event", async function () {
      const { vault, user1 } = await loadFixture(deployVaultFixture);
      const amount = ethers.parseEther("100");

      await expect(vault.connect(user1).deposit(amount))
        .to.emit(vault, "Deposited")
        .withArgs(user1.address, ethers.parseEther("99"), ethers.parseEther("1"));
    });

    it("should revert with zero amount", async function () {
      const { vault, user1 } = await loadFixture(deployVaultFixture);

      await expect(
        vault.connect(user1).deposit(0)
      ).to.be.revertedWithCustomError(vault, "InvalidAmount");
    });
  });

  describe("Withdraw", function () {
    it("should withdraw tokens correctly", async function () {
      const { vault, token, user1 } = await loadFixture(deployVaultFixture);

      // Deposit first
      await vault.connect(user1).deposit(ethers.parseEther("100"));

      // Withdraw
      const balanceBefore = await token.balanceOf(user1.address);
      await vault.connect(user1).withdraw(ethers.parseEther("50"));
      const balanceAfter = await token.balanceOf(user1.address);

      expect(balanceAfter - balanceBefore).to.equal(ethers.parseEther("50"));
    });

    it("should revert with insufficient balance", async function () {
      const { vault, user1 } = await loadFixture(deployVaultFixture);

      await expect(
        vault.connect(user1).withdraw(ethers.parseEther("100"))
      ).to.be.revertedWithCustomError(vault, "InsufficientBalance");
    });
  });

  describe("Admin Functions", function () {
    it("should allow owner to update fee", async function () {
      const { vault, owner } = await loadFixture(deployVaultFixture);

      await vault.connect(owner).setDepositFee(200);

      expect(await vault.depositFee()).to.equal(200);
    });

    it("should emit FeeUpdated event", async function () {
      const { vault, owner } = await loadFixture(deployVaultFixture);

      await expect(vault.connect(owner).setDepositFee(200))
        .to.emit(vault, "FeeUpdated")
        .withArgs(100, 200);
    });

    it("should revert when non-owner updates fee", async function () {
      const { vault, user1 } = await loadFixture(deployVaultFixture);

      await expect(
        vault.connect(user1).setDepositFee(200)
      ).to.be.revertedWithCustomError(vault, "OwnableUnauthorizedAccount");
    });
  });
});
```

## Mock Contracts

```solidity
// contracts/mocks/MockERC20.sol
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";

contract MockERC20 is ERC20 {
    uint8 private _decimals;

    constructor(
        string memory name,
        string memory symbol,
        uint8 decimals_
    ) ERC20(name, symbol) {
        _decimals = decimals_;
    }

    function mint(address to, uint256 amount) external {
        _mint(to, amount);
    }

    function burn(address from, uint256 amount) external {
        _burn(from, amount);
    }

    function decimals() public view override returns (uint8) {
        return _decimals;
    }
}
```

## Test Helpers

```typescript
// test/helpers/constants.ts
export const ZERO_ADDRESS = "0x0000000000000000000000000000000000000000";
export const MAX_UINT256 = 2n ** 256n - 1n;

// test/helpers/utils.ts
import { ethers } from "hardhat";

export async function increaseTime(seconds: number) {
  await ethers.provider.send("evm_increaseTime", [seconds]);
  await ethers.provider.send("evm_mine", []);
}

export async function getBlockTimestamp() {
  const block = await ethers.provider.getBlock("latest");
  return block!.timestamp;
}
```

## Coverage Target

- Minimum: 90% line coverage
- 100% coverage for critical paths (deposits, withdrawals)
- Test all custom errors
- Test access control
