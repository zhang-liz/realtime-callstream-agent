import openai
import asyncio
from typing import Any, List, cast

from exceptions import LLMError
from config import Config, COLLECTIONS_AGENT_PROMPT
from core.logging import get_logger

logger = get_logger()


class CollectionsAgent:
    """LLM-powered collections agent with compliance constraints and short-term memory."""

    def __init__(self, api_key: str, config: Config):
        self.client = openai.OpenAI(api_key=api_key)
        self.config = config
        self.system_prompt = COLLECTIONS_AGENT_PROMPT
        # Per-call short-term history: list of prior user/assistant turns
        self._history: List[dict[str, Any]] = []
        # Limit the number of past turns we keep to bound cost
        self._max_history_messages: int = 10

    def reset_history(self) -> None:
        """Clear conversation history, e.g. when a call ends."""
        self._history.clear()

    async def generate_response(self, user_message: str, stream_sid: str) -> str:
        """
        Generate a response as a collections agent, using short conversation history.
        
        Args:
            user_message: The user's transcribed message
            stream_sid: The stream SID for logging correlation
            
        Returns:
            The generated response text
            
        Raises:
            LLMError: If the LLM request fails
        """
        try:
            # Build message list with system prompt, prior turns, and new user message
            messages: List[dict[str, Any]] = [
                {"role": "system", "content": self.system_prompt},
                *self._history,
                {"role": "user", "content": user_message},
            ]

            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model=self.config.llm_model,
                messages=cast(Any, messages),
                max_tokens=self.config.llm_max_tokens,
                temperature=self.config.llm_temperature,
            )

            content = response.choices[0].message.content
            if not content:
                raise LLMError("LLM returned empty response")
            
            ai_response = content.strip()

            # Update short-term memory with this turn and trim if needed
            self._history.append({"role": "user", "content": user_message})
            self._history.append({"role": "assistant", "content": ai_response})
            if len(self._history) > self._max_history_messages:
                # Drop oldest messages but keep ordering; always even length
                excess = len(self._history) - self._max_history_messages
                self._history = self._history[excess:]

            logger.info(
                "LLM response generated",
                stream_sid=stream_sid,
                user_message_length=len(user_message),
                response_length=len(ai_response),
                history_messages=len(self._history),
            )

            return ai_response

        except Exception as e:
            logger.error(
                "LLM request failed",
                stream_sid=stream_sid,
                error=str(e),
            )
            raise LLMError(f"Failed to generate LLM response: {e}") from e
