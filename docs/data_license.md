# Data License（数据来源与使用条件）

## 数据来源与使用条件

- **webMedQA**：官方仓库为 `hejunqing/webMedQA`，对应 He、Fu 和 Tu 于 2019 年发表的
  *Applying deep matching networks to Chinese medical question answering: A study and a dataset*
  （DOI: `10.1186/s12911-019-0761-8`）。官方仓库标示为 Apache-2.0 License。

- **cMedQA2**：官方仓库为 `zhangsheng93/cMedQA2`，对应 Zhang 等于 2018 年发表的
  *Multi-Scale Attentive Interaction Networks for Chinese Medical Question Answer Selection*
  （DOI: `10.1109/ACCESS.2018.2883637`）。官方 README 说明该数据集仅用于非商业研究；
  仓库代码许可证标示为 GPL-3.0。

本仓库不重新分发上述数据集的完整问题、答案或候选文档。复现者应从官方来源取得数据，
并遵守官方仓库及数据集声明的使用条件。

## Ontology

15 类状态到 6 类医疗需求的操作性映射定义于 `configs/ontology.json`
（任务型操作分类，非 ICD 或 SNOMED CT 临床本体）。
