// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {Ownable, Ownable2Step} from "@openzeppelin/contracts/access/Ownable2Step.sol";
import {Pausable} from "@openzeppelin/contracts/utils/Pausable.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/// @title AgentBudgetVault
/// @notice Holds a stablecoin budget for one AI agent and releases it just in time, one paid call at a time.
///
/// x402 payments are signed by the agent's own wallet (EIP-3009), so no contract can sit inside the
/// payment itself. The vault constrains what the agent can ever hold instead:
///   - the agent wallet's balance may never exceed `floatCap` after a release,
///   - a single release may not exceed `perCallCap`,
///   - releases in one UTC day may not exceed `dailyCap`,
///   - every release names the payee and the hash of the evidence that justified paying it.
/// A compromised or buggy agent can lose at most `floatCap`; the owner can pause and pull the rest.
contract AgentBudgetVault is Ownable2Step, Pausable, ReentrancyGuard {
    using SafeERC20 for IERC20;

    IERC20 public immutable token;

    address public agent;
    uint256 public perCallCap;
    uint256 public dailyCap;
    uint256 public floatCap;

    uint64 public currentDay;
    uint256 public spentToday;
    uint256 public totalReleased;
    uint256 public releaseCount;

    mapping(address payee => bool) public allowedPayee;

    event AgentSet(address indexed previousAgent, address indexed newAgent);
    event CapsSet(uint256 perCallCap, uint256 dailyCap, uint256 floatCap);
    event PayeeSet(address indexed payee, bool allowed);
    event Released(
        address indexed agent,
        address indexed payee,
        uint256 amount,
        bytes32 indexed evidenceHash,
        uint64 day,
        uint256 spentToday
    );
    event Withdrawn(address indexed to, uint256 amount);

    error NotAgent();
    error ZeroAddress();
    error ZeroAmount();
    error InvalidCaps();
    error PayeeNotAllowed(address payee);
    error OverPerCallCap(uint256 amount, uint256 cap);
    error OverDailyCap(uint256 wouldSpend, uint256 cap);
    error OverFloatCap(uint256 wouldHold, uint256 cap);

    modifier onlyAgent() {
        if (msg.sender != agent) revert NotAgent();
        _;
    }

    constructor(
        IERC20 token_,
        address initialOwner,
        address agent_,
        uint256 perCallCap_,
        uint256 dailyCap_,
        uint256 floatCap_,
        address[] memory initialPayees
    ) Ownable(initialOwner) {
        if (address(token_) == address(0) || agent_ == address(0)) revert ZeroAddress();
        token = token_;
        _setAgent(agent_);
        _setCaps(perCallCap_, dailyCap_, floatCap_);
        // Allowing payees at construction means the vault works right after deployment,
        // without a separate transaction from the owner wallet.
        for (uint256 i = 0; i < initialPayees.length; i++) {
            _setPayee(initialPayees[i], true);
        }
    }

    // ----------------------------------------------------------------------------------------------
    // Agent
    // ----------------------------------------------------------------------------------------------

    /// @notice Move `amount` to the agent wallet right before it pays `payee`.
    /// @param evidenceHash keccak256 of what justified the payment (e.g. the verified quotes). Logged, not interpreted.
    function release(address payee, uint256 amount, bytes32 evidenceHash)
        external
        onlyAgent
        whenNotPaused
        nonReentrant
    {
        if (amount == 0) revert ZeroAmount();
        if (!allowedPayee[payee]) revert PayeeNotAllowed(payee);
        if (amount > perCallCap) revert OverPerCallCap(amount, perCallCap);

        uint64 today = uint64(block.timestamp / 1 days);
        if (today != currentDay) {
            currentDay = today;
            spentToday = 0;
        }

        uint256 wouldSpend = spentToday + amount;
        if (wouldSpend > dailyCap) revert OverDailyCap(wouldSpend, dailyCap);

        uint256 wouldHold = token.balanceOf(msg.sender) + amount;
        if (wouldHold > floatCap) revert OverFloatCap(wouldHold, floatCap);

        spentToday = wouldSpend;
        totalReleased += amount;
        releaseCount += 1;

        token.safeTransfer(msg.sender, amount);
        emit Released(msg.sender, payee, amount, evidenceHash, today, wouldSpend);
    }

    /// @notice What the agent could still release right now, given every cap.
    function releasable(address payee) external view returns (uint256) {
        if (paused() || !allowedPayee[payee]) return 0;
        uint256 dayLeft = uint64(block.timestamp / 1 days) == currentDay ? dailyCap - spentToday : dailyCap;
        uint256 held = token.balanceOf(agent);
        uint256 floatLeft = held >= floatCap ? 0 : floatCap - held;
        uint256 vaultBalance = token.balanceOf(address(this));
        return _min(_min(perCallCap, dayLeft), _min(floatLeft, vaultBalance));
    }

    // ----------------------------------------------------------------------------------------------
    // Owner
    // ----------------------------------------------------------------------------------------------

    function setAgent(address newAgent) external onlyOwner {
        _setAgent(newAgent);
    }

    function setCaps(uint256 perCallCap_, uint256 dailyCap_, uint256 floatCap_) external onlyOwner {
        _setCaps(perCallCap_, dailyCap_, floatCap_);
    }

    function setPayee(address payee, bool allowed) external onlyOwner {
        _setPayee(payee, allowed);
    }

    function pause() external onlyOwner {
        _pause();
    }

    function unpause() external onlyOwner {
        _unpause();
    }

    function withdraw(address to, uint256 amount) external onlyOwner nonReentrant {
        if (to == address(0)) revert ZeroAddress();
        if (amount == 0) revert ZeroAmount();
        token.safeTransfer(to, amount);
        emit Withdrawn(to, amount);
    }

    // ----------------------------------------------------------------------------------------------
    // Internal
    // ----------------------------------------------------------------------------------------------

    function _setAgent(address newAgent) private {
        if (newAgent == address(0)) revert ZeroAddress();
        emit AgentSet(agent, newAgent);
        agent = newAgent;
    }

    function _setPayee(address payee, bool allowed) private {
        if (payee == address(0)) revert ZeroAddress();
        allowedPayee[payee] = allowed;
        emit PayeeSet(payee, allowed);
    }

    function _setCaps(uint256 perCallCap_, uint256 dailyCap_, uint256 floatCap_) private {
        // A single call must fit inside both the daily budget and what the agent may hold.
        if (perCallCap_ == 0 || perCallCap_ > dailyCap_ || perCallCap_ > floatCap_) revert InvalidCaps();
        perCallCap = perCallCap_;
        dailyCap = dailyCap_;
        floatCap = floatCap_;
        emit CapsSet(perCallCap_, dailyCap_, floatCap_);
    }

    function _min(uint256 a, uint256 b) private pure returns (uint256) {
        return a < b ? a : b;
    }
}
