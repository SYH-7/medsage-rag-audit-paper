# MedLeakAudit：医疗RAG评测中的私有标签泄漏审计与部署诊断（公开支撑仓库）

**MedLeakAudit: Auditing Private-Label Leakage and Deployment Gaps in Medical RAG Evaluation**

> 本仓库仅提供论文对应的脱敏结果、统计复算脚本和一致性验证材料，不包含论文全文、原始医疗问答文本、完整候选文档、私有Gold标签或模型权重。

论文正在评审中，**暂不公开全文**。本仓库为论文"数据与代码可用性说明"中的最小结果复算与一致性验证材料。

## Release

- 当前发布：**v2.0.3-paper-support** (Default branch: `main`)
- Release 附件（`release_assets/`，git-ignored，仅作 Release 附件）：

| # | 附件 | 内容 |
|---|---|---|
| 1 | `medleakaudit_01_main_audit.zip` | 主工程受控泄漏审计公开脱敏包（内部冻结来源版本 v5.1.1） |
| 2 | `medleakaudit_02_deployment_diagnostics.zip` | 部署诊断核验结果（B0–D3 / MMR / Top-K 敏感性 / 生成盲评） |
| 3 | `medleakaudit_03_cross_pipeline_bm25_topk.zip` | 第二工程 BM25+Top-K 跨管线受控验证（内部冻结来源版本 v6） |
| 4 | `SHA256SUMS.txt` | 上述三个附件的 SHA-256 清单（根目录与 `release_assets/` 各一份，内容一致） |

- v5.1.1 与 v6 为**内部冻结来源版本**，仅在包内 README 与 provenance 文档中标注，不再作为公开附件文件名。
- 公开附件由冻结原始归档经路径脱敏与公开目录重组生成；核心结果、配置和统计值保持不变（差异见 `docs/PUBLIC_ARCHIVE_DIFF_REPORT.md`）。原始归档仅保留在本地 `dist/` / `_incoming/`。
- 历史 v1.x Release 与标签保持不变；本版本删除已被 `results/01|02|03` 取代的 v1.x 旧材料（`paper_results/` 等），旧文件仍由 Git 历史与旧标签保存。

## 公开范围

### 可以公开复算

- DemandCov 与 NDCG 聚合结果
- B0—D3 条件汇总和差距分解
- qid 级配对 Bootstrap 与 Holm 校正
- 泄漏检测/定位/运行时/行为泄漏/未见结构统计
- 生成端冻结统计与盲评
- MMR-TFIDF 代理基线、K=3/5/7 敏感性分析
- 跨管线（BM25+Top-K）受控验证与合成 fixture
- SHA-256 一致性检查

### 不公开

- 论文全文
- 原始医疗问题和回答
- 完整候选文档
- 私有 QueryGold / EvidenceGold
- 模型权重
- API 密钥
- 可识别个人身份的信息

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
5. 生成端盲评经 Holm 校正后无显著差异；Answer relevance 存在天花板效应。
6. 跨管线（第二工程 BM25+Top-K）受控验证：ACCESS_LEAK=25 / BEHAVIORAL_LEAK=11（36 正例 / 60 Clean 负例）。

## 目录结构

- `results/01_main_audit/` — 主工程受控泄漏审计（检测/定位/运行时/行为/未见结构/质量/来源核验）
- `results/02_deployment_diagnostics/` — B0–D3 / MMR / Top-K / 生成盲评核验结果（VERIFIED_FROM_RELEASE）
- `results/03_cross_pipeline/` — 第二工程 BM25+Top-K 跨管线受控验证
- `src/benchmark_v3/`、`src/cross_pipeline/` — 论文自研审计代码与跨管线适配器
- `configs/dakd_v2/`、`configs/dakd_v5/`、`configs/dakd_v6/` — 冻结配置
- `scripts/dakd_v2/`、`scripts/dakd_v5/`、`scripts/dakd_v6/` — 复算与构建脚本
- `fixtures/cross_pipeline/` — 跨管线合成 fixture（TEST_ONLY_PRIVATE_SOURCE）
- `tests/` — `dakd_v5/`、`dakd_v5_1/`、`dakd_v6/`、`dakd_v6_fixture/`、`conftest.py`
- `docs/` — 数据可用性、复现性、结果状态、隐私扫描、差异报告、许可证状态等
- `THIRD_PARTY_NOTICES.md` — 第三方材料声明；`LICENSE` — 完整 MIT 许可；`CITATION.cff`

## 测试

```bash
python -m pytest tests/ -q
```

- 45 passed / 6 skipped / 0 failed（v2.0.1 基线）；skipped 为 `REQUIRES_LOCAL_ORIGINAL_PROJECT`（需本地原始项目，未伪造）。

## License

The original source code in this repository is licensed under the MIT License.

Unless explicitly stated otherwise, the MIT License applies to the original implementation
contained in `src/`, `scripts/`, and `tests/`, as well as author-created configuration and utility
files.

Third-party datasets, pretrained models, software dependencies, derived records, and materials
originating from external sources remain subject to their respective licenses and terms. The MIT
License in this repository does not grant rights to raw medical text, private Gold labels, complete
candidate documents, model weights, or any third-party dataset content.

本仓库原创代码采用MIT许可证。第三方数据集、预训练模型、软件依赖及来源于外部资源的材料仍受其
各自许可条款约束，根目录MIT许可证不对原始医疗文本、私有Gold、完整候选文档、模型权重或第三方
数据内容进行再授权。

## 数据许可

候选池数据来源于 webMedQA（官方仓库 `hejunqing/webMedQA`）和 cMedQA2（官方仓库 `zhangsheng93/cMedQA2`）。本仓库**不分发**原始数据；具体许可见 `THIRD_PARTY_NOTICES.md`。

> Users must obtain the original datasets from their official sources and comply with the original licenses. This repository does not redistribute the complete source texts.

## 医疗免责声明

本平台仅用于 RAG 研究和评估，不提供疾病诊断、治疗或临床决策。

## 引用

```bibtex
@software{medsage_rag_audit_2026,
  author  = {Shi, Yuhan and Wang, Qi},
  title   = {MedLeakAudit: Auditing Private-Label Leakage and Deployment Gaps in Medical RAG Evaluation},
  year    = {2026},
  version = {2.0.3-paper-support},
  url     = {https://github.com/SYH-7/medsage-rag-audit-paper}
}
```

另见 `CITATION.cff`。
