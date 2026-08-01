# MMR 输入验证（fixed）

## 总体：**VALID**

| # | 检查项 | 状态 | 说明 | 致命 |
|---|---|---|---|---|
| 1 | pool_identical_b0_mmr | PASS | 重复 doc_id qid 数=0 | NO |
| 2 | reranker_score_valid | PASS | NaN/Inf 或缺失=0 | NO |
| 3 | embedding_row_alignment | PASS | 45282 vs 45282 | NO |
| 4 | embedding_coverage | WARN | 缺失比例={'formal_dev': 0.5173, 'formal_train': 0.542, 'internal_blind': 0.5987, 'cmedqa2_external': 0.854} → MMR-TFIDF 代理基线 | NO |
| 5 | no_gold_in_selection | PASS | mmr_select_tfidf 仅用 reranker_score + TF-IDF | YES |
