"""Error pipeline yang pesannya aman ditampilin langsung ke user."""


class PipelineError(Exception):
    def __init__(self, step: str, message: str) -> None:
        super().__init__(f"[{step}] {message}")
        self.step = step
        self.message = message
