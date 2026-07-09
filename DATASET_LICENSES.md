# Licencias y Restricciones de Conjuntos de Datos

AegisBench no empaqueta ni distribuye directamente las muestras de los conjuntos de datos en su repositorio. Los datos se descargan en tiempo de ejecución directamente desde sus fuentes originales bajo demanda.

Es responsabilidad de cada usuario cumplir con los términos y licencias de cada conjunto de datos que utiliza para sus evaluaciones. A continuación se detallan las licencias y restricciones aplicables para los 5 datasets integrados:

---

## 1. JailbreakBench
- **Licencia:** MIT License.
- **Uso:** Permitido para investigación y aplicaciones comerciales.
- **Detalle:** Un repositorio de prompts de ataque (jailbreaks) de referencia comunes y actualizados de manera comunitaria.

## 2. AdvBench
- **Licencia:** MIT License.
- **Uso:** Permitido para investigación y desarrollo.
- **Detalle:** Contiene comportamientos peligrosos estándar de ataque directo desarrollados para la evaluación de alineación de LLMs.

## 3. HarmBench
- **Licencia:** MIT License.
- **Uso:** Libre para investigación y evaluación de seguridad.
- **Detalle:** Un benchmark estandarizado y robusto para la detección de comportamientos inseguros y jailbreaks de LLMs.

## 4. AgentHarm (UK AI Safety Institute)
- **Licencia:** AgentHarm Restricted License.
- **Restricciones Críticas de Uso:**
  > [!WARNING]
  > **Licencia Restringida de AgentHarm:**
  > Este conjunto de datos está diseñado específicamente para evaluar las capacidades y riesgos de los sistemas de agentes de IA en escenarios potencialmente dañinos. Está prohibido su uso para fines comerciales sin la debida autorización del UK AI Safety Institute, y su uso está limitado exclusivamente a fines de evaluación de seguridad e investigación ética de alineación.
- **Protección de la CLI:**
  Dado su carácter restringido y delicado, AegisBench bloquea la carga de `AgentHarm` por defecto. Debes aceptar explícitamente sus términos en la línea de comandos pasando la bandera obligatoria:
  `--accept-agentharm-terms`
  Si no se proporciona esta bandera, las muestras se omitirán y se registrarán como N/A.

## 5. XSTest
- **Licencia:** Creative Commons Attribution 4.0 International (CC-BY-4.0).
- **Uso:** Permitido tanto en entornos académicos como comerciales, siempre que se otorgue el crédito correspondiente a los autores originales.
- **Detalle:** Un benchmark de control de sobrebloqueos que evalúa el comportamiento del clasificador ante prompts benignos o de apariencia sensible pero totalmente seguros.

## 6. Policy Compliance
- **Licencia:** CC0 (Public Domain Dedication).
- **Uso:** Curated synthetic eval set, authored in-repo, CC0.
- **Detalle:** Un conjunto de evaluación sintético y curado localmente enfocado en el cumplimiento de políticas de agentes y gobierno empresarial. No es un benchmark público o externo.
