// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.13;

import {Test, console} from "forge-std/Test.sol";
import {KeyManager} from "../src/KeyManager.sol";
import "forge-std/Vm.sol";

contract KeyManagerTest is Test {
    KeyManager public keymgr;

    Vm.Wallet alice;
    Vm.Wallet bob;
    Vm.Wallet carol;

    function setUp() public {
        vm.prank(vm.addr(uint(keccak256("KeyManager.t.sol"))));
        keymgr = new KeyManager();

        alice = vm.createWallet("alice");
        bob = vm.createWallet("bob");
    }

    function test_bootstrap() public {
	// 1. Bootstrap
	// 1a. Simulate invoking /dstack-keymanager/bootstrap
        Vm.Wallet memory xPub = vm.createWallet("masterkey");

        // 1b. Post the key and attestation on-chain
        vm.prank(vm.addr(uint(keccak256("KeyManager.t.sol"))));	
        keymgr.bootstrap(xPub.addr);

	// Check a signature
	bytes32 appdata = bytes32("0xcafe");
        bytes32 digest = keccak256(abi.encodePacked("attest", appdata));
	(uint8 v, bytes32 r, bytes32 s) = vm.sign(xPub, digest);
	bytes memory sig = abi.encodePacked(v,r,s);
        assert(keymgr.verify(appdata, sig));

        // 2. Register a new node
        // 2a. Simulate invoking /dstack-keymanager/register
	Vm.Wallet memory myPub = vm.createWallet("ephem");

	// 2b. Onchain submit the request
	digest = keymgr.register_appdata(address(this));
	(v,r,s) = vm.sign(myPub, digest);
	sig = abi.encodePacked(v,r,s);
        keymgr.register(myPub.addr, sig);

        // 3. Help onboard a new node
        // 3a. Offchain generate a ciphertext with the key
        // 3b. Onchain post the ciphertext
	digest = keymgr.onboard_appdata(myPub.addr, bytes16("1"), bytes32("23424"), bytes(""));
	(v,r,s) = vm.sign(xPub, digest);
	sig = abi.encodePacked(v,r,s);
	keymgr.onboard(myPub.addr, bytes16("1"), bytes32("23424"), bytes(""), sig);
    }
    
}
