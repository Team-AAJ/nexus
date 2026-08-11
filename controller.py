import json

from voice.intent_router import IntentRouter
from voice.llm_chat import NexusLLM
from common import ExecutionAction, ExecutionResult, default_capabilities


class ActionPlanningError(Exception):
    """Raised when the command could not be turned into a valid action."""


class NexusController:

    def __init__(self, confirm_callback=None):

        self.router = IntentRouter()

        self.llm = NexusLLM()

        self.execution_gateway = None
        self.capabilities = default_capabilities()

        # Optional Callable[[str], bool] supplied by the voice layer so this
        # controller can ask "do you approve?" out loud before a high-risk
        # action (delete, pay, login, submit, ...) runs, without this class
        # needing to know anything about microphones/speakers itself.
        self.confirm_callback = confirm_callback

    def execute_action(self, action: dict) -> ExecutionResult:
        """Execute an already-planned action from the partner orchestrator."""
        if self.execution_gateway is None:
            from execution_gateway import ExecutionGateway
            self.execution_gateway = ExecutionGateway()
        return self.execution_gateway.execute(action)

    def handle(self, command: str) -> str:

        intent = self.router.route(command)

        # -------------------------
        # Normal conversation
        # -------------------------

        if intent.category == "chat":

            return self.llm.ask(command)

        # -------------------------
        # Browser / Desktop -> plan real ExecutionAction(s) and run them
        # -------------------------

        if intent.category in ("browser", "desktop"):

            return self._handle_task(command)

        return self.llm.ask(command)

    def _handle_task(self, command: str) -> str:
        try:
            actions = self._plan_actions(command)
        except ActionPlanningError:
            # Could not confidently turn this into a safe, supported
            # action. Never guess-execute -- fall back to a normal
            # conversational answer instead (matches the "safe structured
            # failure, never random clicking" rule the execution layer
            # already follows).
            return self.llm.ask(command)

        if not actions:
            return self.llm.ask(command)

        spoken_parts = []
        for action in actions:
            spoken_parts.append(self._execute_with_confirmation(action))
        return " ".join(spoken_parts)

    def _execute_with_confirmation(self, action: dict) -> str:
        result = self.execute_action(action)

        if not result.success and result.message == "Action blocked pending user approval.":
            description = self._describe_action(action)
            approved = bool(self.confirm_callback) and self.confirm_callback(
                f"{description} karne se pehle confirm karo -- kya main aage badhu?"
            )
            if not approved:
                return f"Theek hai, maine {description} nahi kiya -- approval nahi mila."
            action = dict(action)
            action["approval_token"] = "user_voice_confirmed"
            result = self.execute_action(action)

        return self._describe_result(action, result)

    def _plan_actions(self, command: str) -> list[dict]:
        """Ask the LLM to translate free text into one or more
        ExecutionAction dicts, restricted to the platform/action names the
        execution layer actually supports (common.default_capabilities()).

        This is a deliberately small, single-turn translator -- it is not
        the multi-step research/planning "Brain" (that is a separate,
        larger piece of work). It only maps a clear, immediate instruction
        ("notepad kholo", "google.com kholo aur python search karo") onto
        real actions this execution layer can run and verify.
        """
        catalog = self.capabilities.list()
        catalog_text = "\n".join(
            f"- platform={item['platform']} action={item['action']} :: {item['description']}"
            for item in catalog
        )

        prompt = f"""Convert the user's instruction into a JSON object of the form:
{{"actions": [{{"platform": "desktop"|"browser", "action": "<one of the action names below>", "value": <string or null>, "target": {{}}, "parameters": {{}}}}]}}

Only use platform/action pairs from this exact list -- never invent a new one:
{catalog_text}

Rules:
- Reply with ONLY the JSON object, nothing else -- no explanation, no markdown fences.
- If the instruction is not a clear, executable desktop/browser task (e.g. it's a question, or too vague to act on safely), reply with exactly: {{"actions": []}}
- Prefer the smallest number of actions that accomplishes what was asked.
- Most actions take one piece of info via "value" (e.g. open_app just needs the app name).
- Some actions need MORE than one piece of info -- put those into "target" with these exact key names:
  copy_file/move_file/copy_folder/move_folder -> {{"source": "...", "destination": "..."}}
  rename_file/rename_folder -> {{"source": "...", "new_name": "..."}}
  search_file/search_folder -> {{"directory": "...", "query": "..."}}
  move_mouse/drag_mouse -> {{"x": <int>, "y": <int>}}
  notify -> {{"title": "...", "message": "..."}}
  hotkey -> {{"keys": ["ctrl", "c"]}}
  kill_process -> {{"process_name": "..."}}
  restart_process -> {{"process_name": "...", "command": "..."}}

User instruction: {command}"""

        try:
            raw = self.llm.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=400,
            )
            text = raw.choices[0].message.content.strip()
            text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            payload = json.loads(text)
        except Exception as error:
            raise ActionPlanningError(str(error)) from error

        actions = payload.get("actions", [])
        for action in actions:
            if not self.capabilities.supports(action.get("platform", ""), action.get("action", "")):
                raise ActionPlanningError(
                    f"Unsupported platform/action: {action.get('platform')}/{action.get('action')}"
                )
        return actions

    @staticmethod
    def _describe_action(action: dict) -> str:
        action_name = action.get("action", "this action")
        value = action.get("value")
        return f"{action_name}" + (f" ({value})" if value else "")

    @staticmethod
    def _describe_result(action: dict, result: ExecutionResult) -> str:
        description = NexusController._describe_action(action)
        if result.success:
            return f"{description} ho gaya."
        return f"{description} nahi ho paya -- {result.error or result.message}"
