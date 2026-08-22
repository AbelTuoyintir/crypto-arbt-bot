require('dotenv').config();
const { ethers } = require("ethers");
const axios = require('axios');

// ------------------------
// Provider & Wallet Setup
// ------------------------
const provider = new ethers.JsonRpcProvider(process.env.BSC_RPC);
const wallet = new ethers.Wallet(process.env.PRIVATE_KEY, provider);

// ------------------------
// PancakeSwap Subgraph URL
// ------------------------
const SUBGRAPH_URL = 'https://api.thegraph.com/subgraphs/name/pancakeswap/exchange-v2';

// ------------------------
// Fetch Pairs from PancakeSwap
// ------------------------
async function fetchPairs() {
    const query = `
    {
      pairs(first: 1000) {
        id
        token0 { symbol id }
        token1 { symbol id }
        reserve0
        reserve1
      }
    }`;
    try {
        const response = await axios.post(SUBGRAPH_URL, { query });
        return response.data.data.pairs;
    } catch (err) {
        console.error("Error fetching pairs:", err.message);
        return [];
    }
}

// ------------------------
// AMM Swap Simulation
// ------------------------
function getAmountOut(amountIn, reserveIn, reserveOut) {
    const amountInWithFee = amountIn * 997; // PancakeSwap fee
    const numerator = amountInWithFee * reserveOut;
    const denominator = reserveIn * 1000 + amountInWithFee;
    return numerator / denominator;
}

function estimateProfit(amountIn, pair) {
    const output = getAmountOut(amountIn, pair.reserve0, pair.reserve1);
    return output - amountIn;
}

// ------------------------
// Rank Pairs by Profit
// ------------------------
function rankPairs(pairs, amountIn) {
    return pairs
        .map(p => {
            const profit = estimateProfit(amountIn, p);
            return { pair: p, profit };
        })
        .sort((a, b) => b.profit - a.profit);
}

// ------------------------
// Main Loop
// ------------------------
async function main() {
    const amountIn = 1000; // Test amount, adjust after testing

    const pairs = await fetchPairs();
    if (!pairs.length) return;

    const ranked = rankPairs(pairs, amountIn);

    const top = ranked[0];
    console.log("🔥 Top Arbitrage Pair:");
    console.log(`Pair: ${top.pair.token0.symbol}/${top.pair.token1.symbol}`);
    console.log(`Estimated Profit: ${top.profit.toFixed(6)} units`);

    if (!pairs.length) return;

    const ranked = rankPairs(pairs, amountIn);
    const top = ranked[0];

    console.log("🔥 Top Arbitrage Pair:");
    console.log(`Pair: ${top.pair.token0.symbol}/${top.pair.token1.symbol}`);
    console.log(`Estimated Profit: ${top.profit.toFixed(6)} units`);

    // Send email if profitable
    if (top.profit > 0) {
        const subject = `Top Arbitrage Alert: ${top.pair.token0.symbol}/${top.pair.token1.symbol}`;
        const text = `Pair: ${top.pair.token0.symbol}/${top.pair.token1.symbol}\nEstimated Profit:    ${top.profit.toFixed(6)} units\nTime: ${new Date().toLocaleString()}`;
        await sendEmail(subject, text);
    }
}

setInterval(main, 5000); // Run every 5 seconds