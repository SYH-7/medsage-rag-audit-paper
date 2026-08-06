# Package Mapping

Mapping between the paper-support data items, their GitHub directories, and their Release attachments.

## 支撑数据[1]

**名称**：医疗RAG私有标签泄漏审计脱敏结果与复算材料

**GitHub 目录**：`results/01_main_audit/`

**Release 附件**：`medsage_dakd_authoring_bundle_v5_1_1_public.zip`

- 内容：主工程（v5.1.1，权威版本）泄漏审计脱敏结果与复算材料——576 个双人一致 EvidenceGold pair、36 个泄漏正例、60 个 Clean 负例；检测/定位/运行时/行为泄漏/未见结构/质量报告；代码、配置、脚本与测试。
- 公开附件由冻结原始归档经路径脱敏与公开目录重组生成（差异见 `docs/PUBLIC_ARCHIVE_DIFF_REPORT.md`）；原始归档仅本地保留。

## 支撑数据[2]

**名称**：医疗RAG证据选择B0—D3、MMR、Top-K敏感性与生成盲评脱敏结果

**GitHub 目录**：`results/02_deployment_diagnostics/`

**Release 附件**：`deployment_diagnostics_verified_results.zip`

- 内容：冻结发布版本核验结果（B0-D3 逐 qid/统计/汇总）、组件差距、MMR 基线、Top-K 敏感性、生成盲评、检索-生成关系、复现状态、来源核验（provenance）、配置与复算脚本。
- 仅取自 v2 允许名单；旧泄漏检测/消融/运行时/注入结果已按发布政策排除（见 ZIP 内 `README_DEPLOYMENT_DIAGNOSTICS.md`）。

## 支撑数据[3]

**名称**：MedLeakAudit中医睡眠RAG跨管线受控验证脱敏结果与最小复现材料

**GitHub 目录**：`results/03_cross_pipeline/`

**Release 附件**：`medsage_dakd_cross_pipeline_v6_public.zip`

- 内容：第二工程原生 BM25 + Top-K 跨管线受控验证——36 个泄漏正例、60 个 Clean 负例、ACCESS_LEAK=25 / BEHAVIORAL_LEAK=11；含合成 fixture、适配器、配置、脚本、测试与脱敏结果。
- 公开附件由冻结原始归档经路径脱敏与公开目录重组生成（差异见 `docs/PUBLIC_ARCHIVE_DIFF_REPORT.md`）；原始归档仅本地保留。

## Release 附件清单（release_assets/）

| 附件 | 说明 |
|---|---|
| `medsage_dakd_authoring_bundle_v5_1_1_public.zip` | 主工程审计公开脱敏包（由原始 v5.1.1 归档脱敏/重组生成） |
| `deployment_diagnostics_verified_results.zip` | 部署诊断支撑包（v2 允许名单） |
| `medsage_dakd_cross_pipeline_v6_public.zip` | 第二工程跨管线公开脱敏包（由原始 v6 归档脱敏/重组生成） |
| `SHA256SUMS.txt` | 三个附件的 SHA-256 清单（根目录与 release_assets/ 各一份，内容一致） |

原始归档（v5.1.1 / v6 / v2）**不作为 Release 附件公开**，仅保留在本地 `dist/` / `_incoming/`。
> 三个公开附件均内含 MIT `LICENSE`（版权：Shi Yuhan）与 `THIRD_PARTY_NOTICES.md`；MIT 仅覆盖原创代码，第三方数据/模型/依赖与派生记录不随代码 MIT 再授权。

