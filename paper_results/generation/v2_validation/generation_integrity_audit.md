# Generation Integrity Audit

**API call state: API_CALL_COMPLETE_NO_FAILURE**

- [PASS] full_file_exists: present
- [PASS] full_line_count: 240
- [PASS] answer_id_unique: unique=240 total=240
- [PASS] question_nonempty: 240/240
- [PASS] answer_nonempty: empty=0
- [PASS] no_placeholder_answer: placeholder_like=0 
- [PASS] condition_valid: dist={'B0': 60, 'D0': 60, 'D3_TFIDF': 60, 'D3_ROBERTA': 60}
- [PASS] condition_counts_60: dist={'B0': 60, 'D0': 60, 'D3_TFIDF': 60, 'D3_ROBERTA': 60}
- [FAIL] model_field_consistent: models={''}
- [FAIL] doc_ids_field: rows_with_doc_ids=0/240
- [PASS] no_error_field: with_error=0
- [PASS] prompt_no_gold_label: prompts_with_markers_in_instruction=0
- [PASS] answer_length_sane: min=65 max=705
- [PASS] blinded_file_exists: present
- [PASS] blinded_line_count: 240
- [PASS] key_file_exists: present
- [PASS] key_entry_count: 240
- [PASS] id_sets_match: full=240 blind=240 key=240
- [PASS] blinded_no_condition_field: rows_with_markers=0
- [PASS] blinded_answer_matches_full: blinded has no answer field
- [PASS] key_unique_mapping: entries_with_condition_and_docids=240/240
- [PASS] api_status_generated_flag: generated=True
- [PASS] api_call_state: API_CALL_COMPLETE_NO_FAILURE

## API / generation facts (from files)
- requested_count=240
- successful_count=240
- failed_count=0
- empty_answer_count=0
- retry_count=0
- model_name=deepseek-chat
- base_url_domain=https://api.deepseek.com/v1
- generation_date=2026-07-31
- temperature=0.0
- max_output_tokens=800

## Note on the report contradiction
- The old FINAL_VALIDATION_REPORT.md section 8 hardcoded '未调用 API（配置缺失）' regardless of the actual generation state. generation_status.json now records generated=True, n_generated=240, api_failures=0.
