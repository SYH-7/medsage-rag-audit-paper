# PAPER_UPDATE_NOTES — 跨管线受控泄漏验证（第二套中医睡眠 RAG 工程）

> 用途：为论文第 4.5 节、第 5 节、第 6.6 节与结论提供**可引用的事实清单**。
> 只记录事实与数据，不代写、不夸大论文结论。所有数值来源：
> `paper_package_dakd_v6/16_cross_pipeline/` 下的 CSV/JSONL 结果文件（可复算）。
> 本文件不修改论文正文。

---

## 1. 第二工程的真实调用路径（工程证据）

- 第二工程：`tcm_sleep_rag_full`（中医睡眠领域 RAG，Python 3.10 环境，只读接入）。
- 真实入口与调用链（见 `CROSS_PIPELINE_AUDIT.md`）：
  - 服务入口 `rag_service/api.py` → `POST /rag/retrieve`；
  - BM25 检索入口 `rag_service/retriever_bm25.py::BM25Retriever.retrieve(question, top_k)`（jieba 分词 + rank_bm25 打分 + Top-K 排序，**主工程环境实测可运行，单次约 8 ms**）；
  - 融合入口 `retriever_hybrid.py::HybridRetriever.retrieve`（Dense+BM25+RRF）；
  - 领域增强入口 `retriever_domain.py::DomainEnhancedRetriever.retrieve`（term/syndrome/category 加权 + MMR 重排）；
  - 重排序入口 `reranker.py::MMRReranker.rerank`。
- 跨管线案例的**候选生成与 Top-K 选择均真实调用 `BM25Retriever.retrieve()`**，未重写简化排序器，未固定输出，未修改第二工程任何文件（SHA256 基线比对 `SECOND_PIPELINE_BASELINE.json`，实验后逐文件一致）。
- 测试专用私有源 `synthetic_private_test_label` 以 `TEST_ONLY_PRIVATE_SOURCE` 标记，仅用于数据传播验证；不构成 EvidenceGold/QueryGold，不计算任何医学检索指标。

## 2. 案例规模

| 类别 | 数量 | 说明 |
|---|---|---|
| 泄漏正例（M1–M4 / F1–F4 / R1–R4，12 模式） | 36（每模式 3 个受控变异） | 每个案例真实调用第二工程 BM25 流程；Source>0 且 Sink>0 |
| 普通 Clean | 30 | 不读取测试私有源，仅真实 Public 输入 |
| 困难 Clean | 30 | 代码/字段含 state/label/cache/backup 等词，取值全部来自 Public，Source=0 |
| **合计** | **96** | 全部真实执行，无 NOT_RUN |

## 3. 各检测器结果（冻结检测器，跨管线）

| detector | TP | FP | TN | FN | Precision | Recall | F1 | Specificity | BalAcc | MCC |
|---|---|---|---|---|---|---|---|---|---|---|
| keyword_static_baseline | 36 | 60 | 0 | 0 | 0.375 | 1.000 | 0.545 | 0.000 | 0.500 | 0.000 |
| ast_static_dataflow | 0 | 0 | 60 | 36 | N/A(null) | 0.000 | 0.000 | 1.000 | 0.500 | 0.000 |
| schema_guard | 12 | 0 | 60 | 24 | 1.000 | 0.333 | 0.500 | 1.000 | 0.667 | 0.488 |
| runtime_taint | 36 | 0 | 60 | 0 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| invariance | 11 | 0 | 60 | 25 | 1.000 | 0.306 | 0.468 | 1.000 | 0.653 | 0.464 |
| composite_audit | 36 | 0 | 60 | 0 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |

- **TP+FP=0 时 Precision 记 null（显示 N/A）**，未写成 1.0（对应 ast_static_dataflow）。
- 与主工程（Phase 5/6）行为对比：keyword 全正例命中+全 Clean 误报、ast 全漏报、schema 仅 M 类命中、runtime_taint 与 composite 全命中——**检测器特性在第二工程上保持一致**。

## 4. 泄漏影响分级（ACCESS_LEAK / BEHAVIORAL_LEAK）

| 等级 | 数量 | 说明 |
|---|---|---|
| NO_LEAK | 60 | 全部 Clean 案例：无真实源—汇路径 |
| ACCESS_LEAK | 25 | 存在真实源—汇路径，屏蔽测试私有值后 selected_doc_ids 不变（F1–F4 全部、R1–R4 全部、M3 部分） |
| BEHAVIORAL_LEAK | 11 | 存在真实源—汇路径，且屏蔽后候选集合/顺序/Top-K 变化（M1、M2、M4 全部、M3 部分） |

- 分级依据：unmask 与 mask 两轮真实选择的 `changed_set / changed_order / changed_doc_count / first_changed_rank`（`cross_pipeline_leak_effects.csv`）。
- 正例 36 = ACCESS 25 + BEHAVIORAL 11；不因 Top-K 未变化而降级为 Clean。

## 5. 运行开销（第二工程相同输入与 Top-K=5，12 案例，预热 3 次 + 正式 10 次）

| 条件 | 平均 (ms) | 相对基线 | 说明 |
|---|---|---|---|
| baseline_selection | 87.1 | — | 仅真实选择流程 |
| baseline_plus_runtime_monitor | 117.1 | +34.5% | +污点监控 |
| baseline_plus_schema | 121.8 | +39.9% | +schema 检查 |
| baseline_plus_invariance | 221.3 | +154.2% | 2×选择 |
| baseline_plus_composite_audit | 350.7 | +302.9% | 全部组件 |

- 离线 keyword/AST 扫描单独报告于 `cross_pipeline_offline_scan_runtime.csv`，不与在线选择时间混算。
- Median/P95 见 `cross_pipeline_runtime_overhead.csv`。

## 6. 失败模式（如实记录，未隐藏）

- **ast_static_dataflow 全部 36 个正例漏报（FN=36）**：与主工程行为一致（冻结检测器对「metadata/feature 句柄 → 读取 → 打分」跨文件模式的 AST 检测存在盲区）。跨管线实验未修改该检测器，按协议如实报告。
- **keyword_static_baseline 全部 60 个 Clean 误报（FP=60）**：困难 Clean 的字段名（state/cache/label/backup）与关键字重叠，普通 Clean 因适配器源码含 `private_store` 等字面量被误报；与主工程行为一致。
- **schema_guard 仅命中 M 类（TP=12/36）**：F/R 类注入位于特征/回退路径，不产生候选 schema 越界字段。
- **invariance 命中 11/36**：F/R 类注入经特征/回退路径后未改变 Top-K（ACCESS_LEAK）；M 类直接进候选打分，多数改变 Top-K（BEHAVIORAL_LEAK）。
- 适配失败：**0**（96/96 案例真实执行）。NOT_RUN 模式：**0**。

### 计数口径（一致性修复记录）
- `cross_pipeline_leak_effects.csv` 的 Source/Sink 计数取自 **unmasked 首次运行**（masked 重放不覆盖）；36 个泄漏案例均 Source>0 且 Sink>0，60 个 Clean 均 Source=0。
- `cross_pipeline_case_results.jsonl` 中 `runtime_taint` 行保留真实计数；`composite_audit` 行因 full_audit 内部多次 selection 覆盖 trace，Source/Sink 明确标记为 **N/A**（不承诺单一计数）。

## 6.1 独立 fixture-only 最小复现
- `fixture_dakd_v6/`：脱敏候选 fixture（fx_leak_m1 + fx_clean）+ 纯 Python adapter + 固化预期 `expected.json`；不含第二工程语料、不含私有 truth 明文。
- 全新解压后可独立运行两条命令（无需第二工程/无云端依赖）：
  - `python scripts/dakd_v6/run_tcm_sleep_cross_pipeline.py --fixture-only`
  - `pytest -q tests/dakd_v6_fixture`
- 说明：fixture 仅验证冻结检测器在脱敏 fixture 上的可复现性，**不等同于第二工程 Dense/Hybrid/Domain 管线验证**。

## 7. 可用于论文的事实清单（按章节）

### 第 4.5 节（审计方法/泄漏模式迁移）
- 冻结的 12 类模式（M1–M4、F1–F4、R1–R4）可直接映射到第二工程 BM25 检索 + Top-K 选择的候选元数据 / 特征 / 回退 / 过滤路径。
- 36 个受控泄漏案例中，**每一例均真实调用第二工程 BM25 检索流程**（Source>0 且 Sink>0），候选与分数来自第二工程原始实现。
- 私有值可经「候选 metadata → 打分」（M 类）、「特征构造 → 特征矩阵」（F 类）、「回退 / 过滤 → 选择」（R 类）进入证据选择。

### 第 5 节（检测器设计）
- runtime_taint 与 composite_audit 在第二工程上 Recall=1.0、Specificity=1.0（36 TP / 60 TN / 0 FP / 0 FN）。
- ast 静态数据流与 schema 白名单在第二工程上的召回受模式结构限制（见第 6 节）。
- keyword 基线在第二工程上重现高误报特性（60/60 Clean 误报），进一步说明其对字段名的敏感性。

### 第 6.6 节（跨管线/泛化性）
- 冻结检测器可在**不修改检测逻辑、不修改第二工程代码**的条件下，接入不同 RAG 代码结构并完成数据流检测。
- ACCESS_LEAK 25 / BEHAVIORAL_LEAK 11 / NO_LEAK 60 的分级基于真实选择的 mask 对比，可用于行为影响分析。
- 运行开销：composite 审计约 3 倍基线（350.7 ms vs 87.1 ms，12 案例均值），可作为部署开销引用。

### 结论
- 「在第二套中医睡眠 RAG 工程的受控跨管线实验中，冻结检测器对测试专用私有源进行了独立验证；该实验提供了初步跨工程工程证据；结果仍限于两套 Python RAG 工程和受控变异。」

## 8. 需要删除或替换的原论文表述（建议）

| 原表述（如存在） | 建议 |
|---|---|
| 任何暗示「检测器已验证于多种 RAG 系统」且未附第二工程数据的表述 | 替换为第 7 节「结论」中的保守表述，并引用本实验数据 |
| 把 keyword/ast 误报归因于单工程特性的表述 | 补充说明：误报特性在第二工程上复现（keyword 60/60 Clean FP；ast 36/36 FN） |
| 若原论文称「运行开销 = X」且未含审计开销 | 用第 5 节数据补充绝对/相对增量 |
| 若原论文含「泛化性（generalization）」宣称但无跨工程实验 | 用「初步跨工程工程证据」替代，不得宣称普适性 |

## 9. 不能写入论文的结论（禁止表述）

- 「证明 MedLeakAudit 具有普适性」——仅两套 Python RAG 工程 + 受控变异。
- 「可以检测所有未知泄漏」——ast/schema/invariance 在第二工程上存在漏检。
- 「完成真实临床系统验证」——第二工程为教学/研究工程，非临床系统；本实验只验证工程数据流，不评价中医内容质量。
- 「合成私有标签等同于人工 EvidenceGold」——`TEST_ONLY_PRIVATE_SOURCE` 仅为传播验证值。
- 「第二工程检索效果得到验证」——本实验不计算任何医学检索指标（NDCG/DemandCov 等）。

---

### 附：本目录文件索引（可复算证据）
- `FROZEN_DETECTOR_MANIFEST.json`：冻结检测器源码/配置 SHA256
- `SECOND_PIPELINE_BASELINE.json`：第二工程原文件 SHA256 基线（实验后比对一致）
- `CROSS_PIPELINE_AUDIT.md`：只读审计报告
- `CROSS_PIPELINE_SCENARIO_INDEX.csv`：96 案例清单
- `cross_pipeline_detection_summary.csv` / `cross_pipeline_confusion_matrix.csv`：各检测器指标
- `cross_pipeline_case_results.jsonl`：逐 case × detector 结果
- `cross_pipeline_failure_cases.csv`：FN/FP/执行失败
- `cross_pipeline_leak_effects.csv`：泄漏影响分级
- `cross_pipeline_runtime_overhead.csv` / `cross_pipeline_offline_scan_runtime.csv`：开销
- `pytest_report.txt`：新增 14 项 + 全量 93 项测试全部通过
