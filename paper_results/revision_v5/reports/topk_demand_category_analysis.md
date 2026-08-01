# D01-D06 需求类别覆盖分析（fixed）

> **D01-D06 是本任务的操作性信息需求分类，不是 ICD 或 SNOMED CT 临床术语本体。**

定义：覆盖率 = 在 gold 查询含该类别的 qid 中，选择结果覆盖该类别的比例（条件覆盖率）。

## 关键观察

- formal_train：B0 随 K 增加（K3→K7）增幅最大的类别：**D05_care_emergency**（Δ=+0.237）。
- formal_train：K=3 时 B0 覆盖率最低（最易遗漏）：**D05_care_emergency**（0.539）。
- formal_train：MMR-TFIDF 相对 B0 提升最明显的类别：**D05_care_emergency**（Δ=+0.053）。
- internal_blind：B0 随 K 增加（K3→K7）增幅最大的类别：**D05_care_emergency**（Δ=+0.224）。
- internal_blind：K=3 时 B0 覆盖率最低（最易遗漏）：**D05_care_emergency**（0.571）。
- internal_blind：MMR-TFIDF 相对 B0 提升最明显的类别：**D05_care_emergency**（Δ=+0.061）。
- cmedqa2_external：B0 随 K 增加（K3→K7）增幅最大的类别：**D05_care_emergency**（Δ=+0.308）。
- cmedqa2_external：K=3 时 B0 覆盖率最低（最易遗漏）：**D05_care_emergency**（0.615）。
- cmedqa2_external：MMR-TFIDF 相对 B0 提升最明显的类别：**D04_population_history**（Δ=+0.016）。

## 明细

逐 split × method × K × category 覆盖率与分母见 `tables/topk_demand_category_coverage.csv`。
