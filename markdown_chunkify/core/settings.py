import logging
from typing import Any
from typing import Callable

from pydantic import BaseModel
from pydantic import Field
from tenacity import RetryCallState


class RetryConfig(BaseModel):
    """Configuration settings for retry behavior using tenacity's random exponential backoff strategy.

    Attributes:
        attempts (int): Maximum number of retry attempts before giving up. Default is 3.
        multiplier (float): Base multiplier for tenacity's wait_random_exponential strategy.
            Wait time between retries will be random between [0, min(multiplier * 2^(attempt), max_wait)].
            Default is 1.0.
        max_wait (float): Maximum wait time between retries (seconds). Default is 10.0.
    """

    attempts: int = Field(
        3,
        ge=1,
        description="Maximum number of retry attempts before giving up",
    )
    multiplier: float = Field(
        default=1.0,
        gt=0,
        description=("Base multiplier for tenacity's wait_random_exponential strategy."),
    )
    max_wait: float = Field(
        10.0,
        gt=0,
        description=(
            "Maximum wait time in seconds between retries, regardless of the exponential backoff calculation."
        ),
    )
    retry_error_callback: Callable[[RetryCallState], Any] | None = Field(
        default=lambda state: state.outcome.result(),
        description=("Optional callback function called when all retries have failed."),
    )

    class ConfigDict:
        description = "Retry configuration settings using tenacity's random exponential backoff strategy."

        json_schema_extra = {
            "examples": [
                {
                    "attempts": 5,
                    "multiplier": 2.0,
                    "max_wait": 15.0,
                    "retry_error_callback": "lambda state: state.outcome.result()",
                }
            ]
        }


DEFAULT_RETRY_CONFIG = RetryConfig()


def initialize_logger() -> logging.Logger:
    """Initialize a custom formatted logger."""

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s.%(msecs)02d - %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    logger = logging.getLogger("markdown_chunkify")
    logger.addHandler(logging.NullHandler())

    return logger


logger = initialize_logger()
