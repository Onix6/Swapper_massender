// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IERC20 {
    function transfer(address to, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
}

contract Swapper_masssender {
    address public owner;
    IERC20 public usdt;

    mapping(address => bool) public isClient;
    address[] public clients;

    event Sent(address indexed token, address indexed to, uint256 amount);
    event Withdrawn(address indexed token, address indexed to, uint256 amount);
    event ClientAdded(address indexed client);

    modifier onlyOwner() {
        require(msg.sender == owner, "Not authorized");
        _;
    }

    constructor(address _usdtAddress) {
        owner = msg.sender;
        usdt = IERC20(_usdtAddress);
    }

    // ========== Client Management ==========

    function addClient(address _client) external onlyOwner {
        _addClient(_client);
    }

    function register() external {
        _addClient(msg.sender);
    }

    function _addClient(address _client) internal {
        if (!isClient[_client]) {
            isClient[_client] = true;
            clients.push(_client);
            emit ClientAdded(_client);
        }
    }

    function getAllClients() external view returns (address[] memory) {
        return clients;
    }

    // ========== Swap Logic ==========

    function swap(address token, address to, uint256 amount) external onlyOwner {
        require(IERC20(token).transfer(to, amount), "Transfer failed");
        emit Sent(token, to, amount);
    }

    function sendBatchUSDT(address[] calldata recipients, uint256[] calldata amounts) external onlyOwner {
        require(recipients.length == amounts.length, "Mismatched arrays");
        for (uint256 i = 0; i < recipients.length; i++) {
            require(usdt.transfer(recipients[i], amounts[i]), "Transfer failed");
            emit Sent(address(usdt), recipients[i], amounts[i]);
        }
    }

    function withdrawAllUSDT() external onlyOwner {
        uint256 balance = usdt.balanceOf(address(this));
        require(usdt.transfer(owner, balance), "Withdraw failed");
        emit Withdrawn(address(usdt), owner, balance);
    }

    function withdrawAllToken(address token) external onlyOwner {
        uint256 balance = IERC20(token).balanceOf(address(this));
        require(IERC20(token).transfer(owner, balance), "Withdraw failed");
        emit Withdrawn(token, owner, balance);
    }

    function getTokenBalance(address token) external view returns (uint256) {
        return IERC20(token).balanceOf(address(this));
    }
}
