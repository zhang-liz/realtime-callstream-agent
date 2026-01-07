import openai
import asyncio
import structlog

logger = structlog.get_logger()

class CollectionsAgent:
    """LLM-powered collections agent with compliance constraints"""

    def __init__(self, api_key: str):
        self.client = openai.OpenAI(api_key=api_key)

    async def generate_response(self, user_message: str, stream_sid: str) -> str:
        """
        Generate a response as a collections agent
        """
        system_prompt = """You are a professional collections agent for a financial services company. Your role is to help customers resolve outstanding payments in a respectful, empathetic, and compliant manner.

Key guidelines:
- Always be polite and professional
- Listen actively to customer concerns
- Offer flexible payment arrangements when appropriate
- Never threaten legal action or collection agencies
- Never discuss account details without verification
- Keep responses concise and conversational
- End conversations positively when possible

You must comply with FDCPA and state collection laws:
- No calls before 8 AM or after 9 PM local time
- No harassment or abusive language
- No false representations about amount owed
- No threats of violence or arrest
- No communication with third parties about debt

Respond naturally as if speaking on a phone call."""

        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message}
                    ],
                    max_tokens=150,
                    temperature=0.7
                )
            )

            ai_response = response.choices[0].message.content.strip()

            logger.info("LLM response generated",
                       stream_sid=stream_sid,
                       user_message_length=len(user_message),
                       response_length=len(ai_response))

            return ai_response

        except Exception as e:
            logger.error("LLM request failed",
                        stream_sid=stream_sid,
                        error=str(e))
            return "I'm sorry, I'm having trouble processing your request. Can you please try again?"
