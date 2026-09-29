"""
StandSpec AI — Agent State Contract (Phase P1-F)
Maintains full execution state, tool interactions, candidate tracking,
and audit trails for the LLM-powered procurement agent.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import uuid
import time


@dataclass
class ToolCallRecord:
    """Audit record for a single tool call."""
    step: int
    tool: str
    arguments: Dict[str, Any]
    thought: Optional[str] = None
    timestamp: float = field(default_factory=time.time)


@dataclass
class ToolResultRecord:
    """Audit record for a single tool result."""
    step: int
    tool: str
    status: str  # SUCCESS, ERROR, NO_DATA
    data: Any
    error_message: Optional[str] = None
    timestamp: float = field(default_factory=time.time)


@dataclass
class AgentState:
    """
    Authoritative state for a StandSpec agent session.
    Bounded by MAX_AGENT_STEPS = 6 to prevent infinite loops.
    """
    raw_query: str
    agent_run_id: str = field(default_factory=lambda: f"RUN_{uuid.uuid4().hex[:12].upper()}")
    conversation_context: List[Dict[str, str]] = field(default_factory=list)
    normalized_requirements: Dict[str, Any] = field(default_factory=dict)
    clarifications: List[str] = field(default_factory=list)
    clarification_reason: Optional[str] = None
    
    # Tool tracking
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    tool_results: List[Dict[str, Any]] = field(default_factory=list)
    
    # Knowledge & evidence
    candidates: List[Dict[str, Any]] = field(default_factory=list)
    candidate_evidence: Dict[str, Any] = field(default_factory=dict)  # designation -> EvidenceBundle
    candidate_applicability: Dict[str, Any] = field(default_factory=dict)  # designation -> ApplicabilityResult
    candidate_lifecycle: Dict[str, Any] = field(default_factory=dict)  # designation -> LifecycleResult
    candidate_regulatory: Dict[str, Any] = field(default_factory=dict)  # designation -> RegulatoryResult
    evidence_bundle: Dict[str, Any] = field(default_factory=dict)
    decision_trace: Dict[str, Any] = field(default_factory=dict)
    
    # Output proposals & validation
    proposed_answer: Optional[Dict[str, Any]] = None
    validation_status: Optional[str] = None  # ACCEPT, REVISE, REJECT
    validation_errors: List[str] = field(default_factory=list)
    validated_answer: Optional[Dict[str, Any]] = None
    termination_reason: Optional[str] = None
    
    # Loop bounds
    step_count: int = 0
    max_steps: int = 6
    search_rounds: int = 0
    max_search_rounds: int = 2
    revision_rounds: int = 0
    max_revision_rounds: int = 1
    
    # Audit & performance
    execution_mode: str = "LLM_ASSISTED"  # DETERMINISTIC_ONLY, LLM_ASSISTED, LLM_FALLBACK
    model_name: Optional[str] = None
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None

    def next_step(self) -> int:
        """Advances to the next agent orchestration step."""
        self.step_count += 1
        return self.step_count

    def record_tool_call(self, tool: str, arguments: Dict[str, Any], thought: Optional[str] = None) -> int:
        """Records an outgoing tool invocation."""
        if self.step_count == 0:
            self.step_count = 1
        rec = {
            "step": self.step_count,
            "tool": tool,
            "arguments": arguments,
            "thought": thought,
            "timestamp": time.time(),
        }
        self.tool_calls.append(rec)
        if tool == "search_standards":
            self.search_rounds += 1
        return len(self.tool_calls)

    def record_tool_result(self, tool: str, status: str, data: Any, error_message: Optional[str] = None) -> None:
        """Records an incoming tool execution result."""
        rec = {
            "step": self.step_count,
            "tool": tool,
            "status": status,
            "data": data,
            "error_message": error_message,
            "timestamp": time.time(),
        }
        self.tool_results.append(rec)
        for tc in reversed(self.tool_calls):
            if tc.get("tool") == tool and "status" not in tc:
                tc["status"] = status
                tc["output"] = data
                tc["error"] = error_message
                break

    @property
    def is_exhausted(self) -> bool:
        """Returns True if the agent has reached the maximum allowed orchestration steps."""
        return self.step_count >= self.max_steps

    @property
    def can_search(self) -> bool:
        """Returns True if another retrieval round is permitted."""
        return self.search_rounds < self.max_search_rounds

    @property
    def can_revise(self) -> bool:
        """Returns True if the LLM can make a revision proposal after validator veto."""
        return self.revision_rounds < self.max_revision_rounds

    def to_audit_dict(self) -> Dict[str, Any]:
        """Produces a clean audit record without sensitive data."""
        return {
            "agent_run_id": self.agent_run_id,
            "raw_query": self.raw_query,
            "execution_mode": self.execution_mode,
            "model_name": self.model_name,
            "step_count": self.step_count,
            "search_rounds": self.search_rounds,
            "revision_rounds": self.revision_rounds,
            "tool_calls": [
                {"step": tc["step"], "tool": tc["tool"], "arguments": tc["arguments"]}
                for tc in self.tool_calls
            ],
            "candidate_designations": [c.get("designation") for c in self.candidates if isinstance(c, dict)],
            "termination_reason": self.termination_reason,
            "validation_status": self.validation_status,
            "latency_seconds": round(time.time() - self.start_time, 4) if not self.end_time else round(self.end_time - self.start_time, 4),
        }
