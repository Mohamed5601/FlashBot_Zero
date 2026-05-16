# Alloy-MEV-Executor-V2

This is a low-latency MEV arbitrage execution framework I built for Ethereum Mainnet using Rust and Solidity. 

The main goal of this project was to stop relying on slow RPC queries for route evaluation. Instead of asking a node to simulate every swap, the bot does the EVM math locally in memory to save milliseconds during mempool races.

---

## How it works under the hood

When building this, I had to solve a few annoying bottlenecks to get the speed right:

### 1. Bridging Alloy and Primitive Types
If you work with Rust in Web3 right now, you know the ecosystem is split between the old `primitive_types` and the new `alloy_primitives`. To fix this without wasting time on heap allocations, I wrote direct memory-layout casting using little-endian byte slices (`to_le_bytes::<32>()`). Basically, it acts as a zero-copy bridge between the two formats.

### 2. Running Uniswap Math Locally
Waiting for an RPC response is a death sentence in MEV. So, I ported the core Uniswap V3 math (`compute_swap_step` and `tick_math`) to run locally. The bot calculates the exact `amount_out` and slippage limits right in the CPU before building the transaction.

### 3. Handling State Concurrency
Mempools get chaotic during block spikes. I used a concurrent `DashMap` to cache active pool states. This lets the Tokio runtime handle multiple tasks reading and writing pool data at the same time without locking up the threads.

---

## Codebase Breakdown

I split the backend into specific modules to keep things clean:

* **`math.rs`**: Handles the local Uniswap V3 simulations, Q64.96 math, and the type conversions.
* **`state.rs`**: The concurrent cache holding the active pools. 
* **`executor.rs`**: Builds the payload, estimates gas, and pushes the transaction.
* **`main.rs`**: The Tokio async loop that manages websockets and cross-module channels.

---

## The Smart Contract (`ArbFlashBot.sol`)

The on-chain part is straightforward but defensive:
* **Flash Loans:** Hooked up to the Balancer Vault to borrow capital.
* **Weird ERC20s:** I added custom wrappers to handle non-standard tokens that don't return booleans on `transfer`. If you don't do this, they will silently fail your whole execution.
* **Gas Protection:** Added strict atomicity checks. If the state changes and the margin isn't there anymore, the contract reverts early to save gas.

---

## Stack
* Rust (Tokio, Alloy-rs)
* Solidity 0.8.20
* Targets: Uniswap V3 & Balancer Vault

---

## Notes & Status
I built this as a research project focused on low-level EVM mechanics and execution speed, and I wrapped up the core development around late 2025. 

It works great as a reference architecture, but keep in mind that some scripts in the repo reflect fast, local testing iterations rather than a polished, plug-and-play production binary.
