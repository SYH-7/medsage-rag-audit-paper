#!/usr/bin/env python
"""run_all_revision_v5_fixed.py — 一键运行修正版流水线（01–12）。

用法：python outputs/revision_v5_mmr_topk_fixed/scripts/run_all_revision_v5_fixed.py
Q1/E2 预测复用 revision_v5_mmr_topk/cache，不重新训练。
"""
import io, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
LOG = HERE.parent / "logs"
LOG.mkdir(parents=True, exist_ok=True)

STEPS = [
    ("01_scan_and_validate.py", "扫描与数据版本验证"),
    ("02_reproduce_frozen_k5.py", "全精度复现 K=5 冻结结果（门控）"),
    ("03_validate_mmr_inputs.py", "验证 MMR 输入与 λ=1 复现 B0"),
    ("04_run_mmr_dev.py", "formal_dev λ 选择"),
    ("05_run_mmr_frozen_tests.py", "三划分 MMR 冻结测试"),
    ("06_mmr_bootstrap_statistics.py", "MMR 显著性（配对 Bootstrap 修复 + Holm）"),
    ("07_run_topk_sensitivity.py", "Top-K 逐 qid+汇总"),
    ("08_topk_difference_analysis.py", "Top-K 差值+稳定性"),
    ("09_demand_category_analysis.py", "D01-D06 类别覆盖"),
    ("10_generate_figures.py", "生成图表"),
    ("11_generate_excel.py", "论文紧凑表 + Excel 汇总（修正版）"),
    ("12_generate_narrative_material.py", "叙事/段落/QC/Summary/打包"),
]


def main():
    t0 = time.time()
    failed = []
    for name, desc in STEPS:
        t1 = time.time()
        logf = LOG / f"{name}.log"
        with io.open(logf, "w", encoding="utf-8") as f:
            r = subprocess.run([sys.executable, str(HERE / name)], stdout=f, stderr=subprocess.STDOUT)
        status = "OK" if r.returncode == 0 else "FAIL"
        print(f"[{status}] {desc} ({name}) {time.time()-t1:.0f}s")
        if r.returncode != 0:
            failed.append(name)
    print(f"\n总耗时 {time.time()-t0:.0f}s；失败步骤：{failed if failed else '无'}")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
