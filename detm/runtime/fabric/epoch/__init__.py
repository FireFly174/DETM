"""Epoch/watermark coordination for fabric commit boundaries."""

from detm.runtime.fabric.epoch.contracts import EpochDecision, FabricEpochCoordinator
from detm.runtime.fabric.epoch.file import FileEpochWatermarkCoordinator
from detm.runtime.fabric.epoch.memory import InMemoryEpochWatermarkCoordinator
from detm.runtime.fabric.epoch.operations import commit_epoch, commit_watermark
from detm.runtime.fabric.epoch.replicated import ReplicatedFileEpochWatermarkCoordinator

__all__ = [
    "EpochDecision",
    "FabricEpochCoordinator",
    "FileEpochWatermarkCoordinator",
    "InMemoryEpochWatermarkCoordinator",
    "ReplicatedFileEpochWatermarkCoordinator",
    "commit_epoch",
    "commit_watermark",
]

