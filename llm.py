import openai
import asyncio
from typing import Optional

from exceptions import LLMError
from config import Config, COLLECTIONS_AGENT_PROMPT
from core.logging import get_logger

logger = get_logger()


class CollectionsAgent:
    """LLM-powered collections agent with compliance constraints"""

    def __init__(self, api_key: str, config: Config):
        self.client = openai.OpenAI(api_key=api_key)
        self.config = config
        self.system_prompt = COLLECTIONS_AGENT_PROMPT

    async def generate_response(self, user_message: str, stream_sid: str) -> str:
        """
        Generate a response as a collections agent.
        
        Args:
            user_message: The user's transcribed message
            stream_sid: The stream SID for logging correlation
            
        Returns:
            The generated response text
            
        Raises:
            LLMError: If the LLM request fails
        """
        try:
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model=self.config.llm_model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_message},
                ],
                max_tokens=self.config.llm_max_tokens,
                temperature=self.config.llm_temperature,
            )

            content = response.choices[0].message.content
            if not content:
                raise LLMError("LLM returned empty response")
            
            ai_response = content.strip()

            logger.info("LLM response generated",
                       stream_sid=stream_sid,
                       user_message_length=len(user_message),
                       response_length=len(ai_response))

            return ai_response

        except Exception as e:
            logger.error("LLM request failed",
                        stream_sid=stream_sid,
                        error=str(e))
            raise LLMError(f"Failed to generate LLM response: {e}") from e
