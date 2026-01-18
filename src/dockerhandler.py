import aiodocker
from aiohttp import ClientTimeout


class DockerManager:
    def __init__(self, url: str = "unix:///var/run/docker.sock"):
        self._docker: aiodocker.Docker | None = None
        self._url = url
        self.timeout = 10
        self._connected = False

    async def connect(self):
        if self._connected:
            return
        try:
            self._docker = aiodocker.Docker(
                url=self._url, timeout=ClientTimeout(total=self.timeout)
            )
            # test connection
            await self._docker.version()
            self._connected = True
        except Exception as e:
            self._connected = False
            raise ConnectionError(f"Failed to connect to Docker daemon: {e}") from e

    async def disconnect(self):
        if self._docker:
            await self._docker.close()
            self._connected = False

    @property
    def docker(self) -> aiodocker.Docker:
        if not self._connected or not self._docker:
            raise ConnectionError("Not connected to Docker daemon.")
        return self._docker

    async def get_containers(self):
        try:
            await self.connect()
            return await self.docker.containers.list()
        except Exception as e:
            raise RuntimeError(f"Failed to get containers: {e}") from e

    async def get_container_stats(self, container_id: str):
        try:
            await self.connect()
            container = await self.docker.containers.get(container_id)
            stats = await container.stats(stream=False)
            return stats
        except Exception as e:
            raise RuntimeError(f"Failed to get stats for container {container_id}: {e}") from e

    async def start_container(self, container_id: str) -> None:
        """Start a stopped container."""
        try:
            await self.connect()
            container = await self.docker.containers.get(container_id)
            await container.start()
        except Exception as e:
            raise RuntimeError(f"Failed to start container {container_id}: {e}") from e

    async def stop_container(self, container_id: str) -> None:
        """Stop a running container."""
        try:
            await self.connect()
            container = await self.docker.containers.get(container_id)
            await container.stop()
        except Exception as e:
            raise RuntimeError(f"Failed to stop container {container_id}: {e}") from e

    async def pull_image(self, image: str) -> None:
        """Pull an image from registry."""
        try:
            await self.connect()
            # Parse image:tag
            if ":" in image:
                repo, tag = image.rsplit(":", 1)
            else:
                repo, tag = image, "latest"
            await self.docker.images.pull(from_image=repo, tag=tag)
        except Exception as e:
            raise RuntimeError(f"Failed to pull image {image}: {e}") from e

    async def create_container(
        self, image: str, name: str | None = None, detach: bool = True
    ) -> str:
        """Create and start a new container.

        Pulls the image if not available locally.
        Returns the container ID.
        """
        try:
            await self.connect()
            # Pull image if not available
            try:
                await self.docker.images.inspect(image)
            except Exception:
                await self.pull_image(image)

            config = {"Image": image}
            container = await self.docker.containers.create_or_replace(
                name=name or image.replace(":", "_").replace("/", "_"),
                config=config,
            )
            if detach:
                await container.start()
            return container.id
        except Exception as e:
            raise RuntimeError(f"Failed to create container from {image}: {e}") from e

    async def remove_container(self, container_id: str, force: bool = True) -> None:
        """Remove a container."""
        try:
            await self.connect()
            container = await self.docker.containers.get(container_id)
            await container.delete(force=force)
        except Exception as e:
            raise RuntimeError(f"Failed to remove container {container_id}: {e}") from e
