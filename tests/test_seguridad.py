"""Controles de seguridad del servidor y de la configuración de Vercel."""
import base64
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import parse_qs

import pytest

import server

RAIZ = Path(__file__).resolve().parents[1]


def _vercel_cabeceras():
    cfg = json.loads((RAIZ / "vercel.json").read_text(encoding="utf-8"))
    bloque = next(b for b in cfg["headers"] if b["source"] == "/(.*)")
    return {h["key"]: h["value"] for h in bloque["headers"]}


def test_cabeceras_del_servidor_local_coinciden_con_vercel():
    vercel = _vercel_cabeceras()
    for clave, valor in server.CABECERAS_SEGURAS.items():
        assert vercel.get(clave) == valor, clave


def test_cabeceras_minimas_presentes():
    for clave in ["Content-Security-Policy", "X-Content-Type-Options", "X-Frame-Options",
                  "Referrer-Policy", "Permissions-Policy", "Cross-Origin-Opener-Policy"]:
        assert clave in server.CABECERAS_SEGURAS


def test_los_scripts_no_usan_unsafe_inline():
    csp = server.CABECERAS_SEGURAS["Content-Security-Policy"]
    script_src = next(p for p in csp.split(";") if p.strip().startswith("script-src"))
    assert "'unsafe-inline'" not in script_src
    assert "object-src 'none'" in csp and "frame-ancestors 'none'" in csp
    assert "style-src-elem 'self'" in csp  # no se aceptan bloques <style> inyectados


def test_el_script_de_la_pagina_coincide_con_la_huella_de_la_politica():
    html = (RAIZ / "static" / "index.html").read_text(encoding="utf-8")
    inline = re.findall(r"<script>(.*?)</script>", html, re.S)
    assert len(inline) == 1, "solo debe haber un script dentro de la página"
    huella = "sha256-" + base64.b64encode(hashlib.sha256(inline[0].encode("utf-8")).digest()).decode()
    assert f"'{huella}'" in server.CABECERAS_SEGURAS["Content-Security-Policy"]


def test_no_hay_manejadores_de_eventos_en_linea():
    for archivo in ["static/index.html", "static/alzea.js"]:
        texto = (RAIZ / archivo).read_text(encoding="utf-8")
        assert not re.search(r"\son(click|load|error|mouseover)\s*=", texto), archivo
        assert "javascript:" not in texto, archivo


def test_la_cache_tiene_tope():
    server._cache.clear()
    for i in range(server.MAX_CACHE + 50):
        server.cached(("prueba", i), 600, lambda i=i: i)
    assert len(server._cache) <= server.MAX_CACHE
    server._cache.clear()


def test_solo_se_aceptan_monedas_conocidas():
    assert server.moneda_de(parse_qs("")) == "mxn"
    assert server.moneda_de(parse_qs("moneda=original")) == "original"
    with pytest.raises(ValueError):
        server.moneda_de(parse_qs("moneda=<script>"))


def test_http_get_rechaza_conexiones_sin_cifrar():
    with pytest.raises(ValueError):
        server.http_get("http://example.com/")
    with pytest.raises(ValueError):
        server.http_get("file:///etc/passwd")


def test_el_periodo_no_baja_del_inicio_ni_pasa_de_hoy():
    desde, hasta = server.periodo(parse_qs("desde=2020-01-01&hasta=2099-01-01"))
    assert desde == server.INICIO
    assert hasta <= server.datetime.now(server.TZ).date()


@pytest.mark.parametrize("consulta", ["desde=no-es-fecha", "hasta=2026-13-45", "desde=2026-06-01&hasta=2026-05-01"])
def test_periodos_invalidos_se_rechazan(consulta):
    with pytest.raises(ValueError):
        server.periodo(parse_qs(consulta))
