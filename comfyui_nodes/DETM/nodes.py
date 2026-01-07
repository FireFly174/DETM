from __future__ import annotations

# Thin registration module for ComfyUI.
# All logic lives in sibling modules; this file only exposes mapping dicts.

from .common import ensure_detm_on_path  # noqa: F401

from .nodes_legacy import (
    DETMInitNode,
    DETMStepNode,
    DETMRunNode,
    DETMTimeSeriesAnalyzeNode,
    DETMSaveGifNode,
    DETMRandomSearchNode,
)
from .nodes_scheduler import (
    DETMConfigNode,
    DETMSchedulerTickNode,
    DETMBusPublishNode,
    DETMMakeInfluenceEventNode,
)
from .nodes_runtime import DETMRunPubNode
from .nodes_analysis import (
    DETMStateToImageNode,
    DETMStateToImageEveryNNode,
    DETMSeriesBufferNode,
    DETMFrameBufferNode,
    DETMDetectAttractorsNode,
)

NODE_CLASS_MAPPINGS = {
    "DETM Run": DETMRunPubNode,
    "DETM Run (legacy init+step)": DETMRunNode,
    "DETM Init (legacy)": DETMInitNode,
    "DETM Step (legacy)": DETMStepNode,
    "DETM TimeSeries Analyze": DETMTimeSeriesAnalyzeNode,
    "DETM Save GIF": DETMSaveGifNode,
    "DETM Random Search (legacy)": DETMRandomSearchNode,
    "DETM Config": DETMConfigNode,
    "DETM Scheduler Tick": DETMSchedulerTickNode,
    "DETM Bus Publish": DETMBusPublishNode,
    "DETM Make Influence Event": DETMMakeInfluenceEventNode,
    "DETM State To Image": DETMStateToImageNode,
    "DETM State To Image (every N)": DETMStateToImageEveryNNode,
    "DETM Series Buffer": DETMSeriesBufferNode,
    "DETM Frame Buffer": DETMFrameBufferNode,
    "DETM Detect Attractors": DETMDetectAttractorsNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "DETM Run": "DETM: Run",
    "DETM Run (legacy init+step)": "DETM: Run (legacy)",
    "DETM Init (legacy)": "DETM: Init (legacy)",
    "DETM Step (legacy)": "DETM: Step (legacy)",
    "DETM TimeSeries Analyze": "DETM: TimeSeries Analyze (windows)",
    "DETM Save GIF": "DETM: Save GIF (frames)",
    "DETM Random Search (legacy)": "DETM: Random Search (legacy)",
    "DETM Config": "DETM: Config (json)",
    "DETM Scheduler Tick": "DETM: Scheduler Tick",
    "DETM Bus Publish": "DETM: Bus Publish (events)",
    "DETM Make Influence Event": "DETM: Make Influence Event",
    "DETM State To Image": "DETM: State -> Image",
    "DETM State To Image (every N)": "DETM: State -> Image (every N ticks)",
    "DETM Series Buffer": "DETM: Series Buffer (state->windows)",
    "DETM Frame Buffer": "DETM: Frame Buffer (state->frames)",
    "DETM Detect Attractors": "DETM: Detect Attractors",
}


