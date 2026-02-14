"""ROI stage for refinement pipeline."""

from __future__ import annotations

import numpy as np

from detm.runtime.refinement.geometry import roi_mask as _roi_mask
from detm.runtime.refinement.pipeline.contracts import DetectionContext, NonfiniteRoiSelection, RoiSelection


def detect_nonfinite_roi(context: DetectionContext) -> NonfiniteRoiSelection | None:
    if int(context.overflow_count) > 0:
        return None

    nonfinite_energy = ~np.isfinite(context.energy)
    nonfinite_entropy = ~np.isfinite(context.entropy)
    nonfinite_tau = ~np.isfinite(context.internal_time)
    nonfinite_total_mask = nonfinite_energy | nonfinite_entropy | nonfinite_tau
    nonfinite_count = int(nonfinite_total_mask.sum())
    if nonfinite_count <= 0:
        return None

    center_y, center_x = np.unravel_index(int(np.argmax(nonfinite_total_mask.astype(np.int32))), nonfinite_total_mask.shape)
    radius = min(3, 1 + int(np.sqrt(max(1, nonfinite_count)) // 2))
    mask = _roi_mask(
        context.entropy.shape,
        center_y=int(center_y),
        center_x=int(center_x),
        radius=int(radius),
        boundary=context.boundary,
    )
    area = int(mask.sum())
    if area <= 0:
        return None

    return NonfiniteRoiSelection(
        center_x=int(center_x),
        center_y=int(center_y),
        radius=int(radius),
        area=int(area),
        mask=mask,
        boundary=context.boundary,
        nonfinite_energy=nonfinite_energy,
        nonfinite_entropy=nonfinite_entropy,
        nonfinite_tau=nonfinite_tau,
        nonfinite_total_count=int(nonfinite_count),
    )


def detect_overflow_roi(context: DetectionContext) -> RoiSelection | None:
    if int(context.overflow_count) <= 0:
        return None

    center_y, center_x = np.unravel_index(int(np.argmax(context.overflow_score)), context.overflow_score.shape)
    radius = min(3, 1 + int(np.sqrt(max(1, context.overflow_count)) // 2))
    mask = _roi_mask(
        context.entropy.shape,
        center_y=int(center_y),
        center_x=int(center_x),
        radius=int(radius),
        boundary=context.boundary,
    )
    area = int(mask.sum())
    if area <= 0:
        return None

    return RoiSelection(
        center_x=int(center_x),
        center_y=int(center_y),
        radius=int(radius),
        area=int(area),
        mask=mask,
        boundary=context.boundary,
    )


__all__ = ["detect_nonfinite_roi", "detect_overflow_roi"]
