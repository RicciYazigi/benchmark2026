# Specification — J-Space Latent Probe Experiment (Phase 4)

**Document ID:** SPEC-20260720-JSPACE  
**Status:** Design & Protocol Draft  

---

## 1. Goal

Evaluate whether extracting internal hidden activation representations (**$J$-space**) from open-weights LLM backbones (e.g., `Llama-3.2-1B`, `Qwen2.5-1.5B`) provides a cleaner, lower-noise turn-level risk signal than textual surface-level guard models, thereby maximizing the efficiency of the `fusible` temporal accumulator.

---

## 2. Hypothesis

**Falsable Hypothesis (H_J0):** Linear risk probes trained on mean-pooled hidden activations of intermediate transformer layers achieve higher turn-level signal-to-noise ratio (SNR) on indirect tool environment injections (`corrupted_tool_feedback`, `tool_description_injection`) than surface zero-shot text guards (28.8% vs 34.6% baseline random rate), leading to statistically significant AUROC improvements under $I^2t$ / CUSUM accumulation ($\Delta > 0.05$, 95% CI excluding 0).

---

## 3. Architecture & Extraction Protocol

### 3.1 Representation Extraction
For each turn $k$ in an ATBench trajectory:
1. Pass the turn prompt/response text through the open model backbones (`Llama-3.2-1B-Instruct` or `Qwen2.5-1.5B-Instruct`).
2. Extract hidden state activations from layer $L_{mid} = \lfloor \frac{3}{4} L_{\text{total}} \rfloor$ (e.g., layer 12 of 16 for 1B models).
3. Compute mean token pooling over non-padding tokens:
   $$ v_k = \frac{1}{M} \sum_{i=1}^M h_{i}^{(L_{\text{mid}})} \in \mathbb{R}^{d_{\text{model}}} $$

### 3.2 Probe Training (Zero-Fugue 5-Fold OOF)
- Train a regularized Logistic Regression / Ridge probe $w \in \mathbb{R}^{d_{\text{model}}}$ on $v_k$.
- Protocol: Trajectory-level 5-Fold Out-Of-Fold (OOF). No turn from the same trajectory is ever split across train and validation folds.
- Inferred raw score: $s_k = \sigma(w^T v_k)$.

### 3.3 Accumulator Pipeline
1. Raw probe scores $s_k$ are passed into `QuantileNormalizer` fitted on benign calibration turns ($\mathcal{D}_{\text{cal}}$).
2. Normalized scores $\tilde{s}_k$ feed into the `fusible` accumulator ($I^2t$ and CUSUM).
3. Evaluate streaming global AUROC and 8-family breakdown with cluster bootstrap.

---

## 4. Execution Requirements & Hardware

- **Hardware:** NVIDIA GPU (≥8GB VRAM) or Apple Silicon / CPU with 16GB RAM.
- **Dependencies:** `torch`, `transformers`, `scikit-learn`, `fusible`.
- **Script Location (Target):** `scripts/eval_jspace_probe.py`.

---

## 5. Decision Matrix

| Result | Outcome | Next Action |
|---|---|---|
| Probe + Fusible AUROC > 0.70 (OOD) | **Strong Success** | Incorporate $J$-space probe adapter into `fusible.sensors.latent` |
| Probe + Fusible AUROC ~0.55-0.60 | **Moderate Improvement** | Document as secondary sensor option in Preprint Section 6 |
| Probe AUROC ≤ Surface Zero-Shot | **Negative Result** | Confirm surface textual guards remain the primary deployment target |
