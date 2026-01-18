import asyncio

from rich.pretty import pprint
from src.dockerhandler import DockerManager


async def main():
    docker = DockerManager()
    containers = await docker.get_containers()
    tasks = [docker.get_container_stats(container.id) for container in containers]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for container, stats in zip(containers, results, strict=True):
        if isinstance(stats, Exception):
            print(f"Error fetching stats for container {container.id}: {stats}")
        else:
            pprint(stats[0])
    await docker.disconnect()  # Clean up the connection


if __name__ == "__main__":
    asyncio.run(main())
