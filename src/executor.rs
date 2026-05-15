use anyhow::Result;
use alloy::{
    network::{Ethereum, EthereumWallet, Network},
    primitives::{Address, U256, B256},
    providers::Provider,
    transports::Transport,
    sol,
};
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

pub struct Executor<P, T> {
    provider: P,
    wallet: EthereumWallet,
    contract_address: Address,
    _marker: PhantomData<T>,
}

impl<P, T> Executor<P, T> 
where 
    P: Provider<T, Ethereum> + Clone + 'static,
    T: Transport + Clone,
{
    pub fn new(provider: P, wallet: EthereumWallet, contract_address: Address) -> Self {
        Self { provider, wallet, contract_address, _marker: PhantomData }
    }

    // داخل executor.rs المحدث
 pub async fn execute_trade(
    &self, 
    params: TriangleParams // ستحتاج لتعريف struct يطابق معاملات العقد
 ) -> Result<()> {
    let contract = ArbFlashBotInstance::new(self.contract_address, self.provider.clone());
    
    // إرسال المعاملة بالبارامترات الـ 9
    let call_builder = contract.checkAndShoot(
        params.pool_address,
        params.tokenA, params.tokenB, params.tokenC,
        params.fee1, params.fee2, params.fee3,
        params.loanAmount, params.minProfit
    );

    let pending_tx = call_builder.send().await?;
    println!("🚀 Transaction Sent: {:?}", pending_tx.tx_hash());
    Ok(())
 }
}