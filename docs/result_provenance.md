# Result Provenance（结果来源说明）

本仓库为论文的**公开复算材料**。以下实验结果的原始冻结来源位于内部项目（不公开），公开仓库中仅提供脱敏后的可复算材料；**不得将"内部冻结来源"列中的路径当作本仓库可访问路径**。

| 实验内容 | 内部冻结来源 | 公开复算材料 |
|---|---|---|
| B0—D3 主结果 | 内部冻结目录，不公开 | `paper_results/manifests/main_results.csv` |
| 差距分解 | 内部冻结目录，不公开 | `paper_results/manifests/gap_decomposition.csv` |
| 泄漏注入 | 内部冻结目录，不公开 | `paper_results/manifests/leakage_per_seed.csv` |
| 生成统计 | 内部冻结目录，不公开 | `paper_results/generation/v3_frozen/` |
| MMR 与 Top-K | revision_v5 内部执行结果 | `paper_results/revision_v5/` |
| 逐 qid 材料 | 脱敏导出 | `paper_results/per_query_minimal/` |

## 一致性验证

- `release_manifest_sha256_v11.csv` 包含全部公开文件的完整 64 位 SHA256 哈希；
- 历史 `bundle_manifest.csv` 使用截断哈希，仅作为来源记录，不作为完整文件身份验证；
- `endpoint_final_validation.json` 验证 6 个泄漏端点在逐 qid Top-5 层面的闭合性；
- `tests/` 提供清单、条件与隐私检查的自动化测试。
