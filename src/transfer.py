"""Chunked data transfer over MQTT for container migration.

Provides utilities for transferring large binary data (like container exports)
over MQTT by splitting into chunks and reassembling on the receiver side.
"""

import base64
import hashlib
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from uuid import uuid4

from commlib.msg import PubSubMessage, RPCMessage

# Configuration
CHUNK_SIZE = 64 * 1024  # 64KB chunks


class TransferStatus(Enum):
    """Status of a data transfer."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class TransferChunk(PubSubMessage):
    """A single chunk of data in a transfer."""

    transfer_id: str = ""
    chunk_index: int = 0
    total_chunks: int = 0
    data: str = ""  # base64 encoded
    checksum: str = ""  # SHA256 of this chunk's raw data


@dataclass
class TransferMetadata(PubSubMessage):
    """Metadata about a transfer, sent before chunks."""

    transfer_id: str = ""
    total_size: int = 0
    total_chunks: int = 0
    checksum: str = ""  # SHA256 of complete data
    content_type: str = "application/x-tar"


@dataclass
class TransferComplete(PubSubMessage):
    """Signal that transfer is complete."""

    transfer_id: str = ""
    success: bool = True
    message: str = ""


class InitiateTransferMessage(RPCMessage):
    """RPC message to initiate a transfer."""

    class Request(RPCMessage.Request):
        """Request to start receiving a transfer."""

        transfer_id: str = ""
        total_size: int = 0
        total_chunks: int = 0
        checksum: str = ""

    class Response(RPCMessage.Response):
        """Response confirming ready to receive."""

        ready: bool = True
        message: str = ""


class TransferResultMessage(RPCMessage):
    """RPC message to report transfer result."""

    class Request(RPCMessage.Request):
        """Report transfer completion."""

        transfer_id: str = ""
        success: bool = True
        message: str = ""

    class Response(RPCMessage.Response):
        """Acknowledge receipt of result."""

        acknowledged: bool = True


@dataclass
class TransferState:
    """Tracks state of an ongoing transfer."""

    transfer_id: str
    total_size: int
    total_chunks: int
    expected_checksum: str
    received_chunks: dict[int, bytes] = field(default_factory=dict)
    status: TransferStatus = TransferStatus.PENDING

    @property
    def chunks_received(self) -> int:
        """Number of chunks received so far."""
        return len(self.received_chunks)

    @property
    def is_complete(self) -> bool:
        """Check if all chunks have been received."""
        return self.chunks_received == self.total_chunks

    def add_chunk(self, index: int, data: bytes) -> None:
        """Add a received chunk."""
        self.received_chunks[index] = data
        self.status = TransferStatus.IN_PROGRESS

    def assemble(self) -> bytes:
        """Assemble all chunks into complete data."""
        if not self.is_complete:
            raise ValueError(
                f"Cannot assemble: {self.chunks_received}/{self.total_chunks} chunks received"
            )
        # Sort by index and concatenate
        parts = [self.received_chunks[i] for i in range(self.total_chunks)]
        return b"".join(parts)

    def verify(self, data: bytes) -> bool:
        """Verify assembled data matches expected checksum."""
        actual = hashlib.sha256(data).hexdigest()
        return actual == self.expected_checksum


class ChunkedTransferSender:
    """Sends data in chunks over MQTT.

    Parameters
    ----------
    publish_func : Callable
        Function to publish messages, signature: (topic: str, message: PubSubMessage)
    """

    def __init__(self, publish_func: Callable):
        self._publish = publish_func

    def prepare_transfer(self, data: bytes) -> tuple[str, TransferMetadata, list[TransferChunk]]:
        """Prepare data for transfer by splitting into chunks.

        Parameters
        ----------
        data : bytes
            The data to transfer.

        Returns
        -------
        tuple
            (transfer_id, metadata, list of chunks)
        """
        transfer_id = str(uuid4())
        checksum = hashlib.sha256(data).hexdigest()
        total_chunks = (len(data) + CHUNK_SIZE - 1) // CHUNK_SIZE

        metadata = TransferMetadata(
            transfer_id=transfer_id,
            total_size=len(data),
            total_chunks=total_chunks,
            checksum=checksum,
        )

        chunks = []
        for i in range(total_chunks):
            start = i * CHUNK_SIZE
            end = min(start + CHUNK_SIZE, len(data))
            chunk_data = data[start:end]

            chunk = TransferChunk(
                transfer_id=transfer_id,
                chunk_index=i,
                total_chunks=total_chunks,
                data=base64.b64encode(chunk_data).decode("ascii"),
                checksum=hashlib.sha256(chunk_data).hexdigest(),
            )
            chunks.append(chunk)

        return transfer_id, metadata, chunks

    async def send(
        self,
        data: bytes,
        topic_prefix: str,
        on_progress: Callable[[int, int], None] | None = None,
    ) -> str:
        """Send data in chunks to a topic.

        Parameters
        ----------
        data : bytes
            The data to send.
        topic_prefix : str
            Base topic for the transfer (e.g., "otto/nodes/node1/migration").
        on_progress : Callable, optional
            Callback for progress updates, called with (chunks_sent, total_chunks).

        Returns
        -------
        str
            The transfer ID.
        """
        transfer_id, metadata, chunks = self.prepare_transfer(data)

        # Send metadata first
        await self._publish(f"{topic_prefix}/metadata", metadata)

        # Send chunks
        for i, chunk in enumerate(chunks):
            await self._publish(f"{topic_prefix}/chunk", chunk)
            if on_progress:
                on_progress(i + 1, len(chunks))

        # Send completion signal
        complete = TransferComplete(transfer_id=transfer_id, success=True)
        await self._publish(f"{topic_prefix}/complete", complete)

        return transfer_id


class ChunkedTransferReceiver:
    """Receives chunked data transfers over MQTT.

    Parameters
    ----------
    on_complete : Callable
        Callback when transfer completes, signature: (transfer_id: str, data: bytes)
    on_error : Callable, optional
        Callback on error, signature: (transfer_id: str, error: str)
    """

    def __init__(
        self,
        on_complete: Callable[[str, bytes], None],
        on_error: Callable[[str, str], None] | None = None,
    ):
        self._on_complete = on_complete
        self._on_error = on_error
        self._transfers: dict[str, TransferState] = {}

    def handle_metadata(self, metadata: TransferMetadata) -> None:
        """Handle incoming transfer metadata."""
        state = TransferState(
            transfer_id=metadata.transfer_id,
            total_size=metadata.total_size,
            total_chunks=metadata.total_chunks,
            expected_checksum=metadata.checksum,
        )
        self._transfers[metadata.transfer_id] = state

    def handle_chunk(self, chunk: TransferChunk) -> None:
        """Handle incoming chunk."""
        state = self._transfers.get(chunk.transfer_id)
        if state is None:
            # Unknown transfer, ignore
            return

        # Decode and verify chunk
        try:
            data = base64.b64decode(chunk.data)
            chunk_checksum = hashlib.sha256(data).hexdigest()
            if chunk_checksum != chunk.checksum:
                raise ValueError(f"Chunk {chunk.chunk_index} checksum mismatch")
            state.add_chunk(chunk.chunk_index, data)
        except Exception as e:
            state.status = TransferStatus.FAILED
            if self._on_error:
                self._on_error(chunk.transfer_id, str(e))

    def handle_complete(self, complete: TransferComplete) -> None:
        """Handle transfer completion signal."""
        state = self._transfers.get(complete.transfer_id)
        if state is None:
            return

        if not complete.success:
            state.status = TransferStatus.FAILED
            if self._on_error:
                self._on_error(complete.transfer_id, complete.message)
            return

        try:
            if not state.is_complete:
                raise ValueError(f"Missing chunks: {state.chunks_received}/{state.total_chunks}")

            data = state.assemble()
            if not state.verify(data):
                raise ValueError("Checksum verification failed")

            state.status = TransferStatus.COMPLETED
            self._on_complete(complete.transfer_id, data)

        except Exception as e:
            state.status = TransferStatus.FAILED
            if self._on_error:
                self._on_error(complete.transfer_id, str(e))

        finally:
            # Clean up
            del self._transfers[complete.transfer_id]

    def get_progress(self, transfer_id: str) -> tuple[int, int] | None:
        """Get progress of a transfer.

        Returns
        -------
        tuple or None
            (chunks_received, total_chunks) or None if transfer not found.
        """
        state = self._transfers.get(transfer_id)
        if state is None:
            return None
        return (state.chunks_received, state.total_chunks)
