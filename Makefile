PY := C:/Users/Manit/AppData/Local/Programs/Python/Python311/python.exe

.PHONY: setup test validate check collect normalize cleanup archive-dry-run routes

setup:
	$(PY) -c "print('No package install required for local script workspace')"

test:
	$(PY) -m py_compile scripts/source_registry.py scripts/source_clis.py scripts/intelligence_queue.py scripts/test_intelligence_queue.py scripts/test_post_generation.py scripts/phase1_collect.py scripts/queue_maintenance.py scripts/aggregate_deep_discovery.py scripts/aggregate_news.py scripts/final_hybrid_aggregator.py scripts/flash_hunt.py scripts/merge_breadth.py scripts/generated_codegen.py scripts/process_news.py scripts/archive_stale_files.py scripts/validate_schemas.py scripts/x_distribution.py scripts/reddit_mcp_buddy_collect.py scripts/finance_market_collector.py scripts/startup_funding_collector.py
	$(PY) scripts/test_intelligence_queue.py
	$(PY) scripts/test_post_generation.py
	node --check scripts/reddit_mcp_buddy_bridge.mjs

validate:
	$(PY) scripts/x_distribution.py validate

routes:
	$(PY) scripts/x_distribution.py routes

check: test validate routes

collect:
	$(PY) scripts/x_distribution.py collect

normalize:
	$(PY) scripts/x_distribution.py normalize

archive-dry-run:
	$(PY) scripts/archive_stale_files.py

cleanup:
	$(PY) scripts/x_distribution.py cleanup
