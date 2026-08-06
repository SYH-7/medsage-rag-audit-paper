# 独立 fixture-only 最小复现（DAKD v6）

- 不含第二工程原始医疗语料；不含私有 truth 明文（值为占位符 FIXTURE_PRIVATE_VALUE）。
- 不接入第二工程检索流程；仅验证冻结检测器（benchmark_v3）在脱敏 fixture 上的可复现性。
- 此 fixture 不等同于第二工程 Dense/Hybrid/Domain 管线验证。
- 运行：`python scripts/dakd_v6/run_tcm_sleep_cross_pipeline.py --fixture-only`
- 测试：`pytest -q tests/dakd_v6_fixture`
