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


class ExampleNode:
    def __init__(self):
        conn_params = ConnectionParameters()
        self.node = Node(node_name="example_node", connection_params=conn_params)
        self.action_client = self.node.create_action_client(
            msg_type=TestMessage,
            action_name="test_action",
            on_feedback=self._on_feedback,
            on_result=self._on_result,
            on_goal_reached=self._on_goal,
        )
        self.node.run()

    def _on_feedback(self, feedback: TestMessage.Feedback):
        pprint(f"Feedback received: {feedback}")

    def _on_result(self, result: TestMessage.Result):
        pprint(f"Result received: {result}")

    def _on_goal(self, goal: TestMessage.Goal):
        pprint(f"Goal received: {goal}")

    def set_goal(self, target_cm: float):
        goal = TestMessage.Goal(target_cm=target_cm)
        self.action_client.send_goal(goal)
        result = self.action_client.get_result(wait=True)
        pprint(f"Final result: {result}")


def main():
    node = ExampleNode()
    pprint(f"I am a test node: {node}")
    node.set_goal(5.0)


if __name__ == "__main__":
    main()
