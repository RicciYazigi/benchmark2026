#!/usr/bin/env python3
"""Gate de cadena de evidencia — AegisBench / Benchmark2026.

Cada artefacto sellado `X.json` (o `X.jsonl`) debe tener su sidecar `X.sha256`
con el SHA-256 de los BYTES del archivo. Este script lo verifica y sale con
codigo 1 si algo no cuadra.

Por que existe (auditoria 2026-07-30):
    Durante ~3 semanas, 10 de 17 artefactos sellados no coincidian con su
    sidecar. La causa era `Path.write_text()` en Windows traduciendo LF -> CRLF
    DESPUES de calcular el hash sobre el payload en memoria (LF). El contenido
    nunca estuvo corrupto, pero la propiedad que este proyecto vende
    -- "cualquiera reproduce la evidencia bit a bit" -- estaba rota, y no habia
    ningun gate que lo detectara. Ahora lo hay.

    El fix estructural son las dos cosas juntas:
      1. `.gitattributes` con `evidence/** -text` (git no toca los bytes).
      2. Escritura binaria explicita en los scripts de eval (`sellar()` abajo).

Uso:
    python scripts/verify_evidence_seals.py            # verifica
    python scripts/verify_evidence_seals.py --list     # lista sin fallar
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
EVIDENCE = HERE / "evidence"


def sellar(destino: Path, payload: str) -> str:
    """Escribe `payload` y su sidecar .sha256 de forma consistente.

    Usar SIEMPRE esta funcion en los scripts de eval en vez de
    `write_text` + `hashlib` por separado: escribe en binario con LF explicito,
    de modo que el hash del sidecar es el hash de los bytes en disco en
    cualquier sistema operativo.
    """
    data = payload.encode("utf-8")
    destino.write_bytes(data)
    sha = hashlib.sha256(data).hexdigest()
    destino.with_suffix(destino.suffix + ".sha256").write_bytes(
        (sha + "\n").encode("utf-8")
    )
    return sha


def _target_for(sidecar: Path) -> Path | None:
    base = sidecar.name[: -len(".sha256")]
    for cand in (
        sidecar.parent / base,
        sidecar.parent / f"{base}.json",
        sidecar.parent / f"{base}.jsonl",
    ):
        if cand.exists() and cand != sidecar:
            return cand
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--evidence-dir", type=Path, default=EVIDENCE)
    ap.add_argument(
        "--list", action="store_true", help="Solo listar el estado; no fallar"
    )
    args = ap.parse_args()

    sidecars = sorted(args.evidence_dir.glob("**/*.sha256"))
    if not sidecars:
        print(f"ERROR: no hay sidecars .sha256 en {args.evidence_dir}")
        return 1

    ok, bad, orphan = 0, [], []
    for s in sidecars:
        target = _target_for(s)
        if target is None:
            orphan.append(s.name)
            continue
        want = s.read_text(encoding="utf-8").split()[0].strip()
        got = hashlib.sha256(target.read_bytes()).hexdigest()
        if want == got:
            ok += 1
        else:
            bad.append((target.name, want, got))

    # Artefactos sin sellar: no rompen la cadena, pero "no existen para la
    # auditoria" y conviene verlos.
    sealed = {_target_for(s).name for s in sidecars if _target_for(s)}
    unsealed = sorted(
        p.name
        for p in args.evidence_dir.glob("*")
        if p.is_file() and p.suffix in {".json", ".jsonl"} and p.name not in sealed
    )

    print(
        f"Cadena de evidencia: {ok} OK · {len(bad)} MISMATCH · "
        f"{len(orphan)} sidecar huerfano · {len(unsealed)} sin sellar"
    )
    for name, want, got in bad:
        print(f"  [MISMATCH] {name}\n      esperado {want}\n      real     {got}")
    for name in orphan:
        print(f"  [HUERFANO] {name} (sidecar sin artefacto)")
    for name in unsealed:
        print(f"  [SIN SELLAR] {name}")

    if args.list:
        return 0
    if bad or orphan:
        print(
            "\nFALLO: la cadena de evidencia no reproduce. "
            "Revisa .gitattributes y usa sellar() al escribir artefactos."
        )
        return 1
    print("\nOK: todos los artefactos sellados reproducen su hash.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
