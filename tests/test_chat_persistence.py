import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from digikey_scraper._chat_persistence import ChatPersistenceStore


class ChatPersistenceStoreTests(unittest.TestCase):
    def test_load_messages_returns_empty_dict_when_missing(self) -> None:
        with TemporaryDirectory() as tmp:
            store = ChatPersistenceStore(Path(tmp))
            self.assertEqual(store.load_messages(), {})

    def test_save_and_load_messages_round_trip(self) -> None:
        with TemporaryDirectory() as tmp:
            store = ChatPersistenceStore(Path(tmp))
            payload = {
                "bom-review": [
                    {"id": "m1", "text": "hello"},
                    {"id": "m2", "text": "world"},
                ]
            }

            store.save_messages(payload)

            self.assertEqual(store.load_messages(), payload)

    def test_save_and_load_room_state_round_trip(self) -> None:
        with TemporaryDirectory() as tmp:
            store = ChatPersistenceStore(Path(tmp))
            channels = [{"id": "general", "name": "general", "topic": "", "unread": 0}]
            dms = [{"id": "dm-sh", "name": "서현", "presence": "online", "unread": 0}]
            muted = {"general": False, "dm-sh": True}

            store.save_room_state(channels, dms, muted)

            self.assertEqual(
                store.load_room_state(),
                {"channels": channels, "dms": dms, "muted": muted},
            )

    def test_runtime_path_failure_falls_back_to_cwd(self) -> None:
        with TemporaryDirectory() as tmp:
            fallback = Path(tmp)
            with patch("digikey_scraper._chat_persistence.runtime_path", side_effect=RuntimeError):
                with patch("digikey_scraper._chat_persistence.Path.cwd", return_value=fallback):
                    store = ChatPersistenceStore()

            self.assertEqual(store.messages_path(), fallback / "team_chat_messages.json")
            self.assertEqual(store.rooms_path(), fallback / "team_chat_rooms.json")


if __name__ == "__main__":
    unittest.main()
