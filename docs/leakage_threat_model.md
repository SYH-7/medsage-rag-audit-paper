# Leakage Threat Model

## Leakage Types
1. **Metadata Leakage**: Private labels exposed through candidate metadata fields
2. **Fallback Leakage**: Missing predictions default to ground-truth labels
3. **Feature Leakage**: Labels used in feature construction for selection scoring
4. **Test-set Leakage**: Test labels used for threshold or weight selection

## Exposure Routes
- query-only: Query state labels enter the selection process
- evidence-only: Evidence state labels enter the selection process
- joint: Both query and evidence state labels enter the selection process

## Detection
Gold invariance test verifies that D3 selection is unchanged when:
1. Gold query states are removed
2. Gold evidence states are removed
3. Fake gold states are injected
