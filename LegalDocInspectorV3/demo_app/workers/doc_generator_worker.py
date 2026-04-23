from __future__ import annotations

import asyncio
from typing import Any

from demo_app.broker.rabbit import RabbitBroker
from demo_app.models.messages import (
    CommandMessage,
    ErrorMessage,
    ProgressMessage,
    ResultMessage,
    UiEvent,
)

broker = RabbitBroker()


async def _emit_progress(package_id: str, progress: int, message: str) -> None:
    msg = ProgressMessage.new(
        package_id=package_id,
        stage="generate",
        progress=progress,
        status="running" if progress < 100 else "completed",
        message=message,
    )
    event = UiEvent.new("event.package.progress", package_id, msg.to_json())
    await broker.publish_event("event.package.progress", event.to_json())


async def _handle_command(raw: dict[str, Any]) -> None:
    try:
        print("[generator] Command received")
        command = CommandMessage.from_json(raw)
        if command.type != "generate":
            print(f"[generator] Skip command type={command.type}")
            return

        print(f"[generator] Start generation package_id={command.package_id}")
        await _emit_progress(
            command.package_id, 10, "Generator: получена команда"
        )
        await asyncio.sleep(2)
        print(f"[generator] package_id={command.package_id} progress=40")
        await _emit_progress(
            command.package_id, 40, "Generator: формирование шаблона"
        )
        await asyncio.sleep(2)
        print(f"[generator] package_id={command.package_id} progress=70")
        await _emit_progress(
            command.package_id, 70, "Generator: сборка артефактов"
        )
        await asyncio.sleep(2)
        await _emit_progress(command.package_id, 100, "Generator: завершено")
        print(f"[generator] package_id={command.package_id} progress=100")

        result = ResultMessage.new(
            package_id=command.package_id,
            status="documents_ready",
            artifacts=[
                f"claim_{command.package_id}.docx",
                f"calculation_{command.package_id}.docx",
            ],
        )
        event = UiEvent.new(
            "event.package.completed",
            command.package_id,
            result.to_json(),
        )
        await broker.publish_event("event.package.completed", event.to_json())
        print(
            f"[generator] Completed event published package_id={command.package_id}"
        )
    except Exception as exc:
        package_id = str(raw.get("package_id", "unknown"))
        print(f"[generator] ERROR package_id={package_id}: {exc}")
        err = ErrorMessage.new(
            package_id=package_id,
            code="GENERATOR_FAILURE",
            message=str(exc),
        )
        event = UiEvent.new("event.package.failed", package_id, err.to_json())
        await broker.publish_event("event.package.failed", event.to_json())


async def run() -> None:
    print("[generator] Worker is starting...")
    await broker.connect()
    print("[generator] Connected to RabbitMQ")
    await broker.consume_commands(
        queue_name="worker.generator.commands",
        binding_key="command.package.generate",
        handler=_handle_command,
    )
    print("[generator] Waiting for commands in worker.generator.commands")
    await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(run())
