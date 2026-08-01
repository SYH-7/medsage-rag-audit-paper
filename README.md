# 医疗RAG证据选择的无泄漏评测、部署差距与生成验证（补充材料仓库）

**Leakage-Controlled Evaluation, Deployment Gaps, and Generation Validation for Medical RAG Evidence Selection**

> 本仓库仅提供论文对应的脱敏结果、统计复算脚本和一致性验证材料，不包含论文全文、原始医疗问答文本、完整候选文档、私有Gold标签或模型权重。

论文正在评审中，**暂不公开全文**。本仓库为论文"数据与代码可用性说明"中的最小结果复算与一致性验证材料。

## 公开范围

### 可以公开复算

- DemandCov 与 NDCG 聚合结果
- B0—D3 条件汇总和差距分解
- qid 级配对 Bootstrap 与 Holm 校正
- 泄漏注入逐 seed 统计
- 生成端冻结统计与 Friedman 检验
- MMR-TFIDF 代理基线
- K=3、5、7 敏感性分析
- 脱敏逐 qid 选择结果
- SHA256 一致性检查

### 不公开

- 论文全文
- 原始医疗问题和回答
- 完整候选文档
- 私有 Gold 标签
- 模型权重
- API 密钥
- 可识别个人身份的信息

## Release

- 固定 Release：https://github.com/SYH-7/medsage-rag-audit-paper/releases/tag/v1.1-paper-supplement
- 规范化更新补丁版本：https://github.com/SYH-7/medsage-rag-audit-paper/releases/tag/v1.1.1-paper-supplement

## 评估条件

| 条件 | 查询状态 | 证据状态 | 描述 |
|------|----------|----------|------|
| B0 | 无 | 无 | Reranker 基线 |
| D0 | Oracle | Oracle | 双 Oracle 参考（诊断上界，非可部署配置） |
| D1 | 预测 | Gold | QueryLoss = D0 - D1 |
| D2 | Gold | 预测 | EvidenceLoss = D0 - D2 |
| D3 | 预测 | 预测 | 完全可部署设置 |

## 差距定义

- OracleGain = D0 - B0
- QueryLoss = D0 - D1
- EvidenceLoss = D0 - D2
- DeploymentGap = D0 - D3
- DeployableGain = D3 - B0
- ExactGap = ExactMax - D0

## 关键发现

1. D0 比 B0 在 DemandCov@5 上提高 0.0229–0.0637（双 Oracle 参考空间存在）；
2. 低资源 D3 未形成稳定覆盖优势（−0.0017 / 0.0033 / 0.0100，均不显著），并在部分划分降低 NDCG；
3. MMR-TFIDF（λ=0.6，formal_dev 冻结）与 B0、D3 的覆盖差异均不显著；external 上相对 B0 的 NDCG 差异显著（p_Holm=0.0066）；
4. K=3/5/7 下主要方法 DemandCov@K 排序方向一致（描述性）；
5. 生成端 60 题 240 条答案（4 条件）盲评经 Holm 校正后无显著差异；Answer relevance 存在天花板效应。

## 目录结构

- `paper_results/manifests/` — 冻结汇总、泄漏逐 seed、SHA256 清单
- `paper_results/per_query_minimal/` — 三划分脱敏逐 qid 选择结果（无原始文本）
- `paper_results/generation/` — 生成端盲评与冻结统计（v2/v3）
- `paper_results/revision_v5/tables/` — MMR/Top-K/关联/结构审计表（修正版）
- `paper_results/revision_v5/figures/` — 论文图 2 与 Top-K/λ 曲线（黑白 300 dpi）
- `paper_results/revision_v5/reports/` — 执行摘要、QC、叙事素材、段落草稿、Excel 汇总
- `scripts/revision_v5/` — MMR/Top-K 可复现脚本（在完整数据环境下运行）
- `scripts/` — 清单与 Gold 独立性验证脚本
- `src/` — 核心代码：指标计算、预测器、私有评估逻辑
- `docs/` — 实验协议、数据架构、泄漏威胁模型、补充实验说明
- `tests/` — 一致性、条件与隐私检查测试

## 快速开始（数据就绪环境）

```bash
pip install -r requirements.txt
python scripts/verify_manifest.py
python scripts/verify_gold_independence.py
python scripts/run_all.py
```

MMR/Top-K 复算需完整 data/ 与预测缓存（受许可限制不随仓库分发），脚本见 `scripts/revision_v5/`。

## 数据许可

本仓库发布文件使用完整 SHA256 清单验证（`paper_results/manifests/release_manifest_sha256.csv`，由 `scripts/make_manifest.py` 从 git 索引生成、`scripts/verify_manifest.py` 只读验证）。候选池数据来源于 webMedQA（官方仓库 `hejunqing/webMedQA`，Apache-2.0）和 cMedQA2（官方仓库 `zhangsheng93/cMedQA2`，数据集仅供非商业研究）。

> Users must obtain the original datasets from their official sources and comply with the original licenses. This repository does not redistribute the complete source texts.

## 医疗免责声明

本平台仅用于 RAG 研究和评估，不提供疾病诊断、治疗或临床决策。

## 引用

```bibtex
@software{medsage_rag_audit_2026,
  author  = {Shi, Yuhan and Wang, Qi},
  title   = {Medical RAG Leakage-Controlled Evaluation Supplement},
  year    = {2026},
  version = {v1.1.1-paper-supplement},
  url     = {https://github.com/SYH-7/medsage-rag-audit-paper}
}
```
