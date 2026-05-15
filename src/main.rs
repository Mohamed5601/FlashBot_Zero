use anyhow::Result;
use alloy::{
    network::{Ethereum, EthereumWallet},
    primitives::{address, Address, U256, B256, Bytes}, 
    providers::{Provider, ProviderBuilder, RootProvider, WsConnect},
    signers::local::PrivateKeySigner,
    sol,
    transports::http::{Client, Http},
    transports::Transport,
    rpc::types::eth::Filter,
};
use std::sync::{Arc, atomic::{AtomicUsize, Ordering}};
use dashmap::DashMap;
use futures_util::StreamExt; 
use dotenv::dotenv;
use std::env;
use url::Url;
use tokio::sync::mpsc;
use tokio::time::{sleep, Duration}; 

// تعريف الواجهات
sol! {
    #[sol(rpc)]
    interface IArbDominator {
        function executeArb(
            address tokenA, 
            uint256 loanAmount, 
            uint256 minProfit, 
            bytes calldata swapPath
        ) external;
    }

    #[sol(rpc)]
    interface IUniswapV3Pool {
        function token0() external view returns (address);
        function token1() external view returns (address);
        function fee() external view returns (uint24);
        function liquidity() external view returns (uint128);
    }
}

fn encode_path_v3(token_a: Address, fee1: u32, token_b: Address, fee2: u32, token_c: Address, fee3: u32) -> Vec<u8> {
    let mut path = Vec::new();
    path.extend_from_slice(token_a.as_slice());
    path.extend_from_slice(&fee1.to_be_bytes()[1..4]); 
    path.extend_from_slice(token_b.as_slice());
    path.extend_from_slice(&fee2.to_be_bytes()[1..4]);
    path.extend_from_slice(token_c.as_slice());
    path.extend_from_slice(&fee3.to_be_bytes()[1..4]);
    path.extend_from_slice(token_a.as_slice()); 
    path
}

#[derive(Debug, Clone)]
pub struct PoolStaticInfo {
    pub address: Address,
    pub token0: Address,
    pub token1: Address,
    pub fee: u32, 
}

// المحرك النووي (V11)
pub struct DominatorEngine<P, T> {
    main_provider: P, 
    read_providers: Vec<Arc<RootProvider<Http<Client>>>>,
    counter: AtomicUsize,
    
    pub static_pools: Arc<DashMap<Address, PoolStaticInfo>>, 
    pub last_checked_block: Arc<DashMap<Address, u64>>,
    pub bot_contract: Address,
    _marker: std::marker::PhantomData<T>,
}

impl<P, T> DominatorEngine<P, T> 
where P: Provider<T, Ethereum> + Clone + 'static, T: Transport + Clone,
{
    pub fn new(provider: P, bot_contract: Address) -> Self {
        // قائمة مزودين قوية جداً
        let rpc_sources = vec![
            "https://mainnet.base.org",
            "https://base.llamarpc.com",
            "https://base-mainnet.public.blastapi.io",
            "https://1rpc.io/base",
            "https://base.meowrpc.com",
            "https://base-rpc.publicnode.com",
            "https://base.drpc.org",
            "https://base.gateway.tenderly.co",
            "https://public.stackup.sh/api/v1/node/base-mainnet",
            "https://base-pokt.nodies.app",
        ];

        let mut readers = Vec::new();
        if let Ok(env_rpc) = env::var("RPC_URL") {
            if let Ok(u) = Url::parse(&env_rpc) {
                readers.push(Arc::new(ProviderBuilder::new().on_http(u)));
            }
        }

        for rpc in rpc_sources {
            if let Ok(u) = Url::parse(rpc) {
                let p = ProviderBuilder::new().on_http(u);
                readers.push(Arc::new(p));
            }
        }

        println!("☢️  NUCLEAR ENGINE V11: Loaded {} RPCs. Gas Aggression: HIGH.", readers.len());

        Self { 
            main_provider: provider, 
            read_providers: readers,
            counter: AtomicUsize::new(0),
            static_pools: Arc::new(DashMap::new()), 
            last_checked_block: Arc::new(DashMap::new()),
            bot_contract,
            _marker: std::marker::PhantomData 
        }
    }

    fn get_reader(&self) -> Arc<RootProvider<Http<Client>>> {
        let c = self.counter.fetch_add(1, Ordering::Relaxed);
        let idx = c % self.read_providers.len();
        self.read_providers[idx].clone()
    }

    pub async fn get_or_fetch_static_info(&self, pool_address: Address) -> Option<PoolStaticInfo> {
        if let Some(info) = self.static_pools.get(&pool_address) {
            return Some(info.clone());
        }

        let reader = self.get_reader();
        let contract = IUniswapV3Pool::new(pool_address, reader);
        
        let t0 = match contract.token0().call().await { Ok(v) => v._0, Err(_) => return None };
        let t1 = match contract.token1().call().await { Ok(v) => v._0, Err(_) => return None };
        let fee = match contract.fee().call().await { Ok(v) => v._0, Err(_) => return None };

        let info = PoolStaticInfo {
            address: pool_address,
            token0: t0,
            token1: t1,
            fee: fee as u32,
        };
        self.static_pools.insert(pool_address, info.clone());
        Some(info)
    }

    pub fn cache_new_pool(&self, pool: Address, t0: Address, t1: Address, fee: u32) {
        let info = PoolStaticInfo { address: pool, token0: t0, token1: t1, fee };
        self.static_pools.insert(pool, info);
    }

    pub async fn should_check_pool(&self, pool_addr: Address) -> bool {
        let reader = self.get_reader();
        match reader.get_block_number().await {
            Ok(current_block) => {
                if let Some(last_block) = self.last_checked_block.get(&pool_addr) {
                    if *last_block >= current_block { return false; }
                }
                self.last_checked_block.insert(pool_addr, current_block);
                true
            },
            Err(_) => true 
        }
    }

pub async fn execute_attack(&self, info: &PoolStaticInfo) -> Result<()> {
        let token_a = info.token0;
        let token_b = info.token1;
        
        let token_usdc = address!("833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"); 
        let token_weth = address!("4200000000000000000000000000000000000006"); 
        let token_virtual = address!("0b3e328455c4059eeb9e37430e581849afb33844"); 

        let fee_medium = 500;   
        let fee_high = 3000;
        let fee_meme = 10000;

        let amount_in = U256::from(500000000000000000u128); // 0.5 ETH
        let min_profit_wei = U256::from(1u128); 

        let path_usdc = encode_path_v3(token_a, info.fee, token_b, fee_medium, token_usdc, fee_high);
        let path_weth = encode_path_v3(token_a, info.fee, token_b, fee_medium, token_weth, fee_high);
        let path_virtual = encode_path_v3(token_a, info.fee, token_b, fee_medium, token_virtual, fee_high);
        let path_meme = encode_path_v3(token_a, info.fee, token_b, fee_meme, token_weth, fee_meme);

        let r1 = self.get_reader();
        let r2 = self.get_reader();
        let r3 = self.get_reader();
        let r4 = self.get_reader();

        let c1 = IArbDominator::new(self.bot_contract, r1);
        let c2 = IArbDominator::new(self.bot_contract, r2);
        let c3 = IArbDominator::new(self.bot_contract, r3);
        let c4 = IArbDominator::new(self.bot_contract, r4);
        
        let tx1 = c1.executeArb(token_a, amount_in, min_profit_wei, Bytes::from(path_usdc.clone()));
        let tx2 = c2.executeArb(token_a, amount_in, min_profit_wei, Bytes::from(path_weth.clone()));
        let tx3 = c3.executeArb(token_a, amount_in, min_profit_wei, Bytes::from(path_virtual.clone()));
        let tx4 = c4.executeArb(token_a, amount_in, min_profit_wei, Bytes::from(path_meme.clone()));

        // محاكاة سريعة
        let (res1, res2, res3, res4) = tokio::join!(
            async { tx1.estimate_gas().await.ok() },
            async { tx2.estimate_gas().await.ok() },
            async { tx3.estimate_gas().await.ok() },
            async { tx4.estimate_gas().await.ok() }
        );

        let (gas_estimate, route, best_path) = if let Some(gas) = res4 {
            (gas, "MEME", path_meme)
        } else if let Some(gas) = res2 {
            (gas, "WETH", path_weth)
        } else if let Some(gas) = res1 {
            (gas, "USDC", path_usdc)
        } else if let Some(gas) = res3 {
            (gas, "VIRTUAL", path_virtual)
        } else {
            return Ok(()); 
        };

        // --- مرحلة التنفيذ (تعديل الـ Bribe) ---
        let contract_write = IArbDominator::new(self.bot_contract, self.main_provider.clone());
        let final_call = contract_write.executeArb(token_a, amount_in, min_profit_wei, Bytes::from(best_path));

        // 1. نجيب سعر الشبكة الحالي
        let reader_gas = self.get_reader();
        let current_gas = reader_gas.get_gas_price().await.unwrap_or(100_000); // Default low
        let current_gas_u256 = U256::from(current_gas);
        
        // 2. نحسب "البقشيش" (Hard Tip)
        // هندفع سعر الشبكة + 0.05 Gwei (رقم ثابت ومغري)
        // 1 Gwei = 1,000,000,000 Wei
        // 0.05 Gwei = 50,000,000 Wei
        let miner_tip = U256::from(50_000_000u128); 
        
        let bid_gas = current_gas_u256 + miner_tip;
        let bid_gas_u128 = u128::try_from(bid_gas).unwrap_or(u128::MAX);

        let final_tx = final_call.gas(u128::from(gas_estimate)).gas_price(bid_gas_u128);

        println!("⚡ BRIBE ATTACK [{}] | Gas Price: {} Wei (Includes Tip)", route, bid_gas_u128);
        
        // 3. Retry Loop (الإصرار على الإرسال)
        for i in 0..3 {
            match final_tx.send().await {
                Ok(pending) => {
                    println!("🚀 Tx Sent (Attempt {}): {:?}", i+1, pending.tx_hash());
                    // مهم: خذ الـ Hash ده وافحصه على basescan.org عشان تشوف كسبت كام
                    break; 
                },
                Err(e) => {
                    eprintln!("⚠️ Send Failed (Attempt {}): Retrying...", i+1);
                    sleep(Duration::from_millis(50)).await; // تقليل وقت الانتظار لـ 50ms
                }
            }
        }

        Ok(())
    }
}
enum BotTask {
    NewPool(Address, Address, Address, u32),
    CheckPool(Address),
}

#[tokio::main]
async fn main() -> Result<()> {
    dotenv().ok();
    
    let http_url_str = env::var("RPC_URL").expect("Missing RPC_URL");
    let ws_url_str = env::var("WS_RPC_URL").expect("Missing WS_RPC_URL");
    let bot_contract_addr: Address = env::var("CONTRACT_ADDRESS")?.parse()?;
    let private_key = env::var("PRIVATE_KEY")?;
    let signer: PrivateKeySigner = private_key.parse()?;
    let wallet = EthereumWallet::from(signer);

    let http_url = Url::parse(&http_url_str)?;
    let http_provider = ProviderBuilder::new().with_recommended_fillers().wallet(wallet.clone()).on_http(http_url);
    let http_provider = Arc::new(http_provider);

    let ws_connect = WsConnect::new(ws_url_str);
    let ws_provider = ProviderBuilder::new().on_ws(ws_connect).await?;
    let ws_provider = Arc::new(ws_provider);

    let engine = Arc::new(DominatorEngine::<_, _>::new(http_provider.clone(), bot_contract_addr));

    let (tx, mut rx) = mpsc::channel::<BotTask>(20000);

    println!("☢️  L2 DOMINATOR V11: NUCLEAR OPTION.");
    println!("🔥 High Gas Bidding + Auto-Retry on Send.");

    let tx_factory = tx.clone();
    let ws_factory = ws_provider.clone();
    tokio::spawn(async move {
        let factory = address!("33128a8fC17869897dcE68Ed026d694621f6FDfD");
        let sig: B256 = "783cca1c0412dd0d695e784568c96da2e9c22ff989357a2e8b1d9b2b4e6b7118".parse().unwrap();
        let filter = Filter::new().address(factory).event_signature(sig);

        loop {
            if let Ok(sub) = ws_factory.subscribe_logs(&filter).await {
                let mut stream = sub.into_stream();
                while let Some(log) = stream.next().await {
                    if log.topics().len() < 4 { continue; }
                    let t0 = Address::from_word(log.topics()[1]);
                    let t1 = Address::from_word(log.topics()[2]);
                    let fee = U256::from_be_bytes(log.topics()[3].into()).to::<u32>();
                    let pool = Address::from_slice(&log.data().data[44..64]);
                    let _ = tx_factory.send(BotTask::NewPool(pool, t0, t1, fee)).await;
                }
            } else {
                eprintln!("⚠️ WS Reconnecting...");
                sleep(Duration::from_secs(1)).await;
            }
        }
    });

    let tx_swaps = tx.clone();
    let ws_swaps = ws_provider.clone();
    tokio::spawn(async move {
        let swap_sig: B256 = "0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67".parse().unwrap();
        let filter = Filter::new().event_signature(swap_sig);

        loop {
            if let Ok(sub) = ws_swaps.subscribe_logs(&filter).await {
                let mut stream = sub.into_stream();
                while let Some(log) = stream.next().await {
                    let _ = tx_swaps.send(BotTask::CheckPool(log.address())).await;
                }
            } else {
                sleep(Duration::from_secs(1)).await;
            }
        }
    });

    while let Some(task) = rx.recv().await {
        let eng = engine.clone();
        
        match task {
            BotTask::NewPool(pool, t0, t1, fee) => {
                let weth = address!("4200000000000000000000000000000000000006");
                let usdc = address!("833589fCD6eDb6E08f4c7C32D4f71b54bdA02913");
                if t0 == weth || t1 == weth || t0 == usdc || t1 == usdc {
                    tokio::spawn(async move {
                        eng.cache_new_pool(pool, t0, t1, fee);
                        let info = PoolStaticInfo { address: pool, token0: t0, token1: t1, fee };
                        let _ = eng.execute_attack(&info).await;
                    });
                }
            },
            BotTask::CheckPool(pool_addr) => {
                tokio::spawn(async move {
                    if !eng.should_check_pool(pool_addr).await { return; }
                    if let Some(info) = eng.get_or_fetch_static_info(pool_addr).await {
                         let _ = eng.execute_attack(&info).await;
                    }
                });
            }
        }
    }

    Ok(())
}