use alloy_primitives::{U256 as AlloyU256, I256 as AlloyI256};
use uniswap_v3_math::{swap_math, tick_math};
use crate::state::PoolState;
use primitive_types::U256 as UniU256;

// تحويل فائق السرعة عبر الـ Memory Layout مباشرة
fn to_uni_u256(val: AlloyU256) -> UniU256 {
    UniU256::from_little_endian(&val.to_le_bytes::<32>())
}

fn from_uni_u256(val: UniU256) -> AlloyU256 {
    let mut bytes = [0u8; 32];
    val.to_little_endian(&mut bytes);
    AlloyU256::from_le_bytes(bytes)
}

pub struct SwapResult {
    pub amount_out: AlloyU256,
}

pub fn calculate_swap_nuclear(
    amount_remaining: AlloyI256,
    pool: &PoolState,
    zero_for_one: bool,
) -> Result<SwapResult, &'static str> {
    let sqrt_price_x96 = pool.sqrt_price_x96;
    let liquidity = pool.liquidity;

    let target_price = if zero_for_one { 
        from_uni_u256(tick_math::MIN_SQRT_RATIO) + AlloyU256::from(1)
    } else { 
        from_uni_u256(tick_math::MAX_SQRT_RATIO) - AlloyU256::from(1)
    };

    // الإصلاح الجذري: تحويل Alloy I256 إلى النوع الذي تفهمه المكتبة الرياضية
    let mut i_bytes = [0u8; 32];
    amount_remaining.to_little_endian(&mut i_bytes);
    let amount_uni_v3 = uniswap_v3_math::utils::U256::from_little_endian(&i_bytes);

    // ملاحظة: المكتبة تطلب U256 للقدر المتبقي في الحسابات الداخلية أحياناً
    let (_next_p, step_out, _, _) = swap_math::compute_swap_step(
        to_uni_u256(sqrt_price_x96),
        to_uni_u256(target_price),
        liquidity,
        amount_uni_v3.into(), 
        pool.fee,
    ).map_err(|_| "Compute Swap Fail")?;

    Ok(SwapResult { 
        amount_out: from_uni_u256(step_out) 
    })
}