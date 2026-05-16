# FlashBot Zero v2

FlashBot Zero v2 is a modular arbitrage execution framework built for the Ethereum Mainnet network using Rust and Solidity.

The project focuses on low-latency transaction simulation, multi-hop execution, and reliable interaction with concentrated liquidity AMMs like Uniswap V3.

## Architecture

The Rust backend is split into separate modules to keep simulation, execution, and state management isolated and easier to maintain.

- `main.rs`
  Handles block subscriptions, async orchestration, and cross-module coordination.

- `math.rs`
  Contains Uniswap V3 math utilities, including Tick ↔ Price conversions using Q64.96 fixed-point calculations.

- `executor.rs`
  Handles transaction building, gas estimation, signing, and propagation.

- `state.rs`
  Stores cached pool metadata and token information using DashMap to reduce redundant RPC calls.

## Smart Contract Layer

`ArbFlashBot.sol` handles the on-chain execution flow.

The contract integrates with the Balancer Vault for flash loans and includes compatibility handling for non-standard ERC20 implementations that do not consistently return transfer values.

Additional checks are included to avoid failed execution paths during swaps and approvals.

## Stack

- Rust (Tokio)
- Alloy-rs
- Solidity 0.8.20
- Uniswap V3
- Balancer Vault

## Project Status

Development on this project has been paused since late 2025.

The repository is still kept public as part of my research and engineering portfolio, and some parts of the codebase reflect fast testing and research iterations rather than polished production code.

## Notes

This was built mainly as a research and engineering project focused on execution flow, async infrastructure, and DeFi arbitrage mechanics.

