"""SAQR AI Studio engine.

Public surface is intentionally small: hardware profiling, the model manager,
the face pipeline, camera capture and the local bridge API.
"""

from .version import __version__

__all__ = ["__version__"]
