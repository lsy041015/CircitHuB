from __future__ import annotations

from ._helpers import normalize_part_query, split_part_tokens


class MainWindowPartsMixin:
    def add_part(self, name: str):
        clean = name.strip().upper()
        if not clean:
            return
        for part in self.parts:
            if part["name"] == clean:
                part["qty"] += 1
                self.render_chips()
                self._update_run_button()
                self._update_statusbar()
                self.save_settings()
                return
        self.parts.append({"name": clean, "qty": 1})
        self.render_chips()
        self.render_results()
        self._update_run_button()
        self._update_statusbar()
        self.save_settings()

    def remove_part(self, name: str):
        self.parts = [p for p in self.parts if p["name"] != name]
        self.render_chips()
        self.render_results()
        self._update_run_button()
        self._update_statusbar()
        self.save_settings()

    def set_part_quantity(self, name: str, quantity: int):
        for part in self.parts:
            if part["name"] == name:
                part["qty"] = max(1, int(quantity))
                break
        self._update_statusbar()
        self.save_settings()

    def clear_parts(self):
        self.parts = []
        self.results = []
        self._query_times = []
        self.latest_share_text = ""
        self.render_chips()
        self.render_results()
        self._update_run_button()
        self._update_statusbar()
        self._set_strip("neutral", self._tr("ready_to_search"))
        self.set_status(self._tr("clear_input_status"))
        self.save_settings()

    def load_example(self):
        self.parts = self._default_parts()
        self.render_chips()
        self.render_results()
        self._update_run_button()
        self._update_statusbar()
        self.set_status(self._tr("example_loaded_status"))
        self.save_settings()

    def new_search(self):
        self.show_search_page()
        self.clear_parts()
        self._chip_input.setFocus()

    def get_queries(self) -> list[str]:
        self.commit_input()
        return [p["name"] for p in self.parts]

    def get_quantity_map(self) -> dict[str, int]:
        return {p["name"]: max(1, int(p.get("qty", 1))) for p in self.parts}

    def search_candidate(self, part_name: str):
        part_name = normalize_part_query(part_name)
        if not part_name:
            return
        self.parts = [{"name": part_name, "qty": 1}]
        self.render_chips()
        self.save_settings()
        self.start_search()

    def _load_history_label(self, label):
        self.parts = []
        if isinstance(label, (list, tuple)):
            tokens = [str(tok).strip().upper() for tok in label if str(tok).strip()]
        else:
            tokens = split_part_tokens(str(label))
        for tok in tokens:
            if tok:
                self.parts.append({"name": tok, "qty": 1})
        self.render_chips()
        self.render_results()
        self._update_run_button()
        self._update_statusbar()
        self.save_settings()

    def _load_fav_item(self, name: str):
        self.add_part(name)
