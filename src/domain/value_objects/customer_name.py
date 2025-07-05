"""
Customer Name value object
"""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class CustomerName:
    """Customer name value object with validation"""

    value: str

    def __post_init__(self):
        """Validate customer name"""
        if not self.value or not self.value.strip():
            raise ValueError("Customer name cannot be empty")

        cleaned_name = self.value.strip()

        if len(cleaned_name) < 2:
            raise ValueError("Customer name must be at least 2 characters")

        if len(cleaned_name) > 100:
            raise ValueError("Customer name cannot exceed 100 characters")

        # Check that name contains at least some letters
        if not re.search(
            r"[a-zA-ZàáâäãåąčćęèéêëėįìíîïłńòóôöõøùúûüųūÿýżźñçčšžæÀÁÂÄÃÅĄĆČĖĘÈÉÊËÌÍÎÏĮŁŃÒÓÔÖÕØÙÚÛÜŲŪŸÝŻŹÑßÇŒÆČŠŽ\u0590-\u05FF\u0600-\u06FF]",
            cleaned_name,
        ):
            raise ValueError("Customer name must contain letters")

        # Use object.__setattr__ because the class is frozen
        object.__setattr__(self, "value", cleaned_name)

    def first_name(self) -> str:
        """Extract first name"""
        return self.value.split()[0] if self.value else ""

    def __str__(self) -> str:
        return self.value
