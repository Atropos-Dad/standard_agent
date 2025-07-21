from jentic_agents.communication.hitl.base_intervention_hub import HumanInTheLoopInterface, DelegationAssessment
from jentic_agents.utils.llm import LiteLLMChatLLM
from typing import Optional

class NoopInterventionHub(HumanInTheLoopInterface):
    """
    Null escalation that doesn't provide human help.
    Used when the agent should work completely autonomously.
    """

    def __init__(self, llm: LiteLLMChatLLM):
        super().__init__(llm=llm)

    def should_delegate_to_human(self, context: Optional[str] = None) -> DelegationAssessment:
        return DelegationAssessment(should_delegate=False, message="")

    def request_human_input(self, question: str) -> str:
        return ""
