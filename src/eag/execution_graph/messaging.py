"""Worker messaging system for EAG."""

from eag.execution_graph.models import WorkerMessage


class Mailbox:
    """A simple mailbox for receiving messages."""

    def __init__(self) -> None:
        self._messages: list[WorkerMessage] = []

    def receive(self, message: WorkerMessage) -> None:
        self._messages.append(message)

    def read_all(self) -> tuple[WorkerMessage, ...]:
        return tuple(self._messages)

    def clear(self) -> None:
        self._messages.clear()


class MessageRouter:
    """Routes messages between workers via their mailboxes."""

    def __init__(self) -> None:
        self._mailboxes: dict[str, Mailbox] = {}

    def register(self, worker_id: str) -> None:
        if worker_id not in self._mailboxes:
            self._mailboxes[worker_id] = Mailbox()

    def route(self, message: WorkerMessage) -> None:
        if message.receiver_id not in self._mailboxes:
            raise ValueError(f"Receiver '{message.receiver_id}' not registered")
        self._mailboxes[message.receiver_id].receive(message)

    def get_mailbox(self, worker_id: str) -> Mailbox:
        if worker_id not in self._mailboxes:
            raise ValueError(f"Worker '{worker_id}' not registered")
        return self._mailboxes[worker_id]
