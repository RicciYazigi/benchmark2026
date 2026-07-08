# Usa una imagen oficial de Python como base
FROM python:3.10-slim

# Evita que Python escriba archivos .pyc en el disco
ENV PYTHONDONTWRITEBYTECODE=1
# Evita que Python almacene en búfer stdout y stderr
ENV PYTHONUNBUFFERED=1

# Establece el directorio de trabajo en el contenedor
WORKDIR /app

# Instala dependencias del sistema necesarias
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copia los archivos de configuración del proyecto
COPY pyproject.toml README.md /app/

# Instala las dependencias del proyecto (el modo de desarrollo se puede omitir en producción,
# pero instalamos las dependencias estándar)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# Copia el código fuente del proyecto y configuraciones
COPY src/ /app/src/
COPY configs/ /app/configs/

# Reinstala el proyecto en modo no-editable para producción
RUN pip install --no-cache-dir .

# Define el punto de entrada predeterminado utilizando la CLI de AegisBench
ENTRYPOINT ["aegisbench"]

# Por defecto, muestra la ayuda de la CLI al ejecutar el contenedor
CMD ["--help"]
