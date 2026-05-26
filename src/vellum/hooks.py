class HooksMixin:

    async def before_insert(self) -> None:
        """Called before a document is inserted. Raise to cancel the insert."""

    async def after_insert(self) -> None:
        """Called after a document has been inserted successfully."""

    async def before_update(self) -> None:
        """Called before a document is updated. Raise to cancel the update."""

    async def after_update(self) -> None:
        """Called after a document has been updated successfully."""

    async def before_delete(self) -> None:
        """Called before a document is deleted. Raise to cancel the delete."""

    async def after_delete(self) -> None:
        """Called after a document has been deleted successfully."""
