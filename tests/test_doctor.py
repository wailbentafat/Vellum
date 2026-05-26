from __future__ import annotations

import pytest
import pytest_asyncio

from vellum import VellumBaseModel, VellumRepository
from vellum.doctor import SchemaDoctor


class Patient(VellumBaseModel):
    name: str
    age: int = 0
    email: str | None = None

    class Settings:
        collection_name = "patients"


@pytest_asyncio.fixture
async def patient_repo(db):
    return VellumRepository(Patient, db)


@pytest_asyncio.fixture
async def doctor(db):
    return SchemaDoctor[Patient](Patient, db)


@pytest.mark.asyncio
async def test_check_no_issues(patient_repo, doctor):
    await patient_repo.create(Patient(name="Alice", age=30))
    report = await doctor.check()
    assert report.total == 1
    assert report.ok == 1
    assert report.issue_count == 0


@pytest.mark.asyncio
async def test_check_missing_field(patient_repo, doctor):
    patient = await patient_repo.create(Patient(name="Bob", age=25))
    await doctor.collection.update_one({"_id": str(patient.id)}, {"$unset": {"age": ""}})
    report = await doctor.check()
    assert report.total == 1
    assert report.ok == 0
    assert any(i.field == "age" and i.issue_type == "missing" for i in report.issues)


@pytest.mark.asyncio
async def test_check_unexpected_field(patient_repo, doctor):
    patient = await patient_repo.create(Patient(name="Charlie", age=35))
    await doctor.collection.update_one({"_id": str(patient.id)}, {"$set": {"rogue": "extra"}})
    report = await doctor.check()
    assert report.total == 1
    assert report.ok == 0
    assert any(i.field == "rogue" and i.issue_type == "unexpected" for i in report.issues)


@pytest.mark.asyncio
async def test_summarize(patient_repo, doctor):
    await patient_repo.create(Patient(name="Diana", age=40))
    summary = await doctor.summarize()
    assert summary["total"] == 1
    assert summary["ok"] == 1
    assert summary["issue_count"] == 0


@pytest.mark.asyncio
async def test_repair_missing_field_with_default(patient_repo, doctor):
    patient = await patient_repo.create(Patient(name="Eve", age=50))
    await doctor.collection.update_one({"_id": str(patient.id)}, {"$unset": {"age": ""}})
    report = await doctor.repair()
    assert report.total_processed == 1
    assert any(a.field == "age" and a.action == "set_default" for a in report.actions)
    repaired = await patient_repo.get(str(patient.id))
    assert repaired.age == 0


@pytest.mark.asyncio
async def test_repair_unexpected_field(patient_repo, doctor):
    patient = await patient_repo.create(Patient(name="Frank", age=60))
    await doctor.collection.update_one({"_id": str(patient.id)}, {"$set": {"rogue": "bad"}})
    report = await doctor.repair()
    assert any(a.field == "rogue" and a.action == "unset" for a in report.actions)
    doc = await doctor.collection.find_one({"_id": str(patient.id)})
    assert "rogue" not in doc


@pytest.mark.asyncio
async def test_repair_dry_run(patient_repo, doctor):
    patient = await patient_repo.create(Patient(name="Grace", age=70))
    await doctor.collection.update_one({"_id": str(patient.id)}, {"$unset": {"age": ""}})
    report = await doctor.repair(dry_run=True)
    assert report.total_processed == 1
    assert len(report.actions) > 0
    doc = await doctor.collection.find_one({"_id": str(patient.id)})
    assert "age" not in doc


@pytest.mark.asyncio
async def test_field_map(patient_repo, doctor):
    patient = await patient_repo.create(Patient(name="Heidi", age=80))
    await doctor.collection.update_one({"_id": str(patient.id)}, {"$set": {"old_name": "legacy"}})
    count = await doctor.field_map("old_name", "new_name")
    assert count == 1
    doc = await doctor.collection.find_one({"_id": str(patient.id)})
    assert "old_name" not in doc
    assert doc["new_name"] == "legacy"


@pytest.mark.asyncio
async def test_field_map_dry_run(patient_repo, doctor):
    patient = await patient_repo.create(Patient(name="Ivan", age=90))
    await doctor.collection.update_one({"_id": str(patient.id)}, {"$set": {"old_name": "legacy"}})
    count = await doctor.field_map("old_name", "new_name", dry_run=True)
    assert count == 1
    doc = await doctor.collection.find_one({"_id": str(patient.id)})
    assert "old_name" in doc
    assert "new_name" not in doc


@pytest.mark.asyncio
async def test_field_drop(patient_repo, doctor):
    patient = await patient_repo.create(Patient(name="Judy", age=100))
    await doctor.collection.update_one({"_id": str(patient.id)}, {"$set": {"obsolete": "bye"}})
    count = await doctor.field_drop("obsolete")
    assert count == 1
    doc = await doctor.collection.find_one({"_id": str(patient.id)})
    assert "obsolete" not in doc


@pytest.mark.asyncio
async def test_field_drop_dry_run(patient_repo, doctor):
    patient = await patient_repo.create(Patient(name="Karl", age=110))
    await doctor.collection.update_one({"_id": str(patient.id)}, {"$set": {"obsolete": "keep"}})
    count = await doctor.field_drop("obsolete", dry_run=True)
    assert count == 1
    doc = await doctor.collection.find_one({"_id": str(patient.id)})
    assert "obsolete" in doc
