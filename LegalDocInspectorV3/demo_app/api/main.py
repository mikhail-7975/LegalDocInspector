from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import Body, FastAPI, HTTPException, Query

from demo_app.broker.rabbit import RabbitBroker
from demo_app.models.messages import (
    CommandMessage,
    PackageData,
    UiEvent,
)
from demo_app.state.store import store

app = FastAPI(title="LegalDocInspector V3 Demo")
broker = RabbitBroker()


async def _event_handler(payload: dict[str, Any]) -> None:
    event = UiEvent.from_json(payload)
    store.add_event(event)
    if event.event_type == "event.package.parsed":
        data = PackageData.from_json(event.data["parsed_data"])
        store.set_parsed_data(event.package_id, data)
    if event.event_type == "event.package.completed":
        store.mark_generated(event.package_id)


@app.on_event("startup")
async def startup() -> None:
    await broker.connect()
    await broker.consume_events(
        queue_name="bff.events.ui",
        binding_key="event.package.*",
        handler=_event_handler,
    )


@app.on_event("shutdown")
async def shutdown() -> None:
    await broker.close()


@app.get("/api/v1/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/v1/packages")
async def create_package() -> dict[str, str]:
    package_id = str(uuid4())
    store.create_package(package_id)
    store.add_event(UiEvent.new("event.package.created", package_id, {"state": "created"}))
    return {"package_id": package_id}


@app.post("/api/v1/packages/{package_id}/parse")
async def parse_package(package_id: str, body: dict[str, Any] = Body(...)) -> dict[str, str]:
    try:
        store.ensure_package(package_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    try:
        payload = PackageData.from_json(body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    command = CommandMessage.new("parse", package_id, payload)
    await broker.publish_command("command.package.parse", command.to_json())
    return {"status": "accepted", "package_id": package_id}


@app.get("/api/v1/packages/{package_id}/parsed")
async def get_parsed(package_id: str) -> dict[str, Any]:
    try:
        rec = store.ensure_package(package_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if rec.parsed_data is None:
        raise HTTPException(status_code=409, detail="Parsed data is not ready yet")
    return rec.parsed_data.to_json()


@app.post("/api/v1/packages/{package_id}/generate")
async def generate_docs(package_id: str, body: dict[str, Any] = Body(...)) -> dict[str, str]:
    try:
        rec = store.ensure_package(package_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if rec.parsed_data is None:
        raise HTTPException(status_code=409, detail="Parse stage must be completed first")
    try:
        payload = PackageData.from_json(body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    command = CommandMessage.new("generate", package_id, payload)
    await broker.publish_command("command.package.generate", command.to_json())
    return {"status": "accepted", "package_id": package_id}


@app.get("/api/v1/packages/{package_id}/events")
async def get_events(package_id: str, since: int = Query(default=0, ge=0)) -> dict[str, Any]:
    try:
        events = store.get_events(package_id, since)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"events": events, "next_offset": since + len(events)}
