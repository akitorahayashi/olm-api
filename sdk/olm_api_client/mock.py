import asyncio
import re
from typing import AsyncGenerator

# Streaming configuration
TOKEN_DELAY = 0.1  # Faster delay between tokens (seconds) - reduced from 0.07


class MockOllamaApiClient:
    """
    A high-fidelity mock client that simulates real Ollama API behavior.
    """

    def __init__(self):
        self.mock_responses = [
            "Hello! How can I help you today?",
            "That's an interesting question. Could you tell me more about it?",
            "I understand. Is there anything else you'd like to know?",
            "Yes, I think you're absolutely right about that.",
            "I'm sorry, but could you be more specific about what you're looking for?",
        ]
        self.response_index = 0

    def _tokenize_realistic(self, text: str) -> list[str]:
        """
        Tokenize text in a way that resembles real LLM tokenization.

        This splits text into tokens that include:
        - Whole words
        - Punctuation as separate tokens
        - Partial words/subwords occasionally
        - Keep think tags intact for proper processing
        """
        # Special handling for think tags to keep them intact
        think_pattern = r"(<think>|</think>)"
        parts = re.split(think_pattern, text)

        result = []
        for part in parts:
            if part in ["<think>", "</think>"]:
                # Keep think tags as single tokens
                result.append(part)
                continue

            if not part.strip():
                continue

            # First split by whitespace and punctuation, keeping separators
            tokens = re.findall(r"\S+|\s+", part)

            for token in tokens:
                if token.isspace():
                    continue  # Skip pure whitespace tokens

                # For words longer than 4 characters, occasionally split into subwords
                if len(token) > 6 and token.isalpha():
                    # 30% chance to split long words
                    if hash(token) % 10 < 3:  # Deterministic pseudo-random
                        mid = len(token) // 2
                        result.append(token[:mid])
                        result.append(token[mid:])
                        continue

                # Split punctuation from words (except for think tags)
                if re.search(r"[^\w\s]", token) and token not in [
                    "<think>",
                    "</think>",
                ]:
                    parts_inner = re.findall(r"\w+|[^\w\s]", token)
                    result.extend(parts_inner)
                else:
                    result.append(token)

        return result

    def _create_thinking_process(self, prompt: str) -> str:
        """
        Generate a realistic thinking process based on the prompt.
        """
        # Shorter thinking templates for faster testing
        thinking_templates = [
            """Starting analysis.
First, I need to identify the main points of the provided content.
Next, I'll organize and structure the important information.
Finally, I'll create a concise and understandable summary.
Thinking process complete.""",
            """Breaking down the task.
Step 1: Understand the content overview
Step 2: Extract key points
Step 3: Organize in logical flow
Step 4: Generate clear summary
Ready to proceed.""",
        ]

        # Choose template based on prompt hash for consistency
        template_idx = abs(hash(prompt[:100])) % len(
            thinking_templates
        )  # Use only first 100 chars of prompt
        return thinking_templates[template_idx]

    async def _stream_response(self, full_text: str) -> AsyncGenerator[str, None]:
        """
        Stream response token by token, simulating real Ollama API behavior.
        """
        tokens = self._tokenize_realistic(full_text)

        for i, token in enumerate(tokens):
            await asyncio.sleep(TOKEN_DELAY)

            # Add space before token (except first token) if it's a word
            if i > 0 and token.isalnum() and not tokens[i - 1].endswith("\n"):
                yield " "
                await asyncio.sleep(TOKEN_DELAY * 0.3)  # Shorter delay for spaces

            yield token

    def generate(self, prompt: str, model: str = None) -> AsyncGenerator[str, None]:
        """
        Generates mock text responses with realistic streaming behavior.

        Args:
            prompt: The prompt to send to the model.
            model: The name of the model to use for generation.

        Returns:
            AsyncGenerator yielding text chunks that match real API format.
        """
        # Create thinking process
        thinking = self._create_thinking_process(prompt)

        # Custom responses for specific inputs
        custom_responses = {
            "hello": "Hello! 😊 How are you today? I'm here to help with anything you need!",
            "hi": "Hi there! How are you doing? What can I assist you with?",
            "test": "This is a test response from the mock client. Everything is working correctly!",
            "help": "I'm here to help! What would you like to know? Feel free to ask me anything.",
            "thanks": "You're very welcome! Happy to help anytime. Is there anything else you need?",
        }

        # Check for custom responses first
        response_text = None
        for key, response in custom_responses.items():
            if key in prompt.lower():
                response_text = response
                break

        # If no custom response, use cycling responses
        if not response_text:
            response_text = self.mock_responses[
                self.response_index % len(self.mock_responses)
            ]
            self.response_index += 1

        # Construct full response with thinking tags (similar to real API)
        full_response = f"<think>\n{thinking}\n</think>\n\n{response_text}"

        return self._stream_response(full_response)
