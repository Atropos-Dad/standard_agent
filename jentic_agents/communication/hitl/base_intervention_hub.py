
from abc import abstractmethod
from typing import Optional
import json
from dataclasses import dataclass
from jentic_agents.utils.llm import LiteLLMChatLLM
import jentic_agents.communication.hitl._prompts as prompts

# If should_delegate is false then message is treated as a "tip" or left empty.
@dataclass 
class DelegationAssessment:
    should_delegate: bool
    message: str

class HumanInTheLoopInterface:
    def __init__(
            self,
            llm: LiteLLMChatLLM
    ):
        self.llm = llm

    """
    This is a generic function that all subclasses can use, therefore in base class 
    Subclasses can use request_human_input to display the message as appropriate
    """
    
    def should_delegate_to_human(self, context: Optional[str] = None) -> DelegationAssessment:
        assessment_prompt = prompts.DELEGATION_ASSESSMENT_PROMPT.format(context=context or "")
        response = self.llm.chat(assessment_prompt)
        
        try:
            json_response = json.loads(response)
            should_delegate = json_response.get("should_delegate")
            message = json_response.get("message")

            if not isinstance(should_delegate, bool) or not isinstance(message, str):
                raise ValueError(
                    f"'should_delegate' must be a boolean and 'message' must be a string. "
                    f"Got: should_delegate={should_delegate} (type: {type(should_delegate)}), "
                    f"message={message} (type: {type(message)})"
                )

            return DelegationAssessment(
                should_delegate=should_delegate,
                message=message
            )

        except json.JSONDecodeError as e:
            raise Exception(f"failed to parse JSON: {e}")

    @abstractmethod
    def request_human_input(self, question: str) -> str:
        raise NotImplementedError


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
