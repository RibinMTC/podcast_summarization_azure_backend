import json
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class BaseResponse:
    """Base response model."""

    status: str
    message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {"status": self.status}
        if self.message is not None:
            result["message"] = self.message
        return result

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())


@dataclass
class SuccessResponse(BaseResponse):
    """Success response model."""

    status: str = "success"
    data: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with data if present."""
        result = super().to_dict()
        if self.data is not None:
            result["data"] = self.data
        return result


@dataclass
class ErrorResponse(BaseResponse):
    """Error response model."""

    status: str = "error"
