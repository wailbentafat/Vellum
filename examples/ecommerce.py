"""
Vellum e-commerce example — demonstrates all type-safe features.

Requires a running MongoDB instance (mongodb://localhost:27017).
"""

import asyncio

from motor.motor_asyncio import AsyncIOMotorClient

from vellum import (
    AggregationPipeline,
    Index,
    OptimisticConcurrencyMixin,
    SoftDeleteMixin,
    SortSpec,
    VellumBaseModel,
    VellumRepository,
)


class Category(VellumBaseModel):
    name: str
    slug: str

    class Settings:
        collection_name = "categories"

    @classmethod
    def __init_indexes__(cls):
        return [
            Index(cls.slug, unique=True),
        ]


class Product(SoftDeleteMixin, VellumBaseModel):
    name: str
    price: float
    category: str
    tags: list[str] = []
    stock: int = 0

    class Settings:
        collection_name = "products"

    @classmethod
    def __init_indexes__(cls):
        return [
            Index(cls.name),
            Index(cls.category, cls.price),
            Index(cls.price),
            Index(cls.tags),
        ]


class Order(OptimisticConcurrencyMixin, VellumBaseModel):
    product_id: str
    quantity: int
    total: float

    class Settings:
        collection_name = "orders"


async def main():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["vellum_demo"]
    product_repo = VellumRepository(Product, db)
    order_repo = VellumRepository(Order, db)

    # Ensure indexes defined in Settings / __init_indexes__
    await product_repo.ensure_indexes()

    # --- Create ---
    laptop = await product_repo.create(
        Product(name="Laptop", price=1299.99, category="Electronics",
                tags=["computer", "portable"], stock=10)
    )
    phone = await product_repo.create(
        Product(name="Phone", price=799.99, category="Electronics",
                tags=["mobile", "5g"], stock=25)
    )
    shirt = await product_repo.create(
        Product(name="T-Shirt", price=29.99, category="Clothing",
                tags=["cotton"], stock=100)
    )
    print(f"Created: {laptop.name}, {phone.name}, {shirt.name}")

    # --- Type-safe queries ---
    electronics = await product_repo.find(
        (Product.category == "Electronics").to_mongo_query()
    )
    print(f"Electronics: {len(electronics)} products")

    cheap = await product_repo.find(
        (Product.price < 50).to_mongo_query()
    )
    print(f"Cheap (< $50): {len(cheap)} products")

    tagged = await product_repo.find(
        Product.tags.all_(["computer", "portable"]).to_mongo_query()
    )
    print(f"Tagged computer+portable: {len(tagged)} products")

    # --- Composed queries ---
    expensive_electronics = await product_repo.find(
        ((Product.category == "Electronics") & (Product.price > 1000)).to_mongo_query()
    )
    print(f"Expensive electronics: {len(expensive_electronics)} products")

    # --- Sorting ---
    sorted_products = await product_repo.find(sort=[Product.price.asc()])
    print(f"Cheapest product: {sorted_products[0].name} (${sorted_products[0].price})")

    sorted_desc = await product_repo.find(sort=[Product.price.desc()])
    print(f"Most expensive: {sorted_desc[0].name} (${sorted_desc[0].price})")

    # --- Pagination ---
    page1 = await product_repo.find(skip=0, limit=2)
    page2 = await product_repo.find(skip=2, limit=2)
    print(f"Page 1: {len(page1)} products, Page 2: {len(page2)} products")

    # --- Update ---
    laptop.stock = 8
    await product_repo.update(laptop.id, laptop)
    updated = await product_repo.get(laptop.id)
    print(f"Updated stock: {updated.stock} (was 10)")

    # --- UpdateBuilder ---
    from vellum import UpdateBuilder
    await (UpdateBuilder(product_repo.collection, phone.id)
        .inc(Product.stock, -1)
        .push(Product.tags, "sale")
        .execute()
    )
    refreshed = await product_repo.get(phone.id)
    print(f"Phone stock: {refreshed.stock} (was 25), tags: {refreshed.tags}")

    # --- Soft delete ---
    await product_repo.soft_delete(shirt.id)
    all_products = await product_repo.find()
    print(f"Products after soft delete: {len(all_products)} (2 visible)")

    await product_repo.restore(shirt.id)
    restored = await product_repo.get(shirt.id)
    print(f"Restored: {restored.name}")

    # --- Aggregation ---
    await order_repo.create(Order(
        product_id=str(laptop.id), quantity=2, total=2599.98
    ))
    await order_repo.create(Order(
        product_id=str(phone.id), quantity=5, total=3999.95
    ))
    await order_repo.create(Order(
        product_id=str(laptop.id), quantity=1, total=1299.99
    ))

    pipeline = AggregationPipeline(order_repo.collection)
    results = await (
        pipeline
        .group(Order.product_id, total_revenue={"$sum": Order.total})
        .sort(SortSpec("total_revenue", -1))
        .execute()
    )
    print(f"Top order: product={results[0]['_id']}, revenue=${results[0]['total_revenue']:.2f}")

    # --- Cleanup ---
    for coll in ["products", "orders"]:
        await db[coll].drop()
    client.close()
    print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
