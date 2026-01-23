"""Benchmark migration with large image (~800MB).

Run with: PYTHONPATH=. uv run python test_scripts/benchmark_large_image.py
"""

import asyncio
import json
import subprocess
import time
from datetime import datetime
from pathlib import Path

from src.dockerhandler import DockerManager
from src.migration import MigrationStrategy
from src.remote_migration import RemoteMigrationCoordinator

# Configuration
RPI_SSH_URL = "ssh://lolosioann@192.168.2.7"
TEST_IMAGE = "golang:1.21"
IMAGE_LABEL = "golang"
REPETITIONS = 2
OUTPUT_DIR = Path("thesis/benchmarks")


def run_cmd(cmd: str, timeout: int = 300) -> tuple[str, float, bool]:
    """Run command and return (output, duration, success)."""
    start = time.perf_counter()
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        duration = time.perf_counter() - start
        return result.stdout + result.stderr, duration, result.returncode == 0
    except Exception as e:
        return str(e), time.perf_counter() - start, False


async def ensure_image_on_pi():
    """Pre-pull image on Pi."""
    print(f"Pre-pulling {TEST_IMAGE} on Pi (this may take a while)...")
    output, duration, success = run_cmd(
        f"ssh lolosioann@192.168.2.7 'docker pull {TEST_IMAGE}'", timeout=600
    )
    if success:
        print(f"  Done ({duration:.1f}s)")
    else:
        print(f"  Failed: {output[:200]}")
    return success


async def cleanup():
    """Clean up containers and images."""
    run_cmd("docker rm -f $(docker ps -aq --filter 'name=large_') 2>/dev/null || true")
    run_cmd("ssh lolosioann@192.168.2.7 'docker rm -f $(docker ps -aq) 2>/dev/null || true'")
    run_cmd(
        "ssh lolosioann@192.168.2.7 'docker rmi $(docker images -q --filter reference=\"migrated_*\") 2>/dev/null || true'"
    )


async def benchmark_ssh_migration(strategy: MigrationStrategy, rep: int) -> dict:
    """Run single benchmark."""
    container_name = f"large_{IMAGE_LABEL}_{strategy.value}_{rep}"

    source = DockerManager()
    target = DockerManager(url=RPI_SSH_URL)

    try:
        await source.connect()

        # Create container
        container_id = await source.create_container(
            image=TEST_IMAGE,
            name=container_name,
            command="sleep 3600",
        )

        # Run migration
        coordinator = RemoteMigrationCoordinator(source, target)
        result = await coordinator.migrate(
            container_id,
            strategy=strategy,
            remove_source=True,
        )

        # Cleanup target
        await target.connect()
        if result.target_container_id:
            await target.remove_container(result.target_container_id)

        return {
            "image": TEST_IMAGE,
            "image_label": IMAGE_LABEL,
            "strategy": strategy.value,
            "repetition": rep,
            "success": result.success,
            **result.metrics,
        }

    except Exception as e:
        return {
            "image": TEST_IMAGE,
            "image_label": IMAGE_LABEL,
            "strategy": strategy.value,
            "repetition": rep,
            "success": False,
            "error": str(e),
        }
    finally:
        await source.disconnect()
        await target.disconnect()


def benchmark_swarm(rep: int) -> dict:
    """Run Swarm benchmark."""
    service_name = f"large_swarm_{rep}"
    local_node = "lolosioann-laptop"
    remote_node = "raspberrypi"

    try:
        run_cmd(f"docker service rm {service_name} 2>/dev/null")
        time.sleep(1)

        # Create service
        create_cmd = f"docker service create --name {service_name} --constraint node.hostname=={local_node} --replicas 1 {TEST_IMAGE} sleep 3600"
        run_cmd(create_cmd, timeout=300)

        # Wait for running
        for _ in range(120):
            output, _, _ = run_cmd(
                f"docker service ps {service_name} --format '{{{{.CurrentState}}}} {{{{.Node}}}}'"
            )
            if "running" in output.lower() and local_node in output.lower():
                break
            time.sleep(1)

        # Migrate
        migration_start = time.perf_counter()
        update_cmd = f"docker service update --constraint-rm node.hostname=={local_node} --constraint-add node.hostname=={remote_node} {service_name}"
        run_cmd(update_cmd, timeout=300)

        # Wait for running on remote
        for _ in range(180):
            output, _, _ = run_cmd(
                f"docker service ps {service_name} --format '{{{{.CurrentState}}}} {{{{.Node}}}}'"
            )
            if "running" in output.lower() and remote_node in output.lower():
                break
            time.sleep(1)

        migration_time = time.perf_counter() - migration_start

        run_cmd(f"docker service rm {service_name}")

        return {
            "image": TEST_IMAGE,
            "image_label": IMAGE_LABEL,
            "strategy": "swarm",
            "repetition": rep,
            "success": True,
            "total_time_s": migration_time,
            "transfer_size_bytes": 0,
        }

    except Exception as e:
        run_cmd(f"docker service rm {service_name} 2>/dev/null")
        return {
            "image": TEST_IMAGE,
            "image_label": IMAGE_LABEL,
            "strategy": "swarm",
            "repetition": rep,
            "success": False,
            "error": str(e),
        }


async def main():
    print("=" * 60)
    print(f"Large Image Migration Benchmark ({TEST_IMAGE})")
    print("=" * 60)

    results = []

    # Pre-pull on Pi
    await ensure_image_on_pi()

    # SSH migrations
    for strategy in [MigrationStrategy.STOP_START, MigrationStrategy.EXPORT_IMPORT]:
        print(f"\n--- {strategy.value} ---")
        for rep in range(1, REPETITIONS + 1):
            print(f"  Rep {rep}/{REPETITIONS}...", end=" ", flush=True)
            result = await benchmark_ssh_migration(strategy, rep)
            results.append(result)
            if result["success"]:
                size_mb = result.get("transfer_size_bytes", 0) / (1024 * 1024)
                print(f"OK ({result.get('total_time_s', 0):.2f}s, {size_mb:.1f}MB)")
            else:
                print(f"FAIL: {result.get('error', 'unknown')[:50]}")
            await cleanup()
            await asyncio.sleep(2)

    # Swarm migration
    print("\n--- Setting up Swarm ---")
    run_cmd("docker swarm init 2>/dev/null || true")
    output, _, _ = run_cmd("docker swarm join-token worker -q")
    token = output.strip()
    run_cmd(
        f"ssh lolosioann@192.168.2.7 'docker swarm leave 2>/dev/null; docker swarm join --token {token} 192.168.2.3:2377'"
    )
    time.sleep(3)

    print("\n--- swarm ---")
    for rep in range(1, REPETITIONS + 1):
        print(f"  Rep {rep}/{REPETITIONS}...", end=" ", flush=True)
        result = benchmark_swarm(rep)
        results.append(result)
        if result["success"]:
            print(f"OK ({result.get('total_time_s', 0):.2f}s)")
        else:
            print(f"FAIL: {result.get('error', 'unknown')[:50]}")
        time.sleep(2)

    # Cleanup Swarm
    run_cmd("ssh lolosioann@192.168.2.7 'docker swarm leave'")
    run_cmd("docker swarm leave --force")

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = OUTPUT_DIR / f"large_image_benchmark_{timestamp}.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {output_file}")

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for r in results:
        status = "OK" if r["success"] else "FAIL"
        time_s = r.get("total_time_s", 0)
        size_mb = r.get("transfer_size_bytes", 0) / (1024 * 1024)
        print(
            f"{r['strategy']:15} rep {r['repetition']}: {status:4} {time_s:7.2f}s  {size_mb:7.1f}MB"
        )


if __name__ == "__main__":
    asyncio.run(main())
