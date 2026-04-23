from __future__ import annotations

import asyncio
import os
from typing import Any

from demo_app.broker.rabbit import RabbitBroker
from demo_app.models.messages import (
    CommandMessage,
    ErrorMessage,
    PackageData,
    ProgressMessage,
    UiEvent,
)

broker = RabbitBroker()
PARSER_STEP_DELAY_SEC = float(os.getenv("PARSER_STEP_DELAY_SEC", "5"))


async def _emit_progress(package_id: str, progress: int, message: str) -> None:
    msg = ProgressMessage.new(
        package_id=package_id,
        stage="parse",
        progress=progress,
        status="running" if progress < 100 else "completed",
        message=message,
    )
    event = UiEvent.new("event.package.progress", package_id, msg.to_json())
    await broker.publish_event("event.package.progress", event.to_json())


def _simulate_parse(data: PackageData) -> PackageData:
    # Same deterministic schema as input; only values are normalized.
    return PackageData(
        application_date=data.application_date,
        plaintiff_name=data.plaintiff_name.strip().upper(),
        defendant_name=data.defendant_name.strip().upper(),
        claim_amount=round(data.claim_amount, 2),
        files=data.files,
        notes=f"PARSED: {data.notes.strip()}",
    )


async def _handle_command(raw: dict[str, Any]) -> None:
    try:
        print("[parser] Command received")
        command = CommandMessage.from_json(raw)
        if command.type != "parse":
            print(f"[parser] Skip command type={command.type}")
            return

        print(f"[parser] Start parse package_id={command.package_id}")
        await _emit_progress(command.package_id, 10, "Parser: получена команда")
        await asyncio.sleep(PARSER_STEP_DELAY_SEC)
        print(f"[parser] package_id={command.package_id} progress=40")
        await _emit_progress(
            command.package_id, 40, "Parser: имитация чтения файлов"
        )
        await asyncio.sleep(PARSER_STEP_DELAY_SEC)
        parsed = _simulate_parse(command.payload)
        print(f"[parser] package_id={command.package_id} progress=70")
        await _emit_progress(
            command.package_id, 70, "Parser: подготовка JSON результата"
        )
        await asyncio.sleep(PARSER_STEP_DELAY_SEC)
        await _emit_progress(command.package_id, 100, "Parser: завершено")
        print(f"[parser] package_id={command.package_id} progress=100")
        parsed_event = UiEvent.new(
            "event.package.parsed",
            command.package_id,
            {"parsed_data": parsed.to_json()},
        )
        await broker.publish_event("event.package.parsed", parsed_event.to_json())
        print(f"[parser] Parsed event published package_id={command.package_id}")
    except Exception as exc:
        package_id = str(raw.get("package_id", "unknown"))
        print(f"[parser] ERROR package_id={package_id}: {exc}")
        err = ErrorMessage.new(
            package_id=package_id,
            code="PARSER_FAILURE",
            message=str(exc),
        )
        event = UiEvent.new("event.package.failed", package_id, err.to_json())
        await broker.publish_event("event.package.failed", event.to_json())


async def run() -> None:
    print("[parser] Worker is starting...")
    await broker.connect()
    print("[parser] Connected to RabbitMQ")
    await broker.consume_commands(
        queue_name="worker.parser.commands",
        binding_key="command.package.parse",
        handler=_handle_command,
    )
    print("[parser] Waiting for commands in worker.parser.commands")
    await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(run())
