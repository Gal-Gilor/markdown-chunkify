import json
import os

from google import genai
from google.genai import types
from jinja2 import Template
from tenacity import retry
from tenacity import stop_after_attempt
from tenacity import wait_random_exponential
from vertexai.generative_models import GenerationResponse

from markdown_chunkify.core.interfaces import BaseProcessor
from markdown_chunkify.core.models import MarkdownContent
from markdown_chunkify.core.models import Section
from markdown_chunkify.core.models import SectionMetadata
from markdown_chunkify.core.settings import DEFAULT_RETRY_CONFIG
from markdown_chunkify.core.settings import RetryConfig
from markdown_chunkify.core.settings import logger

# Set up the path and load the prompt template
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROMPT_TEMPLATES_DIR = os.path.join(ROOT_DIR, "core/prompt_templates")
UNICODE_REPLACE_TEMPLATE_PATH = os.path.join(PROMPT_TEMPLATES_DIR, "unicode_replace.txt")

#  Load the template file
with open(os.path.join(UNICODE_REPLACE_TEMPLATE_PATH)) as f:
    UNICODE_REPLACE_TEMPLATE = Template(f.read())

# Define the default generation configuration
DEFAULT_GENERATION_CONFIG = types.GenerateContentConfig(
    safety_settings=[
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
            threshold=types.HarmBlockThreshold.BLOCK_NONE,
        ),
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
            threshold=types.HarmBlockThreshold.BLOCK_NONE,
        ),
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
            threshold=types.HarmBlockThreshold.BLOCK_NONE,
        ),
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
            threshold=types.HarmBlockThreshold.BLOCK_NONE,
        ),
    ],
    response_mime_type="application/json",
    response_schema=MarkdownContent,
)


class UnicodeReplaceProcessor(BaseProcessor):
    """A Gemini powered class to process Markdown text."""

    def __init__(
        self,
        client: genai.Client,
        generation_config: types.GenerateContentConfig | None = None,
        instructions: str | None = None,
        retry_config: RetryConfig | None = None,
    ):
        """Initialize the UnicodeReplaceProcessor.

        Args:
            model (genai.GenerativeModel): A GenerativeModel instance.
            generation_config (types.GenerateContentConfig): GenerationConfig instance.
            instructions: A Jinja2 template string.
            retry_config (RetryConfig): RetryConfig instance.
                The default is settings, defined in DEFAULT_RETRY_CONFIG:
                - attempts (stop_after_attempt): 3
                - multiplier (wait_random_exponential): 1.0
                - max_wait (wait_random_exponential): 10.0
                - retry_error_callback: lambda state: state.outcome.result()
        """
        self.client = client
        self.generation_config = generation_config or DEFAULT_GENERATION_CONFIG
        self.instructions = instructions or UNICODE_REPLACE_TEMPLATE
        self.retry_config = retry_config or DEFAULT_RETRY_CONFIG

    @property
    def _retry_settings(self):
        """A property to configure the retry mechanism, returning a tenacity retry decorator."""
        return retry(
            stop=stop_after_attempt(self.retry_config.attempts),
            wait=wait_random_exponential(
                multiplier=self.retry_config.multiplier, max=self.retry_config.max_wait
            ),
            retry_error_callback=self.retry_config.retry_error_callback,
        )

    def process_text(self, section: Section) -> Section:
        """Wrapper method to normalize Unicode characters in Markdown.

        Args:
            section (Section): A Section instance.

        Returns:
            Section: A new section with normalized Unicode characters.
        """
        logger.debug(
            f"Replacing Unicode characters with their ASCII equivalents in section: {section.section_header}"
        )
        return self._retry_settings(self._normalize_unicode)(section)

    def _normalize_unicode(self, section: Section) -> Section:
        """Normalize Unicode characters in Markdown.

        Args:
            section (Section): A Section instance.

        Returns:
            Section: A new section with normalized Unicode characters.
                Or, the original section if normalization fails.
        """
        try:
            md_content = section.to_markdown()
            logger.debug(
                f"Attempting to normalize section of length: {len(md_content)} characters"
            )

            normalization_response = self.client.models.generate_content(
                model=os.getenv("GOOGLE_GEMINI_MODEL", "gemini-2.0-flash"),
                contents=[self.instructions.render(section_content=md_content)],
                config=self.generation_config,
            )
            logger.debug("Successfully received response from Gemini API")

            return self._create_normalized_section(normalization_response, section)

        except Exception as e:
            logger.error(
                f"Failed to normalize section: {section.section_header}. Error: {str(e)}",
                exc_info=True,
            )
            section.metadata.error = str(e)

            return section

    def _create_normalized_section(
        self, generation_response: GenerationResponse, original_section: Section
    ) -> Section:
        """Create a normalized section from API response.

        Args:
            generation_response (GenerationResponse): A GenerationResponse instance
            original_section (Section): The original section to be normalized

        Returns:
            MarkdownSection: A new section with normalized content and metadata
        """
        try:
            response_text = json.loads(generation_response.text)
            response_obj = generation_response.to_json_dict()
            response_usage = response_obj.get("usage_metadata", {})
            token_count = response_usage.get("candidates_token_count", 0)

            logger.info(
                f"Successfully replaced the Unicode characters in section: {original_section.section_header}"
            )

            return Section(
                section_header=response_text["section_header"],
                section_text=response_text["section_text"],
                header_level=original_section.header_level,
                metadata=SectionMetadata(
                    token_count=token_count,
                    model_version=response_obj.get("model_version"),
                    normalized=True,
                    original_content=MarkdownContent(
                        section_header=original_section.section_header,
                        section_text=original_section.section_text,
                    ),
                    parents=original_section.metadata.parents,
                ),
            )

        except Exception as e:
            logger.warning(
                f"Skipped {original_section.section_header}. Failed to replace Unicode characters. Error: {str(e)}",
                exc_info=True,
            )
            original_section.metadata.error = str(e)

            return original_section
