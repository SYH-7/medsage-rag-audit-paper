# Data Schema

## Public Data (inference inputs)
- qid: Query identifier
- doc_id: Document identifier
- title: Document title (public)
- content: Document content (public)
- reranker_score: Public reranker score

## Private Data (evaluation labels, NOT in deployable path)
- query_demands_6: Gold query demands (6-class)
- supported_states_15: Gold evidence states (15-class)
- relevance: Gold relevance label

## Per-query Result Fields
- qid_hash: Query identifier (SHA256 hashed for public sharing)
- method: Condition name (B0, D0, D1, D2, D3)
- dc: Demand coverage at k
- ndcg: NDCG at k
- selected: Selected document IDs (SHA256 hashed, prefix WMA_)
- query_state_source: 'none', 'gold', or 'predicted'
- evidence_state_source: 'none', 'gold', or 'predicted'
