"""
Product catalog use case

Handles product browsing, search, and information retrieval.
"""

import logging
from dataclasses import dataclass

from src.domain.repositories.product_repository import ProductRepository
from src.domain.value_objects.product_id import ProductId
from src.domain.value_objects.product_name import ProductName
from src.infrastructure.utilities.helpers import is_hilbeh_available

logger = logging.getLogger(__name__)


@dataclass
class ProductCatalogRequest:
    """Request for product catalog operations"""

    category: str | None = None
    search_term: str | None = None
    product_id: int | None = None
    product_name: str | None = None


@dataclass
class ProductInfo:
    """Product information response"""

    id: int
    name: str
    description: str
    base_price: float
    category: str
    is_active: bool
    options: dict | None = None


@dataclass
class ProductCatalogResponse:
    """Response for product catalog operations"""

    success: bool
    products: list[ProductInfo] | None = None
    product: ProductInfo | None = None
    error_message: str | None = None


class ProductCatalogUseCase:
    """
    Use case for product catalog operations

    Handles:
    1. Product listing by category
    2. Product search
    3. Product details retrieval
    4. Availability checking
    """

    def __init__(self, product_repository: ProductRepository):
        self._product_repository = product_repository
        self._logger = logging.getLogger(self.__class__.__name__)

    async def get_products_by_category(
        self, request: ProductCatalogRequest
    ) -> ProductCatalogResponse:
        """Get all products in a specific category"""
        try:
            if not request.category:
                return ProductCatalogResponse(
                    success=False, error_message="Category is required"
                )

            products = await self._product_repository.find_by_category(request.category)
            product_infos = [
                self._map_to_product_info(p) for p in products if p.is_active
            ]

            return ProductCatalogResponse(success=True, products=product_infos)

        except (ValueError, AttributeError) as e:
            self._logger.error(
                "Error getting products by category %s: %s", request.category, e
            )
            return ProductCatalogResponse(
                success=False, error_message="Failed to retrieve products"
            )

    async def get_product_by_name(
        self, request: ProductCatalogRequest
    ) -> ProductCatalogResponse:
        """Get a specific product by name"""
        try:
            if not request.product_name:
                return ProductCatalogResponse(
                    success=False, error_message="Product name is required"
                )

            product_name = ProductName(request.product_name)
            product = await self._product_repository.find_by_name(product_name)

            if not product:
                return ProductCatalogResponse(
                    success=False, error_message="Product not found"
                )

            if not product.is_active:
                return ProductCatalogResponse(
                    success=False, error_message="Product is currently unavailable"
                )

            return ProductCatalogResponse(
                success=True, product=self._map_to_product_info(product)
            )

        except ValueError as e:
            self._logger.error("Invalid product name %s: %s", request.product_name, e)
            return ProductCatalogResponse(
                success=False, error_message="Invalid product name"
            )
        except AttributeError as e:
            self._logger.error(
                "Error getting product by name %s: %s", request.product_name, e
            )
            return ProductCatalogResponse(
                success=False, error_message="Failed to retrieve product"
            )

    async def get_all_active_products(self) -> ProductCatalogResponse:
        """Get all active products"""
        try:
            products = await self._product_repository.find_all_active()
            product_infos = [self._map_to_product_info(p) for p in products]

            return ProductCatalogResponse(success=True, products=product_infos)

        except (ValueError, AttributeError) as e:
            self._logger.error("Error getting all active products: %s", e)
            return ProductCatalogResponse(
                success=False, error_message="Failed to retrieve products"
            )

    async def check_availability(
        self, request: ProductCatalogRequest
    ) -> ProductCatalogResponse:
        """Check if a product is available"""
        try:
            if request.product_name:
                product_name = ProductName(request.product_name)
                product = await self._product_repository.find_by_name(product_name)
            elif request.product_id:
                product_id = ProductId(request.product_id)
                product = await self._product_repository.find_by_id(product_id)
            else:
                return ProductCatalogResponse(
                    success=False, error_message="Product name or ID is required"
                )

            if not product:
                return ProductCatalogResponse(
                    success=False, error_message="Product not found"
                )

            # Special handling for time-sensitive products like Hilbeh
            if product.name.lower() == "hilbeh":
                if not is_hilbeh_available():
                    return ProductCatalogResponse(
                        success=False,
                        error_message="Hilbeh is only available on specific days",
                    )

            return ProductCatalogResponse(
                success=True, product=self._map_to_product_info(product)
            )

        except (ValueError, AttributeError) as e:
            self._logger.error("Error checking availability: %s", e)
            return ProductCatalogResponse(
                success=False, error_message="Failed to check availability"
            )

    def _map_to_product_info(self, product) -> ProductInfo:
        """Map domain product to response DTO"""
        return ProductInfo(
            id=product.id,
            name=product.name,
            description=product.description or "",
            base_price=product.base_price,
            category=product.category,
            is_active=product.is_active,
            options=product.options,
        )
