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

    async def get_container_stats(self, container_id: str) -> dict:
        """Get stats for a container.

        Parameters
        ----------
        container_id : str
            The container ID or name.

        Returns
        -------
        dict
            Container stats including CPU, memory, network, and I/O.
        """
        try:
            await self.connect()
            container = await self.docker.containers.get(container_id)
            stats = await container.stats(stream=False)
            # aiodocker returns a list even with stream=False
            return stats[0] if isinstance(stats, list) else stats
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
        self,
        image: str,
        name: str | None = None,
        command: str | list[str] | None = None,
        ports: list[str] | None = None,
        environment: dict[str, str] | None = None,
        detach: bool = True,
    ) -> str:
        """Create and start a new container.

        Parameters
        ----------
        image : str
            The image to create the container from.
        name : str, optional
            The name for the container.
        command : str or list[str], optional
            Command to run in the container. Required for imported images.
        ports : list[str], optional
            Port mappings in "host:container" format (e.g., ["8080:80"]).
        environment : dict[str, str], optional
            Environment variables for the container.
        detach : bool
            Whether to start the container (default: True).

        Returns
        -------
        str
            The container ID.
        """
        try:
            await self.connect()
            # Pull image if not available
            try:
                await self.docker.images.inspect(image)
            except Exception:
                await self.pull_image(image)

            config: dict = {"Image": image}
            host_config: dict = {}

            if command:
                if isinstance(command, str):
                    config["Cmd"] = command.split()
                else:
                    config["Cmd"] = command

            if environment:
                config["Env"] = [f"{k}={v}" for k, v in environment.items()]

            if ports:
                exposed_ports = {}
                port_bindings = {}
                for port_mapping in ports:
                    if ":" in port_mapping:
                        host_port, container_port = port_mapping.split(":", 1)
                        # Ensure container port has protocol
                        if "/" not in container_port:
                            container_port = f"{container_port}/tcp"
                        exposed_ports[container_port] = {}
                        port_bindings[container_port] = [{"HostPort": host_port}]
                    else:
                        container_port = f"{port_mapping}/tcp"
                        exposed_ports[container_port] = {}

                config["ExposedPorts"] = exposed_ports
                host_config["PortBindings"] = port_bindings

            if host_config:
                config["HostConfig"] = host_config

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

    async def export_container(self, container_id: str) -> bytes:
        """Export a container's filesystem as a tarball.

        Parameters
        ----------
        container_id : str
            The container ID or name to export.

        Returns
        -------
        bytes
            The container filesystem as a tar archive.
        """
        try:
            await self.connect()
            # Use low-level API: GET /containers/{id}/export
            # Returns a streaming response, collect all chunks
            chunks = []
            async with self.docker._query(
                f"containers/{container_id}/export",
                method="GET",
            ) as response:
                async for chunk in response.content.iter_any():
                    chunks.append(chunk)
            return b"".join(chunks)
        except Exception as e:
            raise RuntimeError(f"Failed to export container {container_id}: {e}") from e

    async def import_image(self, data: bytes, repository: str, tag: str = "latest") -> str:
        """Import a tarball as a new Docker image.

        Parameters
        ----------
        data : bytes
            The tar archive data to import.
        repository : str
            The repository name for the new image.
        tag : str
            The tag for the new image (default: "latest").

        Returns
        -------
        str
            The ID of the imported image.
        """
        try:
            await self.connect()
            # Use the low-level API to import
            async with self.docker._query(
                "images/create",
                method="POST",
                params={"fromSrc": "-", "repo": repository, "tag": tag},
                data=data,
                headers={"Content-Type": "application/x-tar"},
            ) as response:
                # Consume the response to ensure import completes
                async for _ in response.content.iter_any():
                    pass
            image = await self.docker.images.inspect(f"{repository}:{tag}")
            return image["Id"]
        except Exception as e:
            raise RuntimeError(f"Failed to import image as {repository}:{tag}: {e}") from e

    async def get_container_info(self, container_id: str) -> dict:
        """Get detailed information about a container.

        Useful for extracting configuration to recreate the container elsewhere.

        Parameters
        ----------
        container_id : str
            The container ID or name.

        Returns
        -------
        dict
            Container configuration and state information.
        """
        try:
            await self.connect()
            container = await self.docker.containers.get(container_id)
            return await container.show()
        except Exception as e:
            raise RuntimeError(f"Failed to get container info for {container_id}: {e}") from e
