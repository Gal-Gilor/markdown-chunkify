import json
import os

from jinja2 import Template
from vertexai.generative_models import GenerationConfig
from vertexai.generative_models import GenerativeModel
from vertexai.generative_models import HarmBlockThreshold
from vertexai.generative_models import HarmCategory
from vertexai.generative_models import SafetySetting

from markdown_chunkify.core.interfaces import BaseNormalizer
from markdown_chunkify.core.models import MarkdownSection
from markdown_chunkify.core.models import NormalizedSection

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROMPT_TEMPLATES_DIR = os.path.join(ROOT_DIR, "core/prompt_templates")
UNICODE_REPLACE_TEMPLATE_PATH = os.path.join(PROMPT_TEMPLATES_DIR, "unicode_replace.txt")

#  Load the template file
with open(os.path.join(UNICODE_REPLACE_TEMPLATE_PATH)) as f:
    UNICODE_REPLACE_TEMPLATE = Template(f.read())

# Safety config
DEFAULT_SAFETY_SETTINGS = [
    SafetySetting(
        category=HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
        threshold=HarmBlockThreshold.BLOCK_NONE,
    ),
    SafetySetting(
        category=HarmCategory.HARM_CATEGORY_HARASSMENT,
        threshold=HarmBlockThreshold.BLOCK_NONE,
    ),
    SafetySetting(
        category=HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
        threshold=HarmBlockThreshold.BLOCK_NONE,
    ),
    SafetySetting(
        category=HarmCategory.HARM_CATEGORY_HATE_SPEECH,
        threshold=HarmBlockThreshold.BLOCK_NONE,
    ),
]


DEFAULT_GENERATION_CONFIG = GenerationConfig(
    response_mime_type="application/json",
    response_schema=NormalizedSection.model_json_schema(),
)


class GeminiNormalizer(BaseNormalizer):
    """A text normalizer class powered by Gemini."""

    def __init__(
        self,
        model: GenerativeModel,
        generation_config: GenerationConfig | None = None,
        saftey_setting: list[SafetySetting] | None = None,
        instructions: str | None = None,
    ):
        """Initialize the normalizer.

        Args:
            model: A model instance
            generation_config: GenerationConfig instance
            saftey_settings: SafetySettings instance
        """
        self.model = model
        self.generation_config = generation_config or DEFAULT_GENERATION_CONFIG
        self.safety_settings = saftey_setting or DEFAULT_SAFETY_SETTINGS
        self.instructions = instructions or UNICODE_REPLACE_TEMPLATE

    def normalize_unicode(self, section: MarkdownSection) -> MarkdownSection:
        """Normalize Unicode characters in Markdown.

        Args:
            section: A MarkdownSection instance

        Returns:
            A MarkdownSection instance with normalized Unicode characters.
        """
        try:
            md_content = section.to_markdown()
            normalization_response = self.model.generate_content(
                self.instructions.render(section_content=md_content),
                generation_config=self.generation_config,
                safety_settings=self.safety_settings,
            )

            response_text = json.loads(normalization_response.text)
            response_obj = normalization_response.to_dict()

            return {
                "section_header": response_text["section_header"],
                "section_text": response_text["section_text"],
                "metadata": {
                    "token_count": response_obj["usage_metadata"]["candidates_token_count"],
                    "model_version": response_obj["model_version"],
                    "normalized": True,
                    "original_content": {
                        "section_header": section.section_header,
                        "section_text": section.section_text,
                    },
                },
            }

        except Exception as e:
            section = {
                "section_header": section.section_header,
                "section_text": section.section_text,
                "metadata": {"normalized": False, "error": str(e)},
            }

            if "normalization_response" in locals():
                section["metadata"]["normalization_response"] = normalization_response.text

            return section
