# FlashBot Zero v2: High-Performance Modular Execution Engine

A production-grade arbitrage execution suite designed for the **Base network**. This version features a modular Rust backend for low-latency transaction simulation and a resilient Solidity executor optimized for capital efficiency and broad token compatibility.

## 🏗 Modular Architecture (Rust)

Unlike monolithic scripts, this engine is decoupled into specialized modules to ensure maintainability and high-speed execution:

* **`main.rs` (The Orchestrator)**: Manages the asynchronous lifecycle, block subscriptions, and cross-module communication.
* **`math.rs` (DeFi Logic)**: Handles precise Uniswap V3 calculations, including Tick-to-Price conversions using Q64.96 fixed-point math to ensure local simulation accuracy.
* **`executor.rs` (Transaction Layer)**: Implements a sophisticated gas bidding strategy (dynamic estimation + 20% buffer) and handles secure transaction signing and propagation.
* **`state.rs` (Data Management)**: Utilizes thread-safe `DashMap` for high-performance caching of pool metadata and static token info, minimizing redundant RPC overhead.

## 🛡 Security & Smart Contract Engineering

The `ArbFlashBot.sol` contract is built with a security-first mindset, focusing on reliability in volatile markets:

* **Capital Efficiency**: Integrated with the **Balancer Vault** to perform zero-fee flash loans, maximizing the net profit of every arbitrage opportunity.
* **Resilient Token Interaction**: Implements a `IERC20Relaxed` interface to maintain compatibility with non-standard tokens (e.g., those that omit return values on `transfer`), a common edge case in emerging assets.
* **Atomic Safety**: Enforces strict profit checks and utilizes low-level `_safeApprove` calls to prevent contract stalls during interaction with complex or malicious token logic.

## ⚡ Technical Specifications

| Component | Technology | Role |
| :--- | :--- | :--- |
| **Runtime** | Rust (Tokio Async) | Concurrent block processing and simulation. |
| **Blockchain Lib** | Alloy-rs | High-performance JSON-RPC and WebSocket interaction. |
| **Smart Contracts** | Solidity 0.8.20 | Atomic multi-hop execution and flash loan management. |
| **Strategy** | Cross-DEX Arbitrage | Target: Uniswap V3 (Concentrated Liquidity) & Aerodrome. |

## 🛠 Environmental Reproducibility

This project uses a dedicated `rust-toolchain.toml` to lock the compiler version, ensuring consistent builds across different development environments.
