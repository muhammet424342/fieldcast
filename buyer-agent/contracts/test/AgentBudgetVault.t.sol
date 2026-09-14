// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";
import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {Pausable} from "@openzeppelin/contracts/utils/Pausable.sol";
import {AgentBudgetVault} from "../src/AgentBudgetVault.sol";

contract MockUSDC is ERC20 {
    constructor() ERC20("USD Coin", "USDC") {}

    function decimals() public pure override returns (uint8) {
        return 6;
    }

    function mint(address to, uint256 amount) external {
        _mint(to, amount);
    }
}

contract AgentBudgetVaultTest is Test {
    MockUSDC usdc;
    AgentBudgetVault vault;

    address owner = makeAddr("owner");
    address agent = makeAddr("agent");
    address seller = makeAddr("seller");
    address stranger = makeAddr("stranger");

    uint256 constant PER_CALL = 20_000; // 0.02 USDC
    uint256 constant DAILY = 100_000; // 0.10 USDC
    uint256 constant FLOAT = 30_000; // 0.03 USDC
    bytes32 constant EVIDENCE = keccak256("invoice_number=nw/88-4471-b");

    event Released(
        address indexed agent,
        address indexed payee,
        uint256 amount,
        bytes32 indexed evidenceHash,
        uint64 day,
        uint256 spentToday
    );

    function setUp() public {
        vm.warp(1_789_000_000);
        usdc = new MockUSDC();
        vault = new AgentBudgetVault(usdc, owner, agent, PER_CALL, DAILY, FLOAT, _payees(seller));
        usdc.mint(address(vault), 1_000_000);
    }

    function _payees(address p) internal pure returns (address[] memory list) {
        list = new address[](1);
        list[0] = p;
    }

    // The agent spends what it received, as the x402 payment would.
    function _agentPays(uint256 amount) internal {
        vm.prank(agent);
        usdc.transfer(seller, amount);
    }

    function test_releaseMovesFundsAndLogsEvidence() public {
        uint64 today = uint64(block.timestamp / 1 days);
        vm.expectEmit(address(vault));
        emit Released(agent, seller, 10_000, EVIDENCE, today, 10_000);

        vm.prank(agent);
        vault.release(seller, 10_000, EVIDENCE);

        assertEq(usdc.balanceOf(agent), 10_000);
        assertEq(vault.spentToday(), 10_000);
        assertEq(vault.totalReleased(), 10_000);
        assertEq(vault.releaseCount(), 1);
    }

    function test_onlyAgentCanRelease() public {
        vm.prank(stranger);
        vm.expectRevert(AgentBudgetVault.NotAgent.selector);
        vault.release(seller, 10_000, EVIDENCE);
    }

    function test_rejectsUnknownPayee() public {
        vm.prank(agent);
        vm.expectRevert(abi.encodeWithSelector(AgentBudgetVault.PayeeNotAllowed.selector, stranger));
        vault.release(stranger, 10_000, EVIDENCE);
    }

    function test_rejectsZeroAmount() public {
        vm.prank(agent);
        vm.expectRevert(AgentBudgetVault.ZeroAmount.selector);
        vault.release(seller, 0, EVIDENCE);
    }

    function test_perCallCap() public {
        vm.prank(agent);
        vm.expectRevert(abi.encodeWithSelector(AgentBudgetVault.OverPerCallCap.selector, PER_CALL + 1, PER_CALL));
        vault.release(seller, PER_CALL + 1, EVIDENCE);
    }

    function test_floatCapStopsHoarding() public {
        vm.startPrank(agent);
        vault.release(seller, 20_000, EVIDENCE); // agent now holds 0.02
        vm.expectRevert(abi.encodeWithSelector(AgentBudgetVault.OverFloatCap.selector, 40_000, FLOAT));
        vault.release(seller, 20_000, EVIDENCE); // would hold 0.04 > 0.03
        vm.stopPrank();
    }

    function test_dailyCapAndRollover() public {
        for (uint256 i = 0; i < 5; i++) {
            vm.prank(agent);
            vault.release(seller, 20_000, EVIDENCE);
            _agentPays(20_000);
        }
        assertEq(vault.spentToday(), DAILY);

        vm.prank(agent);
        vm.expectRevert(abi.encodeWithSelector(AgentBudgetVault.OverDailyCap.selector, DAILY + 10_000, DAILY));
        vault.release(seller, 10_000, EVIDENCE);

        vm.warp(block.timestamp + 1 days);
        vm.prank(agent);
        vault.release(seller, 10_000, EVIDENCE);
        assertEq(vault.spentToday(), 10_000);
    }

    function test_pauseBlocksReleases() public {
        vm.prank(owner);
        vault.pause();
        vm.prank(agent);
        vm.expectRevert(Pausable.EnforcedPause.selector);
        vault.release(seller, 10_000, EVIDENCE);
        assertEq(vault.releasable(seller), 0);
    }

    function test_ownerControls() public {
        vm.prank(stranger);
        vm.expectRevert(abi.encodeWithSelector(Ownable.OwnableUnauthorizedAccount.selector, stranger));
        vault.setCaps(1, 1, 1);

        vm.startPrank(owner);
        vault.withdraw(owner, 400_000);
        vault.setPayee(seller, false);
        vm.expectRevert(AgentBudgetVault.InvalidCaps.selector);
        vault.setCaps(50_000, 40_000, 60_000); // per-call above daily
        vm.stopPrank();

        assertEq(usdc.balanceOf(owner), 400_000);
        assertFalse(vault.allowedPayee(seller));
    }

    function test_releasableReflectsTightestCap() public {
        assertEq(vault.releasable(seller), PER_CALL);
        vm.prank(agent);
        vault.release(seller, 20_000, EVIDENCE); // agent holds 0.02, float left 0.01
        assertEq(vault.releasable(seller), 10_000);
        assertEq(vault.releasable(stranger), 0);
    }

    function test_constructorRejectsZeroAddressesAndBadCaps() public {
        vm.expectRevert(AgentBudgetVault.ZeroAddress.selector);
        new AgentBudgetVault(MockUSDC(address(0)), owner, agent, PER_CALL, DAILY, FLOAT, _payees(seller));
        vm.expectRevert(AgentBudgetVault.ZeroAddress.selector);
        new AgentBudgetVault(usdc, owner, address(0), PER_CALL, DAILY, FLOAT, _payees(seller));
        vm.expectRevert(AgentBudgetVault.InvalidCaps.selector);
        new AgentBudgetVault(usdc, owner, agent, 0, DAILY, FLOAT, _payees(seller));
        vm.expectRevert(AgentBudgetVault.InvalidCaps.selector);
        new AgentBudgetVault(usdc, owner, agent, PER_CALL, DAILY, PER_CALL - 1, _payees(seller)); // per-call above float
    }

    function test_setAgentRotatesTheKey() public {
        address newAgent = makeAddr("newAgent");
        vm.prank(owner);
        vault.setAgent(newAgent);
        assertEq(vault.agent(), newAgent);

        vm.prank(agent);
        vm.expectRevert(AgentBudgetVault.NotAgent.selector);
        vault.release(seller, 10_000, EVIDENCE);

        vm.prank(newAgent);
        vault.release(seller, 10_000, EVIDENCE);
        assertEq(usdc.balanceOf(newAgent), 10_000);

        vm.prank(owner);
        vm.expectRevert(AgentBudgetVault.ZeroAddress.selector);
        vault.setAgent(address(0));
    }

    function test_unpauseRestoresReleases() public {
        vm.startPrank(owner);
        vault.pause();
        vault.unpause();
        vm.stopPrank();
        vm.prank(agent);
        vault.release(seller, 10_000, EVIDENCE);
        assertEq(vault.releaseCount(), 1);
    }

    function test_constructorAllowsInitialPayees() public view {
        assertTrue(vault.allowedPayee(seller));
        assertFalse(vault.allowedPayee(stranger));
    }

    function test_constructorRejectsZeroPayee() public {
        vm.expectRevert(AgentBudgetVault.ZeroAddress.selector);
        new AgentBudgetVault(usdc, owner, agent, PER_CALL, DAILY, FLOAT, _payees(address(0)));
    }

    function test_ownerInputValidation() public {
        vm.startPrank(owner);
        vm.expectRevert(AgentBudgetVault.ZeroAddress.selector);
        vault.withdraw(address(0), 1);
        vm.expectRevert(AgentBudgetVault.ZeroAmount.selector);
        vault.withdraw(owner, 0);
        vm.expectRevert(AgentBudgetVault.ZeroAddress.selector);
        vault.setPayee(address(0), true);
        vm.stopPrank();
    }

    function test_ownershipTransferIsTwoStep() public {
        address newOwner = makeAddr("newOwner");
        vm.prank(owner);
        vault.transferOwnership(newOwner);
        assertEq(vault.owner(), owner); // not yet
        vm.prank(newOwner);
        vault.acceptOwnership();
        assertEq(vault.owner(), newOwner);
    }

    function test_releasableAfterDayRolloverAndWhenAgentHoldsFloat() public {
        vm.startPrank(agent);
        vault.release(seller, 20_000, EVIDENCE);
        vault.release(seller, 10_000, EVIDENCE); // agent holds exactly the float cap
        vm.stopPrank();
        assertEq(vault.releasable(seller), 0);

        _agentPays(30_000);
        vm.warp(block.timestamp + 1 days);
        assertEq(vault.releasable(seller), PER_CALL); // fresh day, empty agent wallet
    }

    function test_releasableIsLimitedByVaultBalance() public {
        vm.prank(owner);
        vault.withdraw(owner, 1_000_000 - 5_000);
        assertEq(vault.releasable(seller), 5_000);
    }

    /// Whatever sequence of amounts the agent tries in one day, it never gets more than the daily cap,
    /// never holds more than the float cap, and never takes more than one per-call cap at a time.
    function testFuzz_capsHoldUnderAnySequence(uint256[12] memory amounts, bool[12] memory spends) public {
        uint256 released;
        for (uint256 i = 0; i < amounts.length; i++) {
            uint256 amount = bound(amounts[i], 0, PER_CALL * 2);
            vm.prank(agent);
            try vault.release(seller, amount, EVIDENCE) {
                released += amount;
                assertLe(amount, PER_CALL);
                assertLe(usdc.balanceOf(agent), FLOAT);
            } catch {}
            if (spends[i] && usdc.balanceOf(agent) > 0) _agentPays(usdc.balanceOf(agent));
        }
        assertLe(released, DAILY);
        assertEq(vault.spentToday(), released);
    }
}
