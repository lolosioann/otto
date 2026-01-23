"""Test Docker Swarm migration for comparison.

Run with: uv run python test_scripts/test_swarm_migration.py
"""

import json
import subprocess
import time


def run_cmd(cmd: str, timeout: int = 60) -> tuple[str, float]:
    """Run command and return output with duration."""
    start = time.perf_counter()
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    duration = time.perf_counter() - start
    output = result.stdout + result.stderr
    return output.strip(), duration


def wait_for_service_state(
    service: str, desired_state: str, node: str | None = None, timeout: int = 60
) -> float:
    """Wait for service task to reach desired state, return wait time."""
    start = time.perf_counter()
    while time.perf_counter() - start < timeout:
        output, _ = run_cmd(
            f"docker service ps {service} --format '{{{{.CurrentState}}}} {{{{.Node}}}}'"
        )
        lines = output.strip().split("\n")
        for line in lines:
            if desired_state.lower() in line.lower() and (
                node is None or node.lower() in line.lower()
            ):
                return time.perf_counter() - start
        time.sleep(0.5)
    raise TimeoutError(
        f"Service {service} did not reach {desired_state} on {node} within {timeout}s"
    )


def test_swarm_migration():
    """Test Swarm service migration via constraint update."""
    print("\n=== Swarm Migration Test ===")

    service_name = "swarm_migration_test"
    local_node = "lolosioann-laptop"
    remote_node = "raspberrypi"

    metrics = {
        "method": "swarm_constraint",
        "service_create_time_s": 0.0,
        "migration_command_time_s": 0.0,
        "migration_complete_time_s": 0.0,
        "total_time_s": 0.0,
    }

    # Cleanup any existing service
    run_cmd(f"docker service rm {service_name} 2>/dev/null")
    time.sleep(1)

    # Create service on local node
    print(f"Creating service on {local_node}...")
    create_cmd = f"""docker service create \
        --name {service_name} \
        --constraint node.hostname=={local_node} \
        --replicas 1 \
        busybox:latest sleep 3600"""

    total_start = time.perf_counter()
    _, create_time = run_cmd(create_cmd)

    # Wait for running
    wait_time = wait_for_service_state(service_name, "Running", local_node)
    metrics["service_create_time_s"] = create_time + wait_time
    print(f"Service created and running: {metrics['service_create_time_s']:.2f}s")

    # Show current state
    output, _ = run_cmd(f"docker service ps {service_name}")
    print(f"Before migration:\n{output}")

    # Migrate by updating constraint
    print(f"\nMigrating to {remote_node}...")
    migration_start = time.perf_counter()

    update_cmd = f"""docker service update \
        --constraint-rm node.hostname=={local_node} \
        --constraint-add node.hostname=={remote_node} \
        {service_name}"""

    _, cmd_time = run_cmd(update_cmd)
    metrics["migration_command_time_s"] = cmd_time

    # Wait for running on remote
    try:
        wait_time = wait_for_service_state(service_name, "Running", remote_node, timeout=120)
        metrics["migration_complete_time_s"] = time.perf_counter() - migration_start
        print(f"Migration completed: {metrics['migration_complete_time_s']:.2f}s")
    except TimeoutError as e:
        print(f"Migration failed: {e}")
        metrics["migration_complete_time_s"] = -1

    metrics["total_time_s"] = time.perf_counter() - total_start

    # Show final state
    output, _ = run_cmd(f"docker service ps {service_name}")
    print(f"\nAfter migration:\n{output}")

    # Cleanup
    print("\nCleaning up...")
    run_cmd(f"docker service rm {service_name}")

    return metrics


def test_swarm_drain_migration():
    """Test Swarm migration via node drain."""
    print("\n=== Swarm Drain Migration Test ===")

    service_name = "swarm_drain_test"
    local_node = "lolosioann-laptop"
    remote_node = "raspberrypi"

    metrics = {
        "method": "swarm_drain",
        "service_create_time_s": 0.0,
        "migration_command_time_s": 0.0,
        "migration_complete_time_s": 0.0,
        "total_time_s": 0.0,
    }

    # Cleanup
    run_cmd(f"docker service rm {service_name} 2>/dev/null")
    time.sleep(1)

    # Create service (no constraint, will land on manager by default)
    print("Creating service...")
    create_cmd = f"""docker service create \
        --name {service_name} \
        --replicas 1 \
        busybox:latest sleep 3600"""

    total_start = time.perf_counter()
    _, create_time = run_cmd(create_cmd)
    wait_time = wait_for_service_state(service_name, "Running")
    metrics["service_create_time_s"] = create_time + wait_time
    print(f"Service created: {metrics['service_create_time_s']:.2f}s")

    # Check where it landed
    output, _ = run_cmd(f"docker service ps {service_name} --format '{{{{.Node}}}}'")
    current_node = output.strip().split("\n")[0]
    print(f"Service running on: {current_node}")

    if current_node == remote_node:
        print("Service already on remote node, skipping drain test")
        run_cmd(f"docker service rm {service_name}")
        return None

    # Drain local node to force migration
    print(f"\nDraining {local_node} to force migration...")
    migration_start = time.perf_counter()

    _, cmd_time = run_cmd(f"docker node update --availability drain {local_node}")
    metrics["migration_command_time_s"] = cmd_time

    # Wait for running on remote
    try:
        wait_time = wait_for_service_state(service_name, "Running", remote_node, timeout=120)
        metrics["migration_complete_time_s"] = time.perf_counter() - migration_start
        print(f"Migration completed: {metrics['migration_complete_time_s']:.2f}s")
    except TimeoutError as e:
        print(f"Migration failed: {e}")
        metrics["migration_complete_time_s"] = -1

    metrics["total_time_s"] = time.perf_counter() - total_start

    # Restore node availability
    run_cmd(f"docker node update --availability active {local_node}")

    # Show final state
    output, _ = run_cmd(f"docker service ps {service_name}")
    print(f"\nAfter migration:\n{output}")

    # Cleanup
    print("\nCleaning up...")
    run_cmd(f"docker service rm {service_name}")

    return metrics


def main():
    print("=" * 50)
    print("Swarm Migration Test Suite")
    print("=" * 50)

    results = []

    # Test constraint-based migration
    metrics1 = test_swarm_migration()
    results.append(metrics1)
    print(f"\nConstraint migration metrics:\n{json.dumps(metrics1, indent=2)}")

    time.sleep(2)

    # Test drain-based migration
    metrics2 = test_swarm_drain_migration()
    if metrics2:
        results.append(metrics2)
        print(f"\nDrain migration metrics:\n{json.dumps(metrics2, indent=2)}")

    # Summary
    print("\n" + "=" * 50)
    print("Summary:")
    print("=" * 50)
    for r in results:
        print(f"{r['method']}: {r['migration_complete_time_s']:.2f}s")


if __name__ == "__main__":
    main()
