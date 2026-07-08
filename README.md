# AegisBench v1.0 🛡️

AegisBench es un benchmark de código abierto, reproducible e independiente para la evaluación y robustez de **Sistemas de Gobernanza de IA en Tiempo de Ejecución (Runtime Governance Systems)**. 

Estos sistemas monitorean las decisiones y conversaciones de los LLMs/agentes en tiempo real y devuelven una decisión de control: permitir (`ALLOW`), bloquear (`BLOCK`) o escalar a revisión humana (`ESCALATE`).

---

## 🌟 Características Clave

- **Independencia Absoluta:** El benchmark evalúa a los sistemas como cajas negras, comunicándose únicamente a través de la interfaz común `interfaces/v1.py`. No asume nada de thresholds o estados internos.
- **Rigor Estadístico:** Cada tasa de éxito de ataque (ASR) o sobrebloqueo (ORR) reportada viene acompañada de un intervalo de confianza del 95% calculado de forma reproducible mediante simulación bootstrap (N=10,000, semilla fija).
- **Cobertura de Datasets:** Soporte integrado con validación de hashes SHA256 para: JailbreakBench, AdvBench, HarmBench, AgentHarm (bajo licencia protegida) y XSTest (para falsos positivos).
- **Capa de Ataques Adversariales:** Permite aplicar de forma dinámica transformaciones de ofuscación como codificación Base64, reemplazos Leetspeak, envolturas de juego de rol y cifrado ROT13.
- **Visualización Premium:** Generación de reportes automáticos en JSON, CSV, Markdown y un panel HTML estático interactivo con gráficos integrados usando Chart.js.
- **Salvaguarda Anti-Gaming:** Oculta por defecto el 20% de las muestras (split held-out) a través de un algoritmo de hash MD5 determinista para evitar el sobreentrenamiento sobre el benchmark.

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
