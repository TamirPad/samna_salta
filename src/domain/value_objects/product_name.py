"""Product Name value object"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ProductName:
    """Product name value object"""

    value: str

    def __post_init__(self):
        if not self.value or not self.value.strip():
            raise ValueError("Product name cannot be empty")

        cleaned_name = self.value.strip()
        if len(cleaned_name) < 2:
            raise ValueError("Product name must be at least 2 characters")
        if len(cleaned_name) > 100:
            raise ValueError("Product name cannot exceed 100 characters")

        object.__setattr__(self, "value", cleaned_name)

    def __str__(self) -> str:
        return self.value
