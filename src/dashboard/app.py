from flask import Flask, render_template_string, jsonify
from datetime import datetime, timezone, timedelta
from config.settings import settings
from src.db.models import SessionLocal, Opportunity, Trade, Token
from src.wallet.wallet_manager import WalletManager

app = Flask(__name__)
wallet_mgr = WalletManager()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>GAT Arbitrage Bot Dashboard</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #1a1e24; color: #e1e6ed; margin: 0; padding: 20px; }
        h1, h2 { color: #00d2ff; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; margin-bottom: 25px; }
        .card { background: #232931; border-radius: 8px; padding: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); border-top: 4px solid #00d2ff; }
        .card h3 { margin-top: 0; color: #8a99ad; font-size: 0.9em; text-transform: uppercase; }
        .card .value { font-size: 1.8em; font-weight: bold; color: #ffffff; margin: 10px 0; }
        .metric-list { list-style: none; padding: 0; margin: 0; }
        .metric-list li { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #2e3642; }
        .metric-list li:last-child { border-bottom: none; }
        .status-badge { padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 0.85em; }
        .status-success { background: #28a745; color: #fff; }
        .status-rejected { background: #dc3545; color: #fff; }
        table { width: 100%; border-collapse: collapse; background: #232931; border-radius: 8px; overflow: hidden; }
        th, td { padding: 12px 15px; text-align: left; border-bottom: 1px solid #2e3642; }
        th { background: #2e3642; color: #00d2ff; text-transform: uppercase; font-size: 0.85em; }
        tr:hover { background: #2a313a; }
    </style>
</head>
<body>
    <h1>🚀 GAT Arbitrage Bot Dashboard</h1>
    <p>Base Token: <strong>{{ settings.BASE_TOKEN_NAME }} ({{ settings.BASE_TOKEN_SYMBOL }})</strong> | Mode: <strong>{{ settings.TRADING_MODE.upper() }}</strong></p>

    <!-- Metrics Grid -->
    <div class="grid">
        <!-- Portfolio -->
        <div class="card">
            <h3>Portfolio</h3>
            <ul class="metric-list">
                <li><span>GAT Balance:</span> <strong>{{ "%.2f"|format(portfolio.gat_balance) }} {{ settings.BASE_TOKEN_SYMBOL }}</strong></li>
                <li><span>Total Value:</span> <strong>{{ "%.2f"|format(portfolio.total_value) }} {{ settings.BASE_TOKEN_SYMBOL }}</strong></li>
                <li><span>Available Balance:</span> <strong>{{ "%.2f"|format(portfolio.available_balance) }} {{ settings.BASE_TOKEN_SYMBOL }}</strong></li>
                <li><span>Locked Balance:</span> <strong>{{ "%.2f"|format(portfolio.locked_balance) }} {{ settings.BASE_TOKEN_SYMBOL }}</strong></li>
            </ul>
        </div>

        <!-- Arbitrage -->
        <div class="card">
            <h3>Arbitrage Metrics</h3>
            <ul class="metric-list">
                <li><span>Opportunities Found:</span> <strong>{{ arbitrage.found }}</strong></li>
                <li><span>Profitable Opportunities:</span> <strong>{{ arbitrage.profitable }}</strong></li>
                <li><span>Rejected Opportunities:</span> <strong>{{ arbitrage.rejected }}</strong></li>
                <li><span>Executed Trades:</span> <strong>{{ arbitrage.executed }}</strong></li>
                <li><span>Successful / Failed:</span> <strong>{{ arbitrage.successful }} / {{ arbitrage.failed }}</strong></li>
            </ul>
        </div>

        <!-- Profit -->
        <div class="card">
            <h3>Profit Performance</h3>
            <ul class="metric-list">
                <li><span>Today's Profit:</span> <strong>{{ "%.4f"|format(profit.today) }} {{ settings.BASE_TOKEN_SYMBOL }}</strong></li>
                <li><span>Weekly Profit:</span> <strong>{{ "%.4f"|format(profit.weekly) }} {{ settings.BASE_TOKEN_SYMBOL }}</strong></li>
                <li><span>Total Profit:</span> <strong>{{ "%.4f"|format(profit.total) }} {{ settings.BASE_TOKEN_SYMBOL }}</strong></li>
                <li><span>Avg Profit / Trade:</span> <strong>{{ "%.4f"|format(profit.avg_per_trade) }} {{ settings.BASE_TOKEN_SYMBOL }}</strong></li>
            </ul>
        </div>

        <!-- Risk -->
        <div class="card">
            <h3>Risk Controls</h3>
            <ul class="metric-list">
                <li><span>High-Risk Tokens Blocked:</span> <strong>{{ risk.blocked_tokens }}</strong></li>
                <li><span>Failed Simulations:</span> <strong>{{ risk.failed_simulations }}</strong></li>
                <li><span>Failed Sell Tests:</span> <strong>{{ risk.failed_sell_tests }}</strong></li>
                <li><span>Liquidity Warnings:</span> <strong>{{ risk.liquidity_warnings }}</strong></li>
                <li><span>Slippage Warnings:</span> <strong>{{ risk.slippage_warnings }}</strong></li>
            </ul>
        </div>
    </div>

    <!-- Recent Opportunities -->
    <h2>Recent Opportunities</h2>
    <table>
        <thead>
            <tr>
                <th>ID</th>
                <th>Target Token</th>
                <th>DEX</th>
                <th>Initial GAT</th>
                <th>Exp. Final GAT</th>
                <th>Profit (%)</th>
                <th>Risk Score</th>
                <th>Status</th>
            </tr>
        </thead>
        <tbody>
            {% for opp in opportunities %}
            <tr>
                <td>{{ opp.id }}</td>
                <td>{{ (opp.target_token|string)[:10] }}...</td>
                <td>{{ opp.dex }}</td>
                <td>{{ "%.2f"|format(opp.initial_gat) }}</td>
                <td>{{ "%.2f"|format(opp.expected_final_gat) }}</td>
                <td>{{ "%.2f"|format(opp.profit_percentage) }}%</td>
                <td>{{ "%.1f"|format(opp.risk_score) }}</td>
                <td><span class="status-badge status-{{ 'success' if opp.status == 'executed' else 'rejected' }}">{{ opp.status.upper() }}</span></td>
            </tr>
            {% else %}
            <tr><td colspan="8" style="text-align:center; color:#8a99ad;">No opportunities recorded yet.</td></tr>
            {% endfor %}
        </tbody>
    </table>
</body>
</html>
"""

@app.route("/")
def dashboard():
    db = SessionLocal()
    try:
        # Portfolio calculations
        gat_bal = wallet_mgr.get_token_balance(settings.BASE_TOKEN_ADDRESS) if wallet_mgr.has_wallet() else 1000.0
        portfolio = {
            "gat_balance": gat_bal,
            "total_value": gat_bal,
            "available_balance": gat_bal,
            "locked_balance": 0.0
        }

        # Arbitrage metrics
        opps = db.query(Opportunity).all()
        trades = db.query(Trade).all()

        found = len(opps)
        profitable = len([o for o in opps if o.estimated_profit > 0])
        rejected = len([o for o in opps if o.status == 'rejected'])
        executed = len(trades)
        successful = len([t for t in trades if t.status == 'success'])
        failed = len([t for t in trades if t.status == 'failed'])

        arbitrage = {
            "found": found,
            "profitable": profitable,
            "rejected": rejected,
            "executed": executed,
            "successful": successful,
            "failed": failed
        }

        # Profit metrics
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = now - timedelta(days=7)

        successful_trades = [t for t in trades if t.status == 'success']

        today_profit = sum(t.actual_profit for t in successful_trades if t.created_at and t.created_at.replace(tzinfo=timezone.utc) >= today_start)
        weekly_profit = sum(t.actual_profit for t in successful_trades if t.created_at and t.created_at.replace(tzinfo=timezone.utc) >= week_start)
        total_profit = sum(t.actual_profit for t in successful_trades)
        avg_profit = (total_profit / len(successful_trades)) if successful_trades else 0.0

        profit = {
            "today": today_profit,
            "weekly": weekly_profit,
            "total": total_profit,
            "avg_per_trade": avg_profit
        }

        # Risk metrics
        blocked_tokens = db.query(Token).filter(Token.risk_score > settings.MAX_TOKEN_RISK_SCORE).count()
        risk = {
            "blocked_tokens": blocked_tokens,
            "failed_simulations": len([o for o in opps if o.status == 'rejected']),
            "failed_sell_tests": len([o for o in opps if o.expected_final_gat == 0]),
            "liquidity_warnings": len([o for o in opps if o.risk_score >= 40]),
            "slippage_warnings": len([o for o in opps if o.slippage > settings.MAX_SLIPPAGE_PERCENT])
        }

        recent_opps = db.query(Opportunity).order_by(Opportunity.id.desc()).limit(10).all()

        return render_template_string(
            HTML_TEMPLATE,
            settings=settings,
            portfolio=portfolio,
            arbitrage=arbitrage,
            profit=profit,
            risk=risk,
            opportunities=recent_opps
        )
    finally:
        db.close()

@app.after_request
def add_security_headers(response):
    # Security headers to protect against clickjacking, MIME sniffing, and XSS
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Content-Security-Policy'] = "default-src 'self' 'unsafe-inline';"
    return response

@app.route("/api/metrics")
def api_metrics():
    db = SessionLocal()
    try:
        total_opps = db.query(Opportunity).count()
        total_trades = db.query(Trade).count()
        successful_trades = db.query(Trade).filter(Trade.status == 'success').all()
        total_profit = sum(t.actual_profit for t in successful_trades)

        return jsonify({
            "status": "online",
            "base_token": settings.BASE_TOKEN_SYMBOL,
            "trading_mode": settings.TRADING_MODE,
            "total_opportunities": total_opps,
            "total_trades": total_trades,
            "total_profit": total_profit
        })
    finally:
        db.close()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
