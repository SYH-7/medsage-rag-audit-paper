# MedLeakAudit: Auditing Private-Label Leakage and Deployment Gaps in Medical RAG Evaluation

**医疗RAG评测中的私有标签泄漏审计与部署诊断**（公开论文支撑仓库 / Public paper-support repository）

> This repository provides desensitized results, minimal runnable code, and reproduction material for the paper *MedLeakAudit: Auditing Private-Label Leakage and Deployment Gaps in Medical RAG Evaluation*. It does **not** contain the full paper text, raw medical questions, complete candidate documents, private Gold labels in plaintext, model weights, or API credentials.

Version `2.0.0-paper-support` · Branch `paper-support-v2`

---

## 1. 项目名称（Project name）

**MedLeakAudit: Auditing Private-Label Leakage and Deployment Gaps in Medical RAG Evaluation**

## 2. 研究目标（Research goals）

1. **私有标签泄漏审计**：医疗 RAG 评测中，私有证据标签（EvidenceGold）与私有查询（QueryGold）是否会泄漏进检索/证据选择阶段，从而虚增评测指标。
2. **部署差距诊断**：从 Oracle 评测条件（B0-D3）到完全可部署设置之间的查询侧/证据侧损失分解。
3. **方法敏感性**：排序聚合（MMR）与 Top-K 大小对结论稳健性的影响。
4. **生成验证**：证据选择质量是否传导到盲评下的答案生成。

## 3. Public / Private 契约

| 侧 | 包含 | 不包含 |
|---|---|---|
| **Public（本仓库）** | 脱敏审计结果、作者表、最小可运行代码、合成跨管线 fixture、配置、测试、SHA-256 清单 | 原始医疗文本、患者问题、完整候选文档、明文私有 Gold、标注者A/B原始表、向量库、模型权重、API 密钥/Token、`.env`、本机绝对路径、投稿论文全文 |
| **Private（不发布）** | 原始语料、候选池、明文 EvidenceGold/QueryGold、标注表、训练模型、两个原始工程 | — |

两个原始工程**不发布**。第二工程（中医睡眠 RAG）仅公开适配器、合成 fixture、配置、测试、哈希与脱敏结果。

## 4. Source—Transform—Sink 审计模型

- **Source**：私有值（EvidenceGold/QueryGold）的起源；
- **Transform**：将私有值传播进公开数据（特征、索引、候选库、提示上下文、排序状态）的操作；
- **Sink**：泄漏值被选择/排序/生成阶段消费的位置。

检测器沿此模型组织：静态关键词基线、AST 静态数据流、schema 防护、运行时污点、不变性分析；复合审计（`full_audit` / `composite_audit`）融合之。

## 5. 泄漏标签定义

- **NO_LEAK**：无私有值到达 sink。
- **ACCESS_LEAK**：私有值对选择阶段可访问，但未改变最终排序集合/顺序。
- **BEHAVIORAL_LEAK**：私有值可访问**且**改变检索/选择输出。

## 6. 主工程结果（v5.1.1 权威）

- 576 个双人一致 EvidenceGold pair；36 个泄漏正例、60 个 Clean 负例；
- 复合 `full_audit`：TP=36, FP=0, TN=60, FN=0（P/R/F1=1.0）；
- 主工程 **ACCESS_LEAK=28，BEHAVIORAL_LEAK=8**；
- 附定位、运行时、行为效应、未见结构泛化与 Gold 规范化报告。

## 7. 第二工程跨管线结果（v6 权威）

- 原生 **BM25 检索 + Top-K** 路径；
- 36 个泄漏正例、60 个 Clean 负例；**ACCESS_LEAK=25，BEHAVIORAL_LEAK=11**；
- 基线 87.1 ms / runtime 117.1 ms / composite 350.7 ms；
- 范围：仅构成"基于真实检索候选的 BM25 与 Top-K 跨管线受控验证"；**未**验证 Dense/Hybrid/领域增强/MMR。

## 8. B0—D3 部署诊断

B0（无预测基线）、D0（双 Oracle 参考，**非可部署配置**）、D1（查询预测+Gold 证据）、D2（Gold 查询+证据预测）、D3（完全可部署）。D0/D1/D2 为**诊断条件**，Oracle 参考收益不得解释为部署收益。

## 9. 三项支撑数据对应目录

| 支撑数据 | 名称 | GitHub 目录 | Release 附件 |
|---|---|---|---|
| [1] | 医疗RAG私有标签泄漏审计脱敏结果与复算材料 | `results/01_main_audit/` | `medsage_dakd_authoring_bundle_v5_1_1_public.zip` |
| [2] | 医疗RAG证据选择B0—D3、MMR、Top-K敏感性与生成盲评脱敏结果 | `results/02_deployment_diagnostics/` | `deployment_diagnostics_verified_results.zip` |
| [3] | MedLeakAudit中医睡眠RAG跨管线受控验证脱敏结果与最小复现材料 | `results/03_cross_pipeline/` | `medsage_dakd_cross_pipeline_v6_public.zip` |

详见 `docs/PACKAGE_MAPPING.md`。

## 10. 结果状态

- **REPRODUCED**：本包内复算/核验。
- **VERIFIED_FROM_RELEASE**：取自此前已核验的发布包并复核完整性。
- **REQUIRES_LOCAL_ORIGINAL_PROJECT**：端到端重跑及依赖原始工程的测试需本地原始工程，并需设置环境变量（`TCM_SLEEP_RAG_ROOT` 等）。

## 11. 测试方法

- 可独立运行：`tests/dakd_v5`、`tests/dakd_v5_1`、`tests/dakd_v6_fixture` 及仓库级核验测试。
- 需本地原工程：`tests/dakd_v6` 的 6 个用例（`REQUIRES_LOCAL_ORIGINAL_PROJECT`，不伪造通过）。
- 完整报告见 `docs/TEST_REPORT.md`（当前 52 passed / 6 skipped / 0 failed）。

## 12. 隐私范围

不发布：原始医疗文本、患者问题、完整候选文档、明文私有 Gold、标注者A/B原始表、向量库、模型权重、API 密钥/Token、`.env`、本机绝对路径、身份信息、投稿论文全文。扫描结果见 `docs/PRIVACY_SCAN_REPORT.md`。

## 13. 已知局限

- 只检测本研究实现的受控泄漏模式；**不**声称检测所有泄漏，**不**声称适用于任意语言、框架或所有 RAG 系统。
- 结论基于两个医疗 RAG 管线；**不**构成临床/医疗验证。
- 第二工程仅覆盖其原生 BM25 + Top-K 路径；Dense/Hybrid/领域增强/MMR **未**在此正式验证。
- 公开材料**不能**脱离本地原始工程独立复现全部端到端实验。

## 14. GitHub Release 附件

`release_assets/`（git-ignored）用于 GitHub Release 附件：

- `medsage_dakd_authoring_bundle_v5_1_1_public.zip`
- `deployment_diagnostics_verified_results.zip`
- `medsage_dakd_cross_pipeline_v6_public.zip`
- `SHA256SUMS.txt`

> **公开附件由冻结原始归档中的科研材料经路径脱敏和公开目录重组生成；核心结果、配置和统计值保持不变，差异见 `docs/PUBLIC_ARCHIVE_DIFF_REPORT.md`。**

原始归档（`medsage_dakd_authoring_bundle_v5_1_1.zip`、`medsage_dakd_cross_pipeline_v6.zip`、`medsage_dakd_authoring_bundle_v2.zip`）**不作为 Release 附件公开**（仅本地 `dist/`/`_incoming/` 保留）。

### 环境变量

运行跨管线/部署诊断脚本前请设置（`REQUIRES_LOCAL_ORIGINAL_PROJECT`）：

```
# Windows PowerShell
$env:TCM_SLEEP_RAG_ROOT = "$env:USERPROFILE\tcm_sleep_rag_full"   # 第二工程根目录
# Linux/macOS
export TCM_SLEEP_RAG_ROOT=~/tcm_sleep_rag_full
```

## 引用（Citation）

```bibtex
@software{medleakaudit_2026,
  author  = {Shi, Yuhan and Wang, Qi},
  title   = {MedLeakAudit: Auditing Private-Label Leakage and Deployment Gaps in Medical RAG Evaluation},
  year    = {2026},
  version = {2.0.0-paper-support}
}
```

See [CITATION.cff](CITATION.cff).

## 数据许可与免责

数据派生文件来源于 webMedQA（`hejunqing/webMedQA`）与 cMedQA2（`zhangsheng93/cMedQA2`）；用户须从官方来源获取原始数据集并遵守原始许可。本仓库不重分发完整源文本。本平台仅用于 RAG 研究与评测，不提供诊断、治疗或临床决策。许可证状态见 `docs/LICENSE_STATUS.md` 与 `docs/LICENSE_REVIEW_REPORT.md`。

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
