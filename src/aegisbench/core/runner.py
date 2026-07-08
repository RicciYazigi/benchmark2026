# -*- coding: utf-8 -*-
"""
Orquestador de ejecución (Runner) para AegisBench.
Maneja la ejecución de adaptadores sobre muestras de datasets.
"""

from typing import List, Optional

from aegisbench.interfaces.v1 import EvalResult, Sample, TargetSystem


class Runner:
    """
    Orquesta la evaluación de un TargetSystem contra un conjunto de Samples.
    """

    def __init__(
        self,
        adapter: TargetSystem,
        samples: List[Sample],
        concurrency: int = 1,
        seed: Optional[int] = None,
    ):
        self.adapter = adapter
        self.samples = samples
        self.concurrency = concurrency
        self.seed = seed

    def run(self) -> List[EvalResult]:
        """
        Ejecuta la evaluación para todas las muestras configuradas.
        """
        import concurrent.futures

        results: List[EvalResult] = []

        # Filtrar muestras soportadas por el adaptador
        valid_samples = [
            s for s in self.samples if self.adapter.supports_scenario(s.scenario_type)
        ]

        if not valid_samples:
            return results

        def eval_single(sample: Sample) -> Optional[EvalResult]:
            try:
                return self.adapter.evaluate(sample)
            except Exception as e:
                # En v1 registramos el fallo
                import logging

                logging.getLogger(__name__).error(
                    f"Error evaluando muestra {sample.sample_id}: {e}"
                )
                return None

        # Ejecución secuencial o concurrente
        if self.concurrency <= 1:
            for sample in valid_samples:
                res = eval_single(sample)
                if res:
                    results.append(res)
        else:
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=self.concurrency
            ) as executor:
                futures = [executor.submit(eval_single, s) for s in valid_samples]
                for future in concurrent.futures.as_completed(futures):
                    res = future.result()
                    if res:
                        results.append(res)

        return results
