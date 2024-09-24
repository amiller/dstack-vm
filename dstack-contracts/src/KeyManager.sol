// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.13;

library Secp256k1 {
    function verify(address signer, bytes32 digest, bytes memory sig) internal pure returns (bool) {
        uint8 v;
        bytes32 r;
        bytes32 s;
        assembly {
            v := mload(add(sig, 1))
            r := mload(add(sig, 33))
            s := mload(add(sig, 65))
        }
        return signer == ecrecover(digest, v, r, s);
    }
}

contract KeyManager {
    
    // Owner is responsible for initializing
    address owner;
    constructor () {
	owner = msg.sender;
    }

    // Anyone can see the master public key
    address public xPub;

    ///////////////////////////////////
    // EVM-Friendly remote attestation
    ///////////////////////////////////

    /* The sig is obtained by calling
        dstack-keymanager/attest/<appdata> */
    function verify(bytes32 appData, bytes memory sig) public view returns (bool) {
        bytes32 digest = keccak256(abi.encodePacked("attest", appData));
        return Secp256k1.verify(xPub, digest, sig);
    }

    ///////////////
    // KubernEthes
    ///////////////

    string public container;
    event ContainerChanged(string container);
    function set_container(string memory _container) public {
	require(msg.sender == owner);
	container = _container;
	emit ContainerChanged(container);
    }    

    //////////////////////////////
    // Replicatoor Bootstrapping
    //////////////////////////////
    /*
      The bootstrap phase is called by the owner, just once,
      and sets the master public key. The significance of this
      is that the remote attestation
     */

    event BootstrapComplete(address indexed xPub); 
    function bootstrap(address _xPub) public {
	require(msg.sender == owner);
        //require(xPub == address(0)); // only once
	//require(_xPub != address(0));
        xPub = _xPub;
	emit BootstrapComplete(xPub);
    }

    //////////////////////////////    
    // Replicatoor register phase
    //////////////////////////////
    
    // TODO: Replace this with On-Chain PCCS

    struct TcbInfo {
	bytes16 fmspc;
	bytes32 mrtd;
    }
    mapping(address => TcbInfo) public registry;

    enum Status { NotYet, Requested, Onboarded, Rejected }
    mapping(address => Status) public requested;

    function register_appdata(address addr)
    public pure returns(bytes32) {
	return keccak256(abi.encodePacked("register",addr));
    }

    event Requested(address indexed addr);
    function register(address addr, bytes memory sig) public {
	// Simply add this event
	// TODO: A valid request must be a blob transaction
	require(requested[addr] == Status.NotYet);
	requested[addr] = Status.Requested;
	bytes32 digest = register_appdata(msg.sender);
        require(Secp256k1.verify(addr, digest, sig));
	emit Requested(addr);
    }

    //////////////////////
    // Replicatoor onboard
    //////////////////////

    function onboard_appdata(address addr, bytes16 fmspc, bytes32 mrtd, bytes memory ciph)
    public pure returns(bytes32) {
	return keccak256(abi.encodePacked("onboard",addr,fmspc,mrtd,ciph));
    }
    
    event Onboarded(address indexed addr, bytes16 fmspc, bytes32 mrtd, bytes ciph);
    function onboard(address addr, bytes16 fmspc, bytes32 mrtd, bytes memory ciph, bytes memory sig) public
    {
	bytes32 digest = onboard_appdata(addr, fmspc, mrtd, ciph);
        require(Secp256k1.verify(xPub, digest, sig));

	// We can process each in turn
	registry[addr].fmspc = fmspc;
        registry[addr].mrtd = mrtd;
	
	emit Onboarded(addr, fmspc, mrtd, ciph);
    }
}
