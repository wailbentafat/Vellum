from __future__ import annotations

import datetime
from typing import Any

from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from vellum.model import SoftDeleteMixin, VellumBaseModel


class DocIssue(BaseModel):
    doc_id: str
    field: str
    issue_type: str
    message: str


class RepairAction(BaseModel):
    doc_id: str
    action: str
    field: str
    detail: str


class CheckReport(BaseModel):
    total: int = 0
    ok: int = 0
    issues: list[DocIssue] = Field(default_factory=list)

    @property
    def issue_count(self) -> int:
        return len(self.issues)

    def __str__(self) -> str:
        return f"Checked {self.total} docs: {self.ok} ok, {self.issue_count} issues"


class RepairReport(BaseModel):
    total_processed: int = 0
    actions: list[RepairAction] = Field(default_factory=list)

    @property
    def action_count(self) -> int:
        return len(self.actions)


class SchemaDoctor[T: VellumBaseModel]:

    def __init__(self, model_cls: type[T], database: AsyncIOMotorDatabase) -> None:
        self.model_cls = model_cls
        self.collection: AsyncIOMotorCollection = database[model_cls.get_collection_name()]

    def _expected_fields(self) -> dict[str, Any]:
        fields: dict[str, Any] = {}
        for name, info in self.model_cls.model_fields.items():
            alias = info.alias or name
            fields[alias] = info.annotation
        return fields

    def _check_field(
        self, doc: dict[str, Any], field: str, expected_type: Any
    ) -> list[DocIssue]:
        issues: list[DocIssue] = []
        doc_id = str(doc.get("_id", "unknown"))

        if field not in doc:
            issues.append(DocIssue(
                doc_id=doc_id,
                field=field,
                issue_type="missing",
                message=f"Missing field '{field}'",
            ))
            return issues

        return issues

    def _check_doc(self, doc: dict[str, Any]) -> list[DocIssue]:
        issues: list[DocIssue] = []
        doc_id = str(doc.get("_id", "unknown"))
        expected = self._expected_fields()

        for field_name in expected:
            issues.extend(self._check_field(doc, field_name, expected[field_name]))

        for field_name in doc:
            if field_name.startswith("_"):
                continue
            if field_name not in expected and field_name not in ("deleted_at", "version"):
                issues.append(DocIssue(
                    doc_id=doc_id,
                    field=field_name,
                    issue_type="unexpected",
                    message=f"Unexpected field '{field_name}' not in model",
                ))

        return issues

    async def check(self, include_deleted: bool = False) -> CheckReport:
        report = CheckReport()
        query: dict[str, Any] = {}
        if issubclass(self.model_cls, SoftDeleteMixin) and not include_deleted:
            query["deleted_at"] = None

        cursor = self.collection.find(query)
        async for doc in cursor:
            report.total += 1
            doc_issues = self._check_doc(doc)
            if doc_issues:
                report.issues.extend(doc_issues)
            else:
                report.ok += 1
        return report

    async def summarize(self, include_deleted: bool = False) -> dict[str, Any]:
        report = await self.check(include_deleted=include_deleted)
        by_type: dict[str, int] = {}
        for issue in report.issues:
            by_type[issue.issue_type] = by_type.get(issue.issue_type, 0) + 1
        return {
            "total": report.total,
            "ok": report.ok,
            "issue_count": report.issue_count,
            "by_type": by_type,
        }

    async def repair(
        self,
        include_deleted: bool = False,
        dry_run: bool = False,
    ) -> RepairReport:
        report = RepairReport()
        expected = self._expected_fields()
        query: dict[str, Any] = {}
        if issubclass(self.model_cls, SoftDeleteMixin) and not include_deleted:
            query["deleted_at"] = None

        now = datetime.datetime.now(datetime.UTC)
        cursor = self.collection.find(query)

        async for doc in cursor:
            report.total_processed += 1
            doc_id = str(doc["_id"])
            update: dict[str, Any] = {}
            unset: dict[str, Any] = {}

            for field_name in expected:
                if field_name not in doc:
                    default = None
                    info = self.model_cls.model_fields.get(field_name)
                    if info and info.default is not None:
                        default = info.default
                    elif info and info.default_factory is not None:
                        default = info.default_factory()
                    if default is not None:
                        update[field_name] = default
                        report.actions.append(RepairAction(
                            doc_id=doc_id,
                            action="set_default",
                            field=field_name,
                            detail=f"Set to default: {default!r}",
                        ))

            for field_name in doc:
                if field_name.startswith("_"):
                    continue
                if field_name not in expected and field_name not in ("deleted_at", "version"):
                    unset[field_name] = ""
                    report.actions.append(RepairAction(
                        doc_id=doc_id,
                        action="unset",
                        field=field_name,
                        detail="Removed unexpected field",
                    ))

            if update or unset:
                ops: dict[str, Any] = {}
                if update:
                    update["updated_at"] = now
                    ops["$set"] = update
                if unset:
                    ops["$unset"] = unset
                if not dry_run:
                    await self.collection.update_one({"_id": doc["_id"]}, ops)

        return report

    async def field_map(
        self,
        old: str,
        new: str,
        include_deleted: bool = False,
        dry_run: bool = False,
    ) -> int:
        query: dict[str, Any] = {old: {"$exists": True}}
        if issubclass(self.model_cls, SoftDeleteMixin) and not include_deleted:
            query["deleted_at"] = None

        count = await self.collection.count_documents(query)
        if not dry_run:
            await self.collection.update_many(
                query,
                {"$rename": {old: new}},
            )
        return count

    async def field_drop(
        self,
        field: str,
        include_deleted: bool = False,
        dry_run: bool = False,
    ) -> int:
        query: dict[str, Any] = {field: {"$exists": True}}
        if issubclass(self.model_cls, SoftDeleteMixin) and not include_deleted:
            query["deleted_at"] = None

        count = await self.collection.count_documents(query)
        if not dry_run:
            await self.collection.update_many(
                query,
                {"$unset": {field: ""}},
            )
        return count
