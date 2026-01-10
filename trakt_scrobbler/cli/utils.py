from rich.prompt import InvalidResponse, PromptBase
from rich.text import Text


class MultiChoicePrompt(PromptBase[list[str]]):
    """Multiple selections using a numbered list."""

    validate_error_message = (
        "[prompt.invalid]Please enter a comma-separated list of integers[/]"
    )
    prompt_suffix = "\n > "

    def make_prompt(self, default) -> Text:
        # FIXME: Support default
        assert self.choices is not None, "No choices provided"
        prompt = self.prompt.copy()
        prompt.end = ""
        for i, c in enumerate(self.choices):
            prompt.append("\n [")
            prompt.append(str(i), "cyan")
            prompt.append("] ")
            prompt.append(c, "prompt.choices")
        prompt.append(self.prompt_suffix)
        return prompt

    def response_type(self, value: str) -> list[str]:
        assert self.choices is not None, "No choices provided"
        res = []
        for v in value.split(","):
            try:
                i = int(v.strip())
            except ValueError as e:
                try:
                    # let user type the exact value.
                    assert self.case_sensitive, "FIXME: Doesn't respect case_sensitive"
                    i = self.choices.index(v.strip())
                except ValueError:
                    raise InvalidResponse(
                        f"[red]Please enter a number or comma-separated names![/] {e}"
                    )
            try:
                res.append(self.choices[i])
            except IndexError:
                raise InvalidResponse(self.illegal_choice_message + f"[/]: Got {i}")
        return res

    def process_response(self, value: str) -> list[str]:
        return self.response_type(value)
