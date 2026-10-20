"""Internacionalização leve: textos-fonte em inglês, catálogo em português.

- ``tr("English text {x}", x=1)`` traduz (se necessário) e formata.
- ``N_("English text")`` apenas marca o texto para tradução posterior
  (usado em constantes de módulo, traduzidas na hora de exibir com ``tr(var)``).
"""
from __future__ import annotations

DEFAULT_LANGUAGE = "en"
LANGUAGES = (("en", "English"), ("pt", "Português"))

_language = DEFAULT_LANGUAGE


def set_language(code: str) -> None:
    global _language
    _language = code if code in dict(LANGUAGES) else DEFAULT_LANGUAGE


def get_language() -> str:
    return _language


def N_(text: str) -> str:  # noqa: N802 - convenção gettext
    return text


def tr(text: str, **kwargs) -> str:
    if _language != DEFAULT_LANGUAGE:
        from glucowidget.locales import CATALOGS

        text = CATALOGS.get(_language, {}).get(text, text)
    return text.format(**kwargs) if kwargs else text


def decimal(text: str) -> str:
    """Troca o separador decimal conforme o idioma (ponto em inglês, vírgula em português)."""
    return text.replace(".", ",") if _language == "pt" else text
