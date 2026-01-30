# Solidity Conventions

## Project Structure

```
project/
├── contracts/
│   ├── interfaces/
│   │   └── IToken.sol
│   ├── libraries/
│   │   └── SafeMath.sol
│   ├── core/
│   │   ├── Token.sol
│   │   └── Vault.sol
│   └── mocks/                    # Test mocks
│       └── MockToken.sol
├── scripts/
│   ├── deploy.ts
│   └── verify.ts
├── test/
│   ├── Token.test.ts
│   └── helpers/
├── hardhat.config.ts
└── package.json
```

## Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Contract | PascalCase | `TokenVault` |
| Interface | I + PascalCase | `ITokenVault` |
| Library | PascalCase | `SafeMath` |
| File | PascalCase | `TokenVault.sol` |
| Function | camelCase | `transferTokens` |
| Private function | _camelCase | `_validateTransfer` |
| Constant | UPPER_SNAKE_CASE | `MAX_SUPPLY` |
| Event | PascalCase | `TokenTransferred` |
| Error | PascalCase | `InsufficientBalance` |
| Modifier | camelCase | `onlyOwner` |

## Approved Libraries

| Purpose | Library | Notes |
|---------|---------|-------|
| Framework | Hardhat | Development |
| Standards | OpenZeppelin | ERC implementations |
| Testing | Chai + Hardhat | Test framework |
| Upgrades | OpenZeppelin Upgrades | Proxy patterns |
| Math | OpenZeppelin Math | Safe math |

## Build Commands

| Action | Command |
|--------|---------|
| Compile | `npx hardhat compile` |
| Test | `npx hardhat test` |
| Coverage | `npx hardhat coverage` |
| Deploy | `npx hardhat run scripts/deploy.ts` |
| Verify | `npx hardhat verify --network mainnet ADDRESS` |
| Console | `npx hardhat console` |

## Contract Structure

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/**
 * @title TokenVault
 * @author Your Name
 * @notice A vault for storing and managing tokens
 * @dev Implements deposit and withdrawal with fee mechanism
 */
contract TokenVault is Ownable, ReentrancyGuard {
    using SafeERC20 for IERC20;

    // ============ Constants ============

    uint256 public constant MAX_FEE = 1000; // 10%
    uint256 public constant FEE_DENOMINATOR = 10000;

    // ============ State Variables ============

    IERC20 public immutable token;
    uint256 public depositFee;
    mapping(address => uint256) public balances;

    // ============ Events ============

    event Deposited(address indexed user, uint256 amount, uint256 fee);
    event Withdrawn(address indexed user, uint256 amount);
    event FeeUpdated(uint256 oldFee, uint256 newFee);

    // ============ Errors ============

    error InvalidAmount();
    error InsufficientBalance();
    error FeeTooHigh();
    error ZeroAddress();

    // ============ Modifiers ============

    modifier validAmount(uint256 amount) {
        if (amount == 0) revert InvalidAmount();
        _;
    }

    // ============ Constructor ============

    constructor(
        address _token,
        uint256 _depositFee,
        address _owner
    ) Ownable(_owner) {
        if (_token == address(0)) revert ZeroAddress();
        if (_depositFee > MAX_FEE) revert FeeTooHigh();

        token = IERC20(_token);
        depositFee = _depositFee;
    }

    // ============ External Functions ============

    /**
     * @notice Deposit tokens into the vault
     * @param amount The amount of tokens to deposit
     */
    function deposit(uint256 amount) external nonReentrant validAmount(amount) {
        uint256 fee = _calculateFee(amount);
        uint256 depositAmount = amount - fee;

        balances[msg.sender] += depositAmount;

        token.safeTransferFrom(msg.sender, address(this), amount);

        emit Deposited(msg.sender, depositAmount, fee);
    }

    /**
     * @notice Withdraw tokens from the vault
     * @param amount The amount of tokens to withdraw
     */
    function withdraw(uint256 amount) external nonReentrant validAmount(amount) {
        if (balances[msg.sender] < amount) revert InsufficientBalance();

        balances[msg.sender] -= amount;

        token.safeTransfer(msg.sender, amount);

        emit Withdrawn(msg.sender, amount);
    }

    // ============ Admin Functions ============

    /**
     * @notice Update the deposit fee
     * @param newFee The new fee in basis points
     */
    function setDepositFee(uint256 newFee) external onlyOwner {
        if (newFee > MAX_FEE) revert FeeTooHigh();

        uint256 oldFee = depositFee;
        depositFee = newFee;

        emit FeeUpdated(oldFee, newFee);
    }

    // ============ View Functions ============

    /**
     * @notice Get the balance of a user
     * @param user The user address
     * @return The user's balance
     */
    function balanceOf(address user) external view returns (uint256) {
        return balances[user];
    }

    // ============ Internal Functions ============

    function _calculateFee(uint256 amount) internal view returns (uint256) {
        return (amount * depositFee) / FEE_DENOMINATOR;
    }
}
```

## Interface Pattern

```solidity
// contracts/interfaces/ITokenVault.sol
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface ITokenVault {
    // Events
    event Deposited(address indexed user, uint256 amount, uint256 fee);
    event Withdrawn(address indexed user, uint256 amount);

    // Errors
    error InvalidAmount();
    error InsufficientBalance();

    // Functions
    function deposit(uint256 amount) external;
    function withdraw(uint256 amount) external;
    function balanceOf(address user) external view returns (uint256);
}
```

## Code Style

- Use custom errors over require strings (gas efficient)
- Use `immutable` for values set in constructor
- Use `constant` for compile-time constants
- Follow checks-effects-interactions pattern
- Use OpenZeppelin for standard implementations
- Document with NatSpec comments
- Order: constants, state, events, errors, modifiers, constructor, external, public, internal, private
- Use SafeERC20 for token transfers
- Always use ReentrancyGuard for external calls
