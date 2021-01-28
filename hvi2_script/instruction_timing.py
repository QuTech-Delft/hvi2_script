"""
@author: sdesnoo
"""
from dataclasses import dataclass, field
from typing import Optional, List, Any

@dataclass
class InstructionTiming:
    # values in number cycles
    fetch_time: int
    execution_time: Optional[int] = None
    start_latency: int = 0
    entry_latency: int = 0
    end_latency: int = 0
    iteration_overhead: int = 0
    exit_overhead: int = 0
    synchronized: bool = False
    non_deterministic: Optional[str] = None
    resources: List[Any] = field(default_factory=list)
    dependencies: List[Any] = field(default_factory=list)

    def get_tail_ns(self):
        return 10*max(self.fetch_time, self.end_latency)

    @property
    def entry_latency_ns(self):
        return 10*self.entry_latency

    @property
    def iteration_overhead_ns(self):
        return 10*self.iteration_overhead

def calculate_start_delay(start_delay, timing: InstructionTiming):
    return start_delay + 10*timing.start_latency