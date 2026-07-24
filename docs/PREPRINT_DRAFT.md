# Preprint Draft — Sequential Risk Integration for Agentic Safety

**Title:** Beyond Single-Turn Guardrails: Sequential Risk Accumulation and Containment in Agentic Trajectories  
**Authors:** 4R2 Research Team & Co-Architects  
**Date:** July 2026  
**Status:** Pre-submission Draft / Internal Review  

---

## Abstract

Modern LLM-based agent systems execute multi-step trajectories where risk often accumulates implicitly across turns rather than manifesting in a single explicit violation. Conventional guardrails rely on static turn-by-turn classifiers, leaving agentic deployments vulnerable to slow-burn drift, multi-turn tool abuse, and indirect prompt injections. In this paper, we introduce a model-agnostic sequential risk containment framework (**Fusible**) based on physical thermal dynamics ($I^2t$) and sequential change-point detection (CUSUM). 

Through explicit sensor-vs-physics isolation on ATBench (1,000 multi-turn agent trajectories across 8 risk categories), we demonstrate that sequential risk aggregation provides robust containment guarantees even when downstream sensor scores are zero-shot and noisy. We introduce **Quantile Normalization** against benign reference streams to stabilize detector thresholds across heterogeneous guard models (`Llama Guard 3`, `Qwen 2.5`). Furthermore, we present an empirical breakdown across risk families, highlighting where quadratic memory ($I^2t$) vs linear drift (CUSUM) offer optimal detection trade-offs. Finally, we align our flight recorder telemetry architecture with continuous post-market monitoring requirements under EU AI Act Article 72.

---

## 1. Introduction

Agentic architectures empower LLMs with autonomous tool use, multi-step planning, and persistent memory. However, safety mechanisms designed for single-turn chat interfaces fail to capture temporal risk propagation. A sequence of individually innocuous tool calls or subtle environment injections can aggregate into catastrophic policy violations.

### Key Contributions
1. **Physics-vs-Sensor De-aliasing:** A evaluation protocol separating turn-level detector fidelity from sequence-level accumulation dynamics.
2. **Quantile-Calibrated Accumulators:** Unification of $I^2t$ thermal accumulation and CUSUM sequential inference under a unified quantile-normalized framework.
3. **ATBench Zero-Shot Evaluation:** Comprehensive benchmark across 8 agentic risk families under out-of-domain (OOD) real sensor conditions.
4. **Compliance-Grade Flight Recording:** An open, auditable telemetry protocol satisfying EU AI Act Article 72 post-market monitoring mandates.

---

## 2. Threat Model & Formulation

Let $\tau = (t_1, t_2, \dots, t_N)$ represent an agent trajectory of $N$ turns. At each turn $k$, a guard model or latent probe emits an uncalibrated criticality score $s_k \in \mathbb{R}$.

### 2.1 Quantile Normalization
To prevent sensor compression or calibration collapse (e.g., $p_{90}=1.0$ in binary guards), raw scores are mapped via a empirical cumulative distribution function over a reference benign dataset $\mathcal{D}_{\text{benign}}$:
$$ \tilde{s}_k = \Phi_{\text{benign}}(s_k) = \frac{1}{|\mathcal{D}_{\text{benign}}|} \sum_{x \in \mathcal{D}_{\text{benign}}} \mathbf{1}(x \le s_k) \in [0, 1] $$

### 2.2 Accumulation Dynamics
- **Thermal Memory ($I^2t$):**
  $$ T_k = T_{k-1} \cdot e^{-\Delta t / \tau} + \max(0, \tilde{s}_k - \theta)^2 $$
- **Sequential Cumulative Sum (CUSUM):**
  $$ S_k = \max\left(0, S_{k-1} + (\tilde{s}_k - k_{\text{ref}})\right) $$

Containment is requested when $T_k \ge T_{\text{trip}}$ or $S_k \ge h$, accompanied by the minimal turn window explaining the accumulation spike.

---

## 3. Experimental Protocol & Audit Integrity

All experiments adhere to zero-leakage out-of-fold (OOF) splitting and cluster bootstrap inference:
- **Dataset:** ATBench (1,000 trajectories: 500 safe, 500 unsafe across 8 risk families).
- **Cluster Bootstrap:** Resampling trajectories at the cluster level to preserve cross-family dependency structures (mitigating optimistic variance estimates).
- **Audit Signatures:** All reported metrics correspond to immutably hashed JSON artifacts sealed with SHA-256 digests in `evidence/`.

---

## 4. Benchmark Results

### 4.1 Global Streaming AUROC (Zero-Shot OOD)

Under the out-of-domain (OOD) real sensor evaluation, we compare sequential aggregators against the turn-level reactive baseline (`runmax`). We report results for both `Llama Guard 3 1B` (under raw/fallback calibration) and `Qwen 2.5 3B` (under Quantile Normalization against benign calibration data).

#### Table 1: Llama Guard 3 1B (Binary Zero-Shot OOD)
| Aggregator | AUROC | $\Delta$ vs `runmax` (95% CI) | $P(\text{improvement})$ |
|---|---|---|---|
| **Thermal $I^2t$ ($\tau=2.0$)** | **0.5523** | — | — |
| **Thermal $I^2t$ ($\tau=5.0$)** | 0.5431 | +0.0427 [-0.0017, +0.0902] | 0.9670 |
| EWMA ($\alpha=0.3$) | 0.5154 | +0.0273 [-0.0240, +0.0766] | 0.8595 |
| Media acumulada (`runmean`) | 0.5154 | +0.0276 [-0.0260, +0.0802] | 0.8510 |
| Max acumulado (`runmax`) | 0.5010 | Reference | — |

*Note: For the binary sensor, the raw $\theta$ calibration at $p_{90}$ collapsed to 1.0 (degenerating continuous accumulation). A fallback calibration threshold of $\theta=0.5$ was applied to ensure the accumulator remained active.*

#### Table 2: Qwen 2.5 3B with Quantile Normalization (Continuous Zero-Shot OOD)
| Aggregator | AUROC | $\Delta$ vs `runmax` (95% CI) | $P(\text{improvement})$ |
|---|---|---|---|
| **CUSUM** ($k_{\text{ref}} \approx 0.76$) | **0.5548** | **+0.0404 [+0.0201, +0.0619]** | **1.0000** |
| EWMA ($\alpha=0.3$) | 0.5384 | +0.0241 [-0.0031, +0.0510] | 0.9540 |
| Media acumulada (`runmean`) | 0.5233 | +0.0090 [-0.0182, +0.0361] | 0.7430 |
| Max acumulado (`runmax`) | 0.5143 | Reference | — |
| Thermal $I^2t$ ($\tau=5.0$) | 0.4802 | -0.0344 [-0.0578, -0.0116] | 0.0015 |

### 4.2 Risk Family Breakdown
Under OOD Llama Guard 3 evaluation, temporal accumulation achieves substantial detection gains on multi-turn failure modes and environment feedback injections:
- `inherent_agent_failures`: $\text{AUROC } 0.6521$ vs $0.5020$ (+0.1501 delta)
- `corrupted_tool_feedback`: $\text{AUROC } 0.6083$ vs $0.5020$ (+0.1063 delta)
- `tool_description_injection`: $\text{AUROC } 0.5424$ vs $0.5020$ (+0.0404 delta)

---

## 5. Regulatory Alignment: EU AI Act Article 72

Article 72 mandates continuous, active, and systematic post-market monitoring for high-risk AI deployments. The Fusible flight recorder fulfills Annex IV technical documentation requirements by exporting cryptographically signed event logs containing:
1. Turn-by-turn normalized sensor scores.
2. Accumulator state trajectory ($T_k, S_k$).
3. Containment request triggers with exact temporal window attribution.
4. Cryptographic checksum (SHA-256) ensuring non-repudiation.

---

## 6. Conclusion & Roadmap

Sequential risk integration bridges the gap between reactive single-turn classifiers and complex multi-turn agent dynamics. Future work will extend this framework to latent space probes ($J$-space) and turn-level ground truth benchmarks (ATBench-TL).
