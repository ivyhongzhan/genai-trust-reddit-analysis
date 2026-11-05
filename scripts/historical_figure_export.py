"""Recreate the historical Day 16 vector export, including its 200 dpi images.

This preserves an old reference for comparison; it is not the high-resolution
export and must not be mistaken for a passing modern source preflight.
"""

def save_historical_vector(fig, stem):
    fig.savefig(stem.with_suffix('.svg'), dpi=200, bbox_inches='tight')
    fig.savefig(stem.with_suffix('.pdf'), dpi=200, bbox_inches='tight')
