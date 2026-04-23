from __future__ import annotations

import json
import os
from collections.abc import Awaitable, Callable
from typing import Any

import aio_pika
from aio_pika import ExchangeType, IncomingMessage


RABBIT_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@127.0.0.1:5672/")
COMMAND_EXCHANGE = "demo.commands"
EVENT_EXCHANGE = "demo.events"


class RabbitBroker:
    def __init__(self, url: str = RABBIT_URL) -> None:
        self.url = url
        self._connection: aio_pika.RobustConnection | None = None
        self._channel: aio_pika.abc.AbstractRobustChannel | None = None
        self._cmd_exchange: aio_pika.abc.AbstractRobustExchange | None = None
        self._event_exchange: aio_pika.abc.AbstractRobustExchange | None = None

    async def connect(self) -> None:
        if self._connection is not None:
            return
        self._connection = await aio_pika.connect_robust(self.url)
        self._channel = await self._connection.channel()
        await self._channel.set_qos(prefetch_count=1)
        self._cmd_exchange = await self._channel.declare_exchange(COMMAND_EXCHANGE, ExchangeType.TOPIC, durable=True)
        self._event_exchange = await self._channel.declare_exchange(EVENT_EXCHANGE, ExchangeType.TOPIC, durable=True)

    async def close(self) -> None:
        if self._connection is not None:
            await self._connection.close()
            self._connection = None

    async def publish_command(self, routing_key: str, payload: dict[str, Any]) -> None:
        await self.connect()
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        assert self._cmd_exchange is not None
        await self._cmd_exchange.publish(aio_pika.Message(body=body, delivery_mode=aio_pika.DeliveryMode.PERSISTENT), routing_key)

    async def publish_event(self, routing_key: str, payload: dict[str, Any]) -> None:
        await self.connect()
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        assert self._event_exchange is not None
        await self._event_exchange.publish(aio_pika.Message(body=body, delivery_mode=aio_pika.DeliveryMode.PERSISTENT), routing_key)

    async def consume_commands(
        self,
        queue_name: str,
        binding_key: str,
        handler: Callable[[dict[str, Any]], Awaitable[None]],
    ) -> None:
        await self.connect()
        assert self._channel is not None
        assert self._cmd_exchange is not None
        queue = await self._channel.declare_queue(queue_name, durable=True)
        await queue.bind(self._cmd_exchange, routing_key=binding_key)

        async def _on_message(msg: IncomingMessage) -> None:
            async with msg.process():
                data = json.loads(msg.body.decode("utf-8"))
                await handler(data)

        await queue.consume(_on_message)

    async def consume_events(
        self,
        queue_name: str,
        binding_key: str,
        handler: Callable[[dict[str, Any]], Awaitable[None]],
    ) -> None:
        await self.connect()
        assert self._channel is not None
        assert self._event_exchange is not None
        queue = await self._channel.declare_queue(queue_name, durable=True)
        await queue.bind(self._event_exchange, routing_key=binding_key)

        async def _on_message(msg: IncomingMessage) -> None:
            async with msg.process():
                data = json.loads(msg.body.decode("utf-8"))
                await handler(data)

        await queue.consume(_on_message)
