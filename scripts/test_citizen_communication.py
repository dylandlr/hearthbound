import copy
import unittest

from rcon_citizen_communication import validate_chain


def history():
    messages = [{"id": source, "world": "world", "episode": "episode", "sender": "scout",
                 "recipient": "worker", "source": f"minecraft:overworld|{x},101,1",
                 "observed_tick": 8, "sent_tick": 10, "delivered_tick": 10}
                for source, x in (("a", 3), ("b", 7))]
    events = []
    for stage, message, tick in (("DELIVERED", "a", 10), ("DELIVERED", "b", 10),
                                  ("READ", "a", 11), ("READ", "b", 11),
                                  ("SELECTED", "a", 11), ("ASSIGNED", "a", 12),
                                  ("PHYSICAL_COMPLETED", "a", 20)):
        event = {"sequence": len(events) + 1, "stage": stage, "message_id": message,
                 "actor": "worker", "tick": tick}
        if stage != "DELIVERED":
            event["decision_id"] = "decision"
        if stage in ("ASSIGNED", "PHYSICAL_COMPLETED"):
            event.update(job_id="job", destination="minecraft:overworld|10,101,2")
        if stage == "PHYSICAL_COMPLETED":
            event.update(wheat_transferred=1, witness="EXECUTOR_INSERTION_RETURNED_NO_REMAINDER")
        events.append(event)
    return {"audit": {"world": "world"}, "messages": messages, "events": events}


class CommunicationEvidenceTests(unittest.TestCase):
    def test_complete_chain(self):
        self.assertEqual(validate_chain(history()), "job")

    def test_incomplete_or_counterfeit_chains_are_rejected(self):
        mutations = (
            lambda d: d["events"].pop(),
            lambda d: d["events"][-1].update(job_id="another-job"),
            lambda d: d["events"][-1].update(actor="scout"),
            lambda d: d["events"][-1].update(tick=9),
            lambda d: d["events"][-1].update(message_id="b"),
            lambda d: d["events"][-1].update(wheat_transferred=2),
            lambda d: d["events"][3].update(decision_id="another-decision"),
            lambda d: d["events"][3].update(message_id="a"),
            lambda d: d["events"][1].update(message_id="a"),
            lambda d: d["events"][4].update(sequence=4),
            lambda d: d["messages"][0].update(sender="worker"),
            lambda d: d["messages"][0].update(world="another-world"),
            lambda d: d["messages"][0].update(episode="another-episode"),
            lambda d: d["messages"][0].update(observed_tick=12),
        )
        for index, mutation in enumerate(mutations):
            with self.subTest(index=index):
                data = copy.deepcopy(history())
                mutation(data)
                with self.assertRaises((AssertionError, KeyError)):
                    validate_chain(data)


if __name__ == "__main__":
    unittest.main()
