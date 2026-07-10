# -*- coding: utf-8 -*-
"""Adaptador AegisBench -> 4R2 (RicciYazigi/4r2v6), modo response-governance.

Mapeo NO degenerado (verificado): usa los TRES campos que 4R2 necesita con
textos genuinamente distintos por muestra:
    policy   = sample.metadata["policy"]        (politica por muestra)
    request  = turno role="user"                 (peticion)
    response = turno role="assistant"            (respuesta del agente a evaluar)
Esto ejercita la Capa 1 (gate de coherencia NRIF) de forma legitima: C_NR y C_RI
quedan vivos (varian por muestra). C_IF queda en el neutro 0.5 porque AegisBench
no aporta senales de verificabilidad/grounding por muestra -> limite honesto del
harness, declarado, no una degeneracion.

NO ejercita CCA / snapshot termico / Mario-Luigi-Arbiter (requieren estado de
sesion entre turnos que AegisBench v1 no modela). Backend embedder = default del
SDK (HashingEmbedder, LEXICO, no semantico).

FOURR2_REPO_PATH debe apuntar a la raiz del repo 4r2v6.
"""
from __future__ import annotations
import os, sys, time, pathlib
from aegisbench.interfaces.v1 import (
    EvalResult, GovernanceDecision, Sample, ScenarioType, TargetSystem,
)

def _resolve() -> pathlib.Path:
    p = os.environ.get("FOURR2_REPO_PATH")
    if p:
        pp = pathlib.Path(p).expanduser().resolve()
        if (pp / "four_r2" / "guardrail.py").exists():
            return pp
    here = pathlib.Path(__file__).resolve()
    cand = here.parent.parent.parent / "4R2 repo maestro jul2026"
    if (cand / "four_r2" / "guardrail.py").exists():
        return cand
    raise ImportError("Define FOURR2_REPO_PATH -> raiz de 4r2v6 (four_r2/guardrail.py).")

_root = _resolve()
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))
from four_r2 import Guardrail  # noqa: E402

_GENERIC = ("Only assist with lawful, safe requests; decline requests or "
            "responses that violate the stated policy.")

class FourR2Adapter(TargetSystem):
    name = "4r2"
    def __init__(self, theta: float = 0.35, weights_profile: str = "balanced",
                 governance: bool = False, anticamo: bool = False,
                 embedder=None, nli_backend=None) -> None:
        """governance/anticamo/embedder/nli_backend: config del SDK 4R2 (opt-in).

        El scoring del benchmark NO cambia: esto solo configura el sistema
        bajo prueba (el adapter es la única costura entre ambos repos).
        """
        self._g = Guardrail(theta=theta, weights_profile=weights_profile,
                            embedder=embedder, governance_mode=governance,
                            governance_anticamo=anticamo,
                            governance_nli_backend=nli_backend)
        mode = ("anticamo" if anticamo else
                "governance" if governance else "layer1")
        emb = "semantic" if embedder is not None else "lexical"
        self.version = f"4r2-sdk-{mode}-{emb}"

    def evaluate(self, sample: Sample) -> EvalResult:
        t0 = time.perf_counter()
        policy = sample.metadata.get("policy") or _GENERIC
        req = next((m.content for m in sample.turns if m.role == "user"), "")
        resp = next((m.content for m in sample.turns if m.role == "assistant"), req)
        d = self._g.evaluate(policy=policy, request=req, response=resp)
        vmap = {"ALLOW": GovernanceDecision.ALLOW,
                "FLAG": GovernanceDecision.ESCALATE,
                "BLOCK": GovernanceDecision.BLOCK}
        decision = vmap.get(d.verdict, GovernanceDecision.BLOCK)
        # Contrato de AegisBench: 'confidence' = confianza EN LA DECISION tomada
        # (stats hace score=conf si BLOCK/ESCALATE, score=1-conf si ALLOW).
        # 4R2 produce un score de RIESGO (c_total, mayor = peor); el mapeo
        # correcto al contrato es: conf = riesgo si se bloquea/escala,
        # conf = 1 - riesgo si se permite. Asi el score continuo reconstruido
        # por el benchmark es exactamente c_total y el AUROC mide el ranking
        # real del sistema (antes, exponer c_total crudo violaba el contrato
        # y producia un AUROC artefactual).
        risk = max(0.0, min(1.0, float(d.c_total)))
        conf = risk if decision in (GovernanceDecision.BLOCK,
                                    GovernanceDecision.ESCALATE) else 1.0 - risk
        lat = (time.perf_counter() - t0) * 1000.0
        return EvalResult(sample_id=sample.sample_id, decision=decision,
                          confidence=conf, latency_ms=lat, adapter_name=self.name,
                          adapter_version=str(getattr(d, "package_version", self.version)),
                          raw_output=f"verdict={d.verdict} c_total={float(d.c_total):.4f} theta={d.theta}")

    def supports_scenario(self, st: ScenarioType) -> bool:
        return st in (ScenarioType.RESPONSE_GOVERNANCE, ScenarioType.SINGLE_TURN,
                      ScenarioType.AGENTIC_TOOL_USE, ScenarioType.OVER_REFUSAL_CONTROL)
