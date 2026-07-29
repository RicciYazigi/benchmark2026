# AegisBench v1.0 & fuse-ai 🛡️

**AegisBench** es un benchmark de código abierto, reproducible e independiente para la evaluación y robustez de **Sistemas de Gobernanza de IA en Tiempo de Ejecución (Runtime Governance Systems)**.

Acompaña a **`fuse-ai`** (`fusible`), la **capa de contención temporal sensor-agnóstica** para sistemas agénticos.

> [!NOTE]
> **Tesis del Proyecto (2026-07-27):**
> *El riesgo se acumula a lo largo de una trayectoria. Un fusible con memoria (CUSUM, $I^2t$, EWMA) lo detecta donde un detector reactivo por turno es ciego.*

---

## 🌟 Características Clave

- **Capa de Contención Temporal (`fuse-ai` / `fusible`):** Convierte señales de riesgo por turno de cualquier detector (Llama Guard, probes latentes, webhooks) en decisiones de contención acumulativa con memoria y flight recorder auditable (EU AI Act Art. 72).
- **Independencia Absoluta:** AegisBench evalúa a los sistemas como cajas negras a través de la interfaz `interfaces/v1.py`.
- **Rigor Estadístico:** ASR y ORR con intervalos de confianza del 95% mediante simulación bootstrap determinista (N=10,000).
- **Cobertura de Datasets:** Hash SHA256 para JailbreakBench, AdvBench, HarmBench, AgentHarm y XSTest.
- **Visualización Premium:** Reportes automáticos en JSON, CSV, Markdown y HTML interactivo con Chart.js.
- **Salvaguarda Anti-Gaming:** Split held-out del 20% mediante hash MD5 determinista.


---

## 🚀 Instalación Rápida

AegisBench requiere Python >= 3.10.

```bash
# Clonar el repositorio
git clone https://github.com/usuario/aegisbench.git
cd aegisbench

# Instalación editable de desarrollo local
python -m pip install -e .[dev]
```

### Ejecutar con Docker

Puedes construir y ejecutar el entorno reproducible usando Docker:

```bash
# Construir la imagen
docker build -t aegisbench -f docker/Dockerfile .

# Ejecutar el autodiagnóstico
docker run --rm aegisbench doctor
```

---

## 💻 Guía de Uso de la CLI

AegisBench expone varios comandos intuitivos a través del comando `aegisbench`:

### 1. Autodiagnóstico e Integridad
Comprueba que el entorno de ejecución esté bien configurado y realiza un test de consistencia y determinismo:
```bash
aegisbench doctor
```

### 2. Validar un Adaptador Personalizado
Antes de correr pruebas largas, asegúrate de que tu adaptador cumple al 100% con la especificación de interfaces de AegisBench:
```bash
aegisbench validate-adapter --adapter dummy
```

### 3. Listar Conjuntos de Datos y Ataques
Visualiza las licencias, hashes y restricciones de uso:
```bash
aegisbench list-datasets
aegisbench list-attacks
```

### 4. Ejecutar la Suite de Evaluación
Ejecuta la evaluación completa para un adaptador. 

```bash
# Ejecutar una prueba rápida contra el dataset de falsos positivos XSTest
aegisbench run --adapter dummy --dataset xstest -n 10 --concurrency 4

# Ejecutar contra todos los datasets (excluyendo AgentHarm a menos que se acepten los términos)
aegisbench run --adapter dummy --dataset all --concurrency 16

# Ejecutar con el dataset restringido AgentHarm aceptando sus términos
aegisbench run --adapter dummy --dataset agentharm --accept-agentharm-terms --concurrency 4

# Evaluar robustez aplicando un ataque de ofuscación de Base64
aegisbench run --adapter dummy --dataset jailbreakbench -n 50 --attack base64 --concurrency 4
```

---

## 📊 Formatos de Reportes Generados

Al finalizar una ejecución, AegisBench escribe 4 archivos en el directorio de salida configurado (por defecto `./reports`):
- `report.json`: Estructura completa y canónica de datos para su almacenamiento en bases de datos o análisis de CI.
- `report.csv`: Detalle tabular fila por fila indicando la decisión tomada y si la evaluación fue correcta.
- `report.md`: Resumen legible en formato Markdown ideal para comentarios de pull requests.
- `report.html`: Dashboard estático premium autohospedado con gráficos interactivos que muestra el ASR, ORR, latencia promedio y distribución de decisiones.

---

## 🛠️ Contribuir y Desarrollar

AegisBench utiliza `pytest` para la suite de pruebas unitarias y de integración, garantizando una cobertura mínima del 85%:

```bash
# Ejecutar la suite de pruebas
python -m pytest --cov=src/aegisbench --cov-report=term-missing

# Ejecutar análisis de tipado estático
python -m mypy --strict src/aegisbench/core src/aegisbench/interfaces

# Formatear y verificar linter
python -m ruff check .
```

---

## 📄 Licencia

El código fuente de AegisBench se distribuye bajo la licencia **Apache 2.0**. Consulte el archivo [DATASET_LICENSES.md](DATASET_LICENSES.md) para conocer las licencias correspondientes a cada conjunto de datos de referencia (las cuales se descargan dinámicamente y no están integradas en este repositorio).
