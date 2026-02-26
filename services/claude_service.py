# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Claude API wrapper for generating proposal and report content."""

import logging
import anthropic
from services.config_service import load_prompts

logger = logging.getLogger(__name__)


class ClaudeService:
    """Handles all Claude API interactions for content generation."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-5-20250929"):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.prompts = load_prompts()
        self.system_prompt = self.prompts["system_prompt"]
        self.total_input_tokens = 0
        self.total_output_tokens = 0

    def generate_section(self, prompt: str, max_tokens: int = 2000) -> str:
        """Generate content for a single proposal section."""
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=self.system_prompt,
                messages=[{"role": "user", "content": prompt}],
            )
            self._track_usage(response)
            return response.content[0].text
        except Exception as e:
            logger.error("Claude API error in generate_section: %s", e)
            return ""

    def generate_email(self, prompt: str) -> str:
        """Generate a cover email."""
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                system=self.system_prompt,
                messages=[{"role": "user", "content": prompt}],
            )
            self._track_usage(response)
            return response.content[0].text
        except Exception as e:
            logger.error("Claude API error in generate_email: %s", e)
            return ""

    def generate_insights(self, prompt: str) -> str:
        """Generate data-driven insights for a traction report."""
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1500,
                system=self.system_prompt,
                messages=[{"role": "user", "content": prompt}],
            )
            self._track_usage(response)
            return response.content[0].text
        except Exception as e:
            logger.error("Claude API error in generate_insights: %s", e)
            return ""

    def build_section_prompt(self, proposal_type: str, section_key: str, variables: dict) -> str:
        """Build a prompt for a specific section by filling in template variables."""
        type_prompts = self.prompts.get(proposal_type, {})
        template = type_prompts.get(section_key, "")
        if not template:
            return ""
        try:
            return template.format(**variables)
        except KeyError:
            # If a variable is missing, return template with remaining placeholders
            for key, value in variables.items():
                template = template.replace(f"{{{key}}}", str(value))
            return template

    def _track_usage(self, response):
        """Track token usage for cost monitoring."""
        if hasattr(response, "usage"):
            self.total_input_tokens += response.usage.input_tokens
            self.total_output_tokens += response.usage.output_tokens

    @property
    def usage_summary(self) -> str:
        """Return a human-readable usage summary."""
        return (
            f"Input: {self.total_input_tokens:,} tokens | "
            f"Output: {self.total_output_tokens:,} tokens"
        )
