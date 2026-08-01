# 医疗RAG证据选择的无泄漏评测、部署差距与生成验证

**Leakage-Controlled Evaluation, Deployment Gaps, and Generation Validation for Medical RAG Evidence Selection**

本仓库提供投稿论文的最小结果复算与一致性验证材料，不包含完整语料、私有Gold、模型权重及全部端到端训练输入。

可直接复算：DemandCov、NDCG、B0-D3汇总、差距分解、配对统计、MMR-TFIDF、Top-K敏感性、泄漏NDCG补算。
只提供冻结汇总核验：ExactMax完整穷举、完整泄漏注入重新运行、BGE/RoBERTa模型重新训练、生成端人工评分。

---

## 论文

- 全文（Word）：`paper/医疗RAG证据选择的无泄漏评测、部署差距与生成验证.doc`
- 全文（PDF）：`paper/医疗RAG证据选择的无泄漏评测、部署差距与生成验证.pdf`

## 评估条件

| 条件 | 查询状态 | 证据状态 | 描述 |
|------|----------|----------|------|
| B0 | 无 | 无 | Reranker 基线 |
| D0 | Oracle | Oracle | 双 Oracle 参考（诊断上界，非可部署配置） |
| D1 | 预测 | Gold | QueryLoss = D0 - D1 |
| D2 | Gold | 预测 | EvidenceLoss = D0 - D2 |
| D3 | 预测 | 预测 | 完全可部署设置 |

## 关键发现

1. D0 比 B0 在 DemandCov@5 上提高 0.0229–0.0637（双 Oracle 参考空间存在）；
2. 低资源 D3 未形成稳定覆盖优势（差值 −0.0017 / 0.0033 / 0.0100，均不显著），并在部分划分降低 NDCG；
3. MMR-TFIDF（λ=0.6，formal_dev 冻结）与 B0、D3 的覆盖差异均不显著；external 上相对 B0 的 NDCG 差异显著（p_Holm=0.0066）；
4. K=3/5/7 下主要方法 DemandCov@K 排序方向一致（描述性）；
5. 生成端 60 题 240 条答案（4 条件）盲评经 Holm 校正后无显著差异；Answer relevance 存在天花板效应。

## 目录结构

- `paper/` — 论文 Word 与 PDF
- `paper_results/` — 冻结结果、MMR/Top-K 表与图、生成端统计、泄漏 NDCG 补算
  - `manifests/` 与 `per_query_minimal/`：三划分脱敏逐 qid 选择结果与 SHA256 清单
  - `revision_v5/tables/`：MMR/Top-K/关联/结构审计表（修正版）
  - `revision_v5/figures/`：论文图 2 与 Top-K/λ 曲线（黑白 300 dpi）
  - `revision_v5/reports/`：执行摘要、QC、叙事素材、段落草稿、Excel 汇总
  - `generation/`：生成端盲评与冻结统计（v2/v3）
- `scripts/revision_v5/`：MMR/Top-K 可复现脚本（在完整数据环境下运行）
- `src/` — 核心代码：指标计算、预测器、私有评估逻辑
- `docs/` — 实验协议、数据架构、泄漏威胁模型、补充实验说明
- `tests/` — 测试

## 快速开始（数据就绪环境）

```bash
pip install -r requirements.txt
python scripts/verify_manifest.py
python scripts/verify_gold_independence.py
python scripts/run_all.py
# MMR/Top-K（需完整 data/ 与预测缓存）
python scripts/revision_v5/run_all_revision_v5_fixed.py
```

## 数据许可与免责声明

发布文件使用完整 SHA256 清单验证；候选池数据来源于 webMedQA 和 cMedQA2，用户必须尊重原始数据集许可。
完整问题文本、候选文档、模型权重和私有 Gold 不公开。本平台仅用于 RAG 研究和评估，不提供疾病诊断、治疗或临床决策。

## 引用

```
@article{medsage2026,
  title={Leakage-Controlled Evaluation, Deployment Gaps, and Generation Validation for Medical RAG Evidence Selection},
  author={Shi Yuhan and Wang Qi},
  journal={Taiyuan University of Technology},
  year={2026}
}
```
