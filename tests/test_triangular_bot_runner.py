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
    assert "Daily Win Rate:" in caplog.text
    assert "Completed requested scanning iterations" in caplog.text
