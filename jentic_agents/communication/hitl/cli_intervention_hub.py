from .base_intervention_hub import HumanInTheLoopInterface

class CliInterventionHub(HumanInTheLoopInterface):

    def request_human_input(self, question: str) -> str:
        print("\n" + "=" * 60)
        print("🤖 STANDARD AGENT REQUESTING USER HELP")
        print("=" * 60)

        print(f"Question: {question}\n")

        response = input("Your response: ").strip()
        print("=" * 60 + "\n")

        print("✅ Response received. Resuming autonomous operation.\n")
        return response

        
        


