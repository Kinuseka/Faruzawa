"""App-facing catalog and streaming facades.

Upstream adapters are selected by Backend.provider (src1, src2, ...) in the local API registry.
"""
from bridge.catalog import Catalog, catalog
from bridge.streaming import Streaming, streaming

__all__ = ["Catalog", "catalog", "Streaming", "streaming"]
