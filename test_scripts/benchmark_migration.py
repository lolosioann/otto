"""Comprehensive migration benchmarks for thesis.

Run with: PYTHONPATH=. uv run python test_scripts/benchmark_migration.py

Benchmarks:
- Container sizes: busybox, alpine, nginx, python
- Filesystem state: empty vs with data
- Strategies: StopStart, ExportImport, Swarm
- 10 repetitions each
"""

import asyncio
import csv
import json
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from src.dockerhandler import DockerManager
from src.migration import MigrationStrategy
from src.remote_migration import RemoteMigrationCoordinator

# Configuration
RPI_SSH_URL = "ssh://lolosioann@192.168.2.7"
REPETITIONS = 10
OUTPUT_DIR = Path("thesis/benchmarks")

# Test images (varying sizes)
TEST_IMAGES = [
    ("busybox:latest", "busybox"),
    ("alpine:latest", "alpine"),
    ("nginx:alpine", "nginx"),
    ("python:3.11-alpine", "python"),
]

# Filesystem states
FILESYSTEM_STATES = [
    ("empty", None),  # No extra data
    ("small", "dd if=/dev/urandom of=/data.bin bs=1K count=100"),  # 100KB
    ("medium", "dd if=/dev/urandom of=/data.bin bs=1K count=1000"),  # 1MB
]


@dataclass
class BenchmarkResult:
    """Single benchmark result."""

    timestamp: str
    image: str
    image_label: str
    filesystem_state: str
    strategy: str
    repetition: int
    success: bool
    export_time_s: float
    transfer_size_bytes: int
    import_time_s: float
    start_time_s: float
    total_time_s: float
    error: str = ""

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "image": self.image,
            "image_label": self.image_label,
            "filesystem_state": self.filesystem_state,
            "strategy": self.strategy,
            "repetition": self.repetition,
            "success": self.success,
            "export_time_s": self.export_time_s,
            "transfer_size_bytes": self.transfer_size_bytes,
            "import_time_s": self.import_time_s,
            "start_time_s": self.start_time_s,
            "total_time_s": self.total_time_s,
            "error": self.error,
        }


def run_cmd(cmd: str, timeout: int = 120) -> tuple[str, float, bool]:
    """Run command and return (output, duration, success)."""
    start = time.perf_counter()
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        duration = time.perf_counter() - start
        return result.stdout + result.stderr, duration, result.returncode == 0
    except subprocess.TimeoutExpired:
        return "Timeout", time.perf_counter() - start, False
    except Exception as e:
        return str(e), time.perf_counter() - start, False


async def cleanup_remote():
    """Clean up containers and images on Pi."""
    cmds = [
        "docker rm -f $(docker ps -aq) 2>/dev/null || true",
        "docker rmi $(docker images -q --filter 'reference=migrated_*') 2>/dev/null || true",
    ]
    for cmd in cmds:
        run_cmd(f"ssh lolosioann@192.168.2.7 '{cmd}'")


async def cleanup_local():
    """Clean up local test containers."""
    run_cmd("docker rm -f $(docker ps -aq --filter 'name=bench_') 2>/dev/null || true")


async def ensure_image_on_pi(image: str):
    """Make sure image exists on Pi to avoid pull time in benchmarks."""
    print(f"  Ensuring {image} on Pi...", end=" ", flush=True)
    output, duration, success = run_cmd(
        f"ssh lolosioann@192.168.2.7 'docker pull {image}'", timeout=300
    )
    if success:
        print(f"done ({duration:.1f}s)")
    else:
        print(f"failed: {output[:100]}")


async def benchmark_ssh_migration(
    image: str,
    image_label: str,
    fs_state: str,
    fs_cmd: str | None,
    strategy: MigrationStrategy,
    rep: int,
) -> BenchmarkResult:
    """Run single SSH migration benchmark."""
    container_name = f"bench_{image_label}_{fs_state}_{rep}"
    timestamp = datetime.now().isoformat()

    source = DockerManager()
    target = DockerManager(url=RPI_SSH_URL)

    try:
        await source.connect()

        # Create container with optional filesystem state
        cmd = f"sh -c '{fs_cmd} 2>/dev/null; sleep 3600'" if fs_cmd else "sleep 3600"

        container_id = await source.create_container(
            image=image,
            name=container_name,
            command=cmd,
        )

        # Wait for filesystem command to complete
        if fs_cmd:
            await asyncio.sleep(2)

        # Run migration
        coordinator = RemoteMigrationCoordinator(source, target)
        result = await coordinator.migrate(
            container_id,
            strategy=strategy,
            remove_source=True,
        )

        # Clean up on target
        await target.connect()
        if result.target_container_id:
            await target.remove_container(result.target_container_id)

        metrics = result.metrics
        return BenchmarkResult(
            timestamp=timestamp,
            image=image,
            image_label=image_label,
            filesystem_state=fs_state,
            strategy=strategy.value,
            repetition=rep,
            success=result.success,
            export_time_s=metrics.get("export_time_s", 0),
            transfer_size_bytes=metrics.get("transfer_size_bytes", 0),
            import_time_s=metrics.get("import_time_s", 0),
            start_time_s=metrics.get("container_start_time_s", 0),
            total_time_s=metrics.get("total_time_s", 0),
            error="" if result.success else result.message,
        )

    except Exception as e:
        return BenchmarkResult(
            timestamp=timestamp,
            image=image,
            image_label=image_label,
            filesystem_state=fs_state,
            strategy=strategy.value,
            repetition=rep,
            success=False,
            export_time_s=0,
            transfer_size_bytes=0,
            import_time_s=0,
            start_time_s=0,
            total_time_s=0,
            error=str(e),
        )
    finally:
        await source.disconnect()
        await target.disconnect()


def wait_for_swarm_running(service: str, node: str, timeout: int = 120) -> float:
    """Wait for swarm service to be running on node, return wait time."""
    start = time.perf_counter()
    while time.perf_counter() - start < timeout:
        output, _, _ = run_cmd(
            f"docker service ps {service} --format '{{{{.CurrentState}}}} {{{{.Node}}}}'"
        )
        for line in output.strip().split("\n"):
            if "running" in line.lower() and node.lower() in line.lower():
                return time.perf_counter() - start
        time.sleep(0.5)
    raise TimeoutError(f"Service didn't start on {node}")


def benchmark_swarm_migration(
    image: str,
    image_label: str,
    fs_state: str,
    rep: int,
) -> BenchmarkResult:
    """Run single Swarm migration benchmark."""
    service_name = f"bench_swarm_{image_label}_{rep}"
    timestamp = datetime.now().isoformat()
    local_node = "lolosioann-laptop"
    remote_node = "raspberrypi"

    try:
        # Clean up any existing service
        run_cmd(f"docker service rm {service_name} 2>/dev/null")
        time.sleep(1)

        # Create service on local node
        create_cmd = f"""docker service create \
            --name {service_name} \
            --constraint node.hostname=={local_node} \
            --replicas 1 \
            {image} sleep 3600"""
        _, create_time, success = run_cmd(create_cmd)
        if not success:
            raise RuntimeError("Failed to create service")

        wait_for_swarm_running(service_name, local_node)

        # Migrate via constraint update
        migration_start = time.perf_counter()
        update_cmd = f"""docker service update \
            --constraint-rm node.hostname=={local_node} \
            --constraint-add node.hostname=={remote_node} \
            {service_name}"""
        _, cmd_time, success = run_cmd(update_cmd, timeout=180)
        if not success:
            raise RuntimeError("Failed to update service")

        wait_for_swarm_running(service_name, remote_node, timeout=180)
        migration_time = time.perf_counter() - migration_start

        # Clean up
        run_cmd(f"docker service rm {service_name}")

        return BenchmarkResult(
            timestamp=timestamp,
            image=image,
            image_label=image_label,
            filesystem_state=fs_state,
            strategy="swarm",
            repetition=rep,
            success=True,
            export_time_s=0,  # Swarm doesn't expose this
            transfer_size_bytes=0,  # No direct transfer
            import_time_s=0,
            start_time_s=0,
            total_time_s=migration_time,
            error="",
        )

    except Exception as e:
        run_cmd(f"docker service rm {service_name} 2>/dev/null")
        return BenchmarkResult(
            timestamp=timestamp,
            image=image,
            image_label=image_label,
            filesystem_state=fs_state,
            strategy="swarm",
            repetition=rep,
            success=False,
            export_time_s=0,
            transfer_size_bytes=0,
            import_time_s=0,
            start_time_s=0,
            total_time_s=0,
            error=str(e),
        )


async def run_benchmarks():
    """Run all benchmarks."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    results: list[BenchmarkResult] = []

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = OUTPUT_DIR / f"migration_benchmarks_{timestamp}.csv"
    json_path = OUTPUT_DIR / f"migration_benchmarks_{timestamp}.json"

    print("=" * 60)
    print("Migration Benchmark Suite")
    print("=" * 60)
    print(f"Repetitions: {REPETITIONS}")
    print(f"Images: {[img[1] for img in TEST_IMAGES]}")
    print(f"Filesystem states: {[fs[0] for fs in FILESYSTEM_STATES]}")
    print(f"Output: {csv_path}")
    print("=" * 60)

    # Pre-pull images on Pi
    print("\nPre-pulling images on Pi...")
    for image, _ in TEST_IMAGES:
        await ensure_image_on_pi(image)

    # SSH-based migrations (StopStart and ExportImport)
    print("\n--- SSH Migration Benchmarks ---")
    for image, image_label in TEST_IMAGES:
        for fs_name, fs_cmd in FILESYSTEM_STATES:
            for strategy in [MigrationStrategy.STOP_START, MigrationStrategy.EXPORT_IMPORT]:
                print(f"\n[{image_label}] [{fs_name}] [{strategy.value}]")

                for rep in range(1, REPETITIONS + 1):
                    print(f"  Rep {rep}/{REPETITIONS}...", end=" ", flush=True)

                    result = await benchmark_ssh_migration(
                        image, image_label, fs_name, fs_cmd, strategy, rep
                    )
                    results.append(result)

                    if result.success:
                        print(
                            f"OK ({result.total_time_s:.2f}s, {result.transfer_size_bytes / 1024:.0f}KB)"
                        )
                    else:
                        print(f"FAIL: {result.error[:50]}")

                    # Brief pause between runs
                    await asyncio.sleep(1)

                # Clean up between strategy/fs combinations
                await cleanup_local()
                await cleanup_remote()

    # Swarm migrations (only with empty filesystem, as Swarm doesn't preserve state)
    print("\n--- Swarm Migration Benchmarks ---")

    # Initialize Swarm
    print("Initializing Swarm cluster...")
    run_cmd("docker swarm init 2>/dev/null || true")

    # Get join token and join Pi
    output, _, _ = run_cmd("docker swarm join-token worker -q")
    token = output.strip()
    local_ip = "192.168.2.3"
    run_cmd(
        f"ssh lolosioann@192.168.2.7 'docker swarm leave 2>/dev/null; docker swarm join --token {token} {local_ip}:2377'"
    )

    time.sleep(2)

    for image, image_label in TEST_IMAGES:
        print(f"\n[{image_label}] [empty] [swarm]")

        for rep in range(1, REPETITIONS + 1):
            print(f"  Rep {rep}/{REPETITIONS}...", end=" ", flush=True)

            result = benchmark_swarm_migration(image, image_label, "empty", rep)
            results.append(result)

            if result.success:
                print(f"OK ({result.total_time_s:.2f}s)")
            else:
                print(f"FAIL: {result.error[:50]}")

            time.sleep(2)

    # Clean up Swarm
    print("\nCleaning up Swarm...")
    run_cmd("ssh lolosioann@192.168.2.7 'docker swarm leave'")
    run_cmd("docker swarm leave --force")

    # Save results
    print("\n--- Saving Results ---")

    # CSV
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].to_dict().keys())
        writer.writeheader()
        for r in results:
            writer.writerow(r.to_dict())
    print(f"CSV saved: {csv_path}")

    # JSON
    with open(json_path, "w") as f:
        json.dump([r.to_dict() for r in results], f, indent=2)
    print(f"JSON saved: {json_path}")

    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)

    successful = [r for r in results if r.success]
    failed = [r for r in results if not r.success]
    print(f"Total: {len(results)}, Success: {len(successful)}, Failed: {len(failed)}")

    # Group by strategy
    for strategy in ["stop_start", "export_import", "swarm"]:
        strat_results = [r for r in successful if r.strategy == strategy]
        if strat_results:
            avg_time = sum(r.total_time_s for r in strat_results) / len(strat_results)
            avg_size = sum(r.transfer_size_bytes for r in strat_results) / len(strat_results)
            print(f"\n{strategy}:")
            print(f"  Avg time: {avg_time:.2f}s")
            print(f"  Avg transfer: {avg_size / 1024:.0f}KB")


if __name__ == "__main__":
    asyncio.run(run_benchmarks())
