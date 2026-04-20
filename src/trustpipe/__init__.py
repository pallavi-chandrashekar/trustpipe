"""TrustPipe — AI Data Supply Chain Trust & Provenance Platform.

Usage (the 3-line promise):
    from trustpipe import TrustPipe
    tp = TrustPipe()
    tp.track(df, name="customers")
"""

from trustpipe._version import __version__
from trustpipe.core.engine import TrustPipe
from trustpipe.provenance.record import ProvenanceRecord

__all__ = [
    "__version__",
    "TrustPipe",
    "ProvenanceRecord",
]
