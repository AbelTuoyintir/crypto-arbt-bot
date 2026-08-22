require('dotenv').config();
const axios = require('axios');
const crypto = require('crypto');

const apiKey = process.env.API_KEY;
const secretKey = process.env.SECRET_KEY;
const baseUrl = 'https://testnet.binance.vision/api/v3/order';

function buildQuery(params) {
  return new URLSearchParams(params).toString();
}

async function createOrder() {
  if (!apiKey || !secretKey) {
    throw new Error('Missing API_KEY or SECRET_KEY in .env');
  }

  const params = {
    symbol: 'LTCBTC',
    side: 'BUY',
    type: 'LIMIT',
    timeInForce: 'GTC',
    quantity: '1',
    price: '0.1',
    recvWindow: '5000',
    timestamp: Date.now().toString(),
  };

  const query = buildQuery(params);
  const signature = crypto.createHmac('sha256', secretKey).update(query).digest('hex');
  const url = `${baseUrl}?${query}&signature=${signature}`;

  try {
    const response = await axios.post(url, null, {
      headers: {
        'X-MBX-APIKEY': apiKey,
      },
    });

    console.log('✅ Binance order response:');
    console.log(response.data);
  } catch (err) {
    if (err.response) {
      console.error('❌ Binance API error:', err.response.status, err.response.data);
    } else {
      console.error('❌ Request error:', err.message);
    }
    process.exit(1);
  }
}

if (require.main === module) {
  createOrder();
}

module.exports = { createOrder };
