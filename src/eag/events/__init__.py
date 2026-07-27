"""EAG domain events and event bus."""

from eag.events.bus import EventBus, Subscription
from eag.events.event import Event
from eag.events.types import (
    CapabilityRegistered,
    CapabilityUnregistered,
    KernelBootCompleted,
    KernelBootFailed,
    KernelBootStarted,
    KernelShutdownCompleted,
    KernelShutdownFailed,
    KernelShutdownStarted,
    PluginLoadCompleted,
    PluginLoadFailed,
    PluginLoadStarted,
    PluginRegistered,
    PluginUnloadCompleted,
    PluginUnloadFailed,
    PluginUnloadStarted,
)

__all__ = [
    "Event",
    "EventBus",
    "Subscription",
    "KernelBootCompleted",
    "KernelBootFailed",
    "KernelBootStarted",
    "KernelShutdownCompleted",
    "KernelShutdownFailed",
    "KernelShutdownStarted",
    "CapabilityRegistered",
    "CapabilityUnregistered",
    "PluginLoadCompleted",
    "PluginLoadFailed",
    "PluginLoadStarted",
    "PluginRegistered",
    "PluginUnloadCompleted",
    "PluginUnloadFailed",
    "PluginUnloadStarted",
]
