# -*- coding: utf-8 -*-
import os
import tempfile

import pytest

from aegisbench.datasets.loaders import calculate_sha256, download_file, get_lock_config


@pytest.mark.network
def test_real_dataset_urls():
    """
    Test de integración marcado como network.
    Intenta descargar cada dataset configurado y comprueba que la URL está viva
    y el contenido coincide exactamente con el hash SHA256 bloqueado.
    """
    config = get_lock_config()

    # Probar al menos un par de datasets reales para validar que la red y hashes están correctos
    # Para agilizar el test, probamos jailbreakbench y xstest
    for dataset_name in ["jailbreakbench", "xstest"]:
        info = config[dataset_name]
        url = info["url"]
        expected_sha = info["sha256"]

        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_name = tmp.name
        try:
            download_file(url, tmp_name, expected_sha)
            # Si download_file no lanzó error, significa que la descarga fue exitosa
            # y el hash SHA256 coincide exactamente.
            assert os.path.exists(tmp_name)
            assert calculate_sha256(tmp_name) == expected_sha
        finally:
            if os.path.exists(tmp_name):
                os.remove(tmp_name)
