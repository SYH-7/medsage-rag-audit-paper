# 跨管线只读审计报告（tcm_sleep_rag_full）

生成时间：2026-08-04 14:29:48
工作目录：medsage_rag_full（主审计工程）；第二工程以只读方式接入。

## 1. 真实入口文件
| 环节 | 文件 | 实际调用函数 |
|---|---|---|
| 服务入口 | rag_service/api.py | `POST /rag/retrieve` → `retrieve()` → `get_retriever()` |
| BM25 检索入口 | rag_service/retriever_bm25.py | `BM25Retriever.retrieve(question, top_k)` |
| Dense 检索入口 | rag_service/retriever_dense.py | `DenseRetriever.retrieve(question, top_k)`（依赖 ChromaDB collection） |
| 融合入口 | rag_service/retriever_hybrid.py | `HybridRetriever.retrieve()`（Dense+BM25+RRF 融合） |
| 重排序入口 | rag_service/reranker.py | `MMRReranker.rerank(question, candidates, top_k)` |
| 领域增强入口 | rag_service/retriever_domain.py | `DomainEnhancedRetriever.retrieve()`（term/syndrome/category 加权 + MMR） |
| 纠错/回退路径 | rag_service/embedding_model.py | `allow_fallback` → hashing 离线后端（仅回退，不改业务数据） |
| Top-K 输出结构 | 各 retriever | `result["retrieved"]`：`{rank, chunk_id, doc_id, title, content, category, score, ...}` |
| 候选唯一标识 | 各 retriever | `chunk_id`（BM25 中同时含 `doc_id`） |

## 2. 真实选择路径
```
用户问题 → BM25/Dense 检索候选 → RRF 融合(HybridRetriever)
         → 领域增强打分(DomainEnhancedRetriever) → MMR 重排序(MMRReranker) → Top-K → retrieved
```

## 3. 候选结构
- `rank`（1-based）、`chunk_id`、`doc_id`、`content`、`category`、`source_dataset`
- 打分字段：`score`、`bm25_score`、`dense_score`、`rrf_score`、`final_score`（归一化范围约 [0,1]）
- selected_doc_ids 生成位置：各 `retrieve()` 内部 `retrieved[:top_k]` / `sorted(...)[:top_k]`

## 4. 依赖项
- Python 3.10（tcmrag 环境）/ 3.13（主工程环境均可跑 BM25 路径）
- jieba、rank-bm25（BM25）；chromadb、sentence-transformers（Dense/Hybrid/Domain）
- numpy、sklearn（hashing 回退）、fastapi/pydantic（服务层）
- 数据：data/processed/knowledge_chunks_v3_1905_ffr.jsonl（1905 chunks，含 BM25 缓存 pkl）
- 索引：chroma_db / chroma_db_v2_auth / chroma_db_v3_1500_ffr_bge（sqlite）
- 词典：data/dictionary/{sleep_terms,synonym_dict,syndrome_dict,category_rule}.json
- 模型：bge-small-zh（sentence-transformers，可离线缓存；allow_fallback 时用 hashing）

## 5. 数据可用性
| 数据 | 是否可用 | 说明 |
|---|---|---|
| knowledge_chunks_v3_1905_ffr.jsonl | 可用 | 1905 chunks，1.8 MB |
| BM25 缓存 | 可用 | knowledge_chunks_v3_1905_ffr.bm25_cache.pkl 存在 |
| dictionary | 可用 | 4 个词典文件齐全 |
| ChromaDB collection | 可用 | chroma_db_v3_1500_ffr_bge 等（需 tcmrag 环境） |
| eval_300.jsonl | 可用 | 300 个公开测试问题（仅用 question，不用 gold） |

## 6. 可插入测试专用私有源的路径
- 候选 metadata（M1-M4）：候选对象 `metadata` 字典
- 特征构造（F1-F4）：public_features 特征矩阵
- 回退/过滤（R1-R4）：缺失预测 / 异常分支 / 闭包默认参数 / 候选过滤
- 所有注入均通过受控私有读取接口（proxy.read_evidence_label），不读取第二工程业务数据

## 7. 无法执行的路径
| 路径 | 原因 |
|---|---|
| DomainEnhancedRetriever 完整链（Dense+MMR）在主工程环境运行 | 主工程 .venv 无 chromadb/sentence-transformers；可用 tcmrag 环境执行，但本实验以 BM25 真实流程为主 |
| 外部 API / 生成端 | 第二工程无云端 API 依赖；生成端不在本实验范围 |

## 8. 是否满足正式实验条件
- 真实入口与调用函数：已确认（BM25Retriever.retrieve 为真实检索 + Top-K 选择流程，主工程环境实测可运行，约 8ms）
- 候选与 selected_doc_ids 结构：已确认
- 离线、本地、无云端 API 条件：满足（BM25 路径完全离线）
- 测试专用私有源可受控插入：满足
- 结论：**满足正式实验条件**（BM25 真实路径）。Dense/Hybrid/Domain 路径需 tcmrag 环境，作为补充说明记录，不虚报。

真实调用验证：`{"status": "OK", "method": "bm25", "retrieved_count": 5, "latency_ms": 3, "sample_chunk_id": "C000245"}`
