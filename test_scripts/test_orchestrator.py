import time
from pprint import pprint

from commlib.msg import ActionMessage
from commlib.node import Node
from commlib.transports.mqtt import ConnectionParameters


class TestMessage(ActionMessage):
    class Goal(ActionMessage.Goal):
        target_cm: float = 0.0

    class Result(ActionMessage.Result):
        dest_cm: float = 0.0

    class Feedback(ActionMessage.Feedback):
        current_cm: float = 0.0


def on_goal(goal_h):
    c = 0
    res = TestMessage.Result()
    while c < goal_h.data.target_cm:
        if goal_h.cancel_event.is_set():
            break
        goal_h.send_feedback(TestMessage.Feedback(current_cm=c))
        c += 1
        time.sleep(1)
    res.dest_cm = c
    return res


class TestOrchestrator:
    def __init__(self):
        conn_params = ConnectionParameters()
        self.node = Node(
            node_name="test_orchestrator_node",
            connection_params=conn_params,
        )

        self.action_server = self.node.create_action(
            msg_type=TestMessage,
            action_name="test_action",
            on_goal=on_goal,
        )
        self.node.run_forever()


def main():
    orchestrator = TestOrchestrator()
    pprint(f"I am a test orchestrator: {orchestrator}")


if __name__ == "__main__":
    main()
