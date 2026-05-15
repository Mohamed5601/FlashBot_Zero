use anyhow::Result;
use alloy::{
    network::Ethereum,
    primitives::{Address, U256, B256},
    providers::Provider,
    transports::Transport,
    sol,
    rpc::types::eth::Log,
};
use std::sync::Arc;
use tokio::sync::RwLock;
use std::collections::HashMap;
use std::marker::PhantomData;

sol! {
    #[sol(rpc)] // ضروري لتوليد دالة new والاتصال بالشبكة
    interface ArbFlashBot {
        // يجب أن تطابق التوقيع في Solidity تماماً
        function checkAndShoot(
            address poolAddress, 
            address tokenA, address tokenB, address tokenC,
            uint24 fee1, uint24 fee2, uint24 fee3,
            uint256 loanAmount, uint256 minProfit
        ) external;
    }
}
#[derive(Debug, Clone)]
pub struct PoolState {
    pub address: Address,
    pub token0: Address,
    pub token1: Address,
    pub fee: u32,
    pub tick: i32,
    pub tick_spacing: i32,
    pub liquidity: u128,
    pub sqrt_price_x96: U256,
    pub ticks: HashMap<i32, i128>, // لتخزين السيولة عند الـ Ticks
}

pub struct MultiPoolManager<P, T> {
    provider: P,
    pub pools: Arc<RwLock<HashMap<Address, PoolState>>>,
    _marker: PhantomData<T>,
}

impl<P, T> MultiPoolManager<P, T> 
where 
    P: Provider<T, Ethereum> + Clone + 'static,
    T: Transport + Clone,
{
    pub fn new(provider: P) -> Self {
        Self {
            provider,
            pools: Arc::new(RwLock::new(HashMap::new())),
            _marker: PhantomData,
        }
    }

    pub async fn initialize_pool(&self, addr: Address, _t0: Address, _t1: Address, fee: u32, spacing: i32) -> Result<()> {
       let contract = IUniswapV3Pool::new(addr, self.provider.clone());
        let slot0 = contract.slot0().call().await?;
        let liq = contract.liquidity().call().await?;

        let pool = PoolState {
            address: addr,
            token0: _t0,
            token1: _t1,
            fee,
            tick: slot0.tick.into(),
            tick_spacing: spacing,
            liquidity: liq.liquidity,
            sqrt_price_x96: slot0.sqrtPriceX96,
            ticks: HashMap::new(),
        };

        self.pools.write().await.insert(addr, pool);
        Ok(())
    }

    pub async fn update_from_log(&self, log: &Log) -> Option<Address> {
        let addr = log.address();
        // هنا يتم تحديث السعر بناء على حدث الـ Swap (تبسيطاً سنعيد العنوان)
        Some(addr)
    }

    pub async fn get_pool(&self, addr: &Address) -> Option<PoolState> {
        self.pools.read().await.get(addr).cloned()
    }
}