import pytest
from triangular_bot import create_triangular_bot_engine, run_triangular_bot

def test_create_triangular_bot_engine():
    dex_manager, engine, scanner = create_triangular_bot_engine()
    assert dex_manager is not None
    assert engine is not None
    assert scanner is not None

def test_run_triangular_bot_single_run(caplog):
    import logging
    caplog.set_level(logging.INFO)

    # Run a single market scan iteration
    run_triangular_bot(interval=1, iterations=1, initial_gat=50.0, single_run=True)

    # Verify log messages contain expected initialization and summary text
    assert "GAT ENHANCED TRIANGULAR ARBITRAGE BOT INITIALIZED" in caplog.text
    assert "Target Win Rate   : 95.0%" in caplog.text
    assert "Win Rate:" in caplog.text
    assert "Completed requested scanning iterations" in caplog.text

def test_run_triangular_bot_auto_generate_pairs(caplog):
    import logging
    caplog.set_level(logging.INFO)

    # Run single scan with auto_generate_pairs=True and min_confidence=90.0
    run_triangular_bot(
        interval=1,
        iterations=1,
        initial_gat=100.0,
        single_run=True,
        min_confidence=90.0,
        auto_generate_pairs=True
    )

    assert "Min Confidence    : 90.0%" in caplog.text
    assert "Active Pair Paths : 20 pairs" in caplog.text
    assert "Yield Rate:" in caplog.text

def test_run_triangular_bot_target_daily_profit(caplog):
    import logging
    caplog.set_level(logging.INFO)

    run_triangular_bot(
        interval=1,
        iterations=1,
        initial_gat=100.0,
        single_run=True,
        min_confidence=95.0,
        target_daily_profit=15.0
    )

    assert "Daily Profit Target: 15.0%" in caplog.text
    assert "Target: 15.0%" in caplog.text
