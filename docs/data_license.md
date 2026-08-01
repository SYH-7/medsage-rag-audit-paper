# Data License（数据许可说明）

## 候选池数据来源

候选池基于以下公开中文医疗数据集构建：

- **webMedQA**：中文在线医疗咨询数据集。
- **cMedQA2**：中文医疗问答数据集。

**MANUAL_REVIEW**：本仓库内的数据集出处描述（作者、会议/期刊、年份）与论文参考文献中的条目存在出入，无法在本仓库范围内核实精确许可条款。请在投稿前由作者依据数据集官方主页与论文参考文献核对后修正，**本仓库不自行编造许可或出处结论**。

## 使用约束

本仓库**不重新分发** webMedQA、cMedQA2 的完整原始文本、完整候选文档、私有 Gold 标签或模型权重。

> Users must obtain the original datasets from their official sources and comply with the original licenses. This repository does not redistribute the complete source texts.

## Ontology

15 类状态到 6 类医疗需求的操作性映射定义于 `configs/ontology.json`（任务型操作分类，非 ICD 或 SNOMED CT 临床本体）。
