from __future__ import annotations

from .contracts import DEPLOYMENT_SINKS, PRIVATE_SOURCE_TYPES


def is_private_source(source_type: str) -> bool:
    return source_type in PRIVATE_SOURCE_TYPES


def is_deployment_sink(sink: str) -> bool:
    return sink in DEPLOYMENT_SINKS

