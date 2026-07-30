# 医疗RAG证据选择的标签泄漏与部署差距

**Leakage Auditing and Oracle-to-Deployment Gap Analysis for Chinese Medical RAG**

本仓库验证投稿论文的冻结结果，是最小结果复算与一致性验证仓库，不包含完整语料、私有Gold、模型权重及全部端到端训练输入。

可直接复算：DemandCov、NDCG、B0-D3汇总、差距分解、配对统计。

只提供冻结汇总核验：ExactMax完整穷举、完整泄漏注入重新运行、BGE模型重新训练。

---

## 评估条件

| 条件 | 查询状态 | 证据状态 | 描述 |
|------|----------|----------|------|
| B0 | 无 | 无 | Reranker 基线 |
| D0 | Oracle | Oracle | 双 Oracle 参考（非严格上界） |
| D1 | 预测 | Gold | QueryLoss = D0 - D1（查询预测损失） |
| D2 | Gold | 预测 | EvidenceLoss = D0 - D2（证据预测损失） |
| D3 | 预测 | 预测 | 完全可部署设置 |

**ExactMaxCoverage**: 通过所有 k 组合的暴力搜索得到的严格组合上界。

## 差距定义

- OracleGain = D0 - B0
- QueryLoss = D0 - D1（查询预测损失）
- EvidenceLoss = D0 - D2（证据预测损失）
- DeploymentGap = D0 - D3
- DeployableGain = D3 - B0
- ExactGap = ExactMax - D0

## 关键发现

1. D0 比 B0 在 DemandCov@5 上提升 0.0229-0.0637
2. D3-B0 差异：-0.0017, 0.0033, 0.0100（均无统计显著性）
3. 证据支持预测是主要瓶颈
4. 证据侧泄漏是评估指标虚高的主要来源

## 快速开始

```bash
pip install -r requirements.txt
python scripts/verify_manifest.py
python scripts/verify_gold_independence.py
python scripts/run_all.py
```

## 目录结构

- `src/` — 核心代码：指标计算、预测器、私有评估逻辑
- `paper_results/` — 论文冻结结果、每查询粒度数据和清单
- `scripts/` — 验证脚本
- `tests/` — 测试
- `configs/` — 本体论配置
- `docs/` — 实验协议、数据架构、泄漏威胁模型等

## Random基线

Random选择不提供逐qid配对Bootstrap复算。
仅保留论文冻结均值，不提供逐qid追溯。

## 数据许可

本仓库发布文件使用完整SHA256清单验证。历史R7清单因采用截断哈希，仅作为来源记录，不作为完整文件身份验证。候选池数据来源于 webMedQA 和 cMedQA2 — 用户必须尊重原始数据集许可。

## 医疗免责声明

本平台仅用于 RAG 研究和评估，不提供疾病诊断、治疗或临床决策。

## 引用

```
@article{medsage2026,
  title={Leakage Auditing and Oracle-to-Deployment Gap Analysis for Chinese Medical RAG},
  year={2026}
}
```
