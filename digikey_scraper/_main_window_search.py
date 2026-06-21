from __future__ import annotations

import time

from PySide6.QtWidgets import QMessageBox

from ._helpers import _calc_bom_total, price_rows
from .formatters import format_result_text, format_results_text
from .models import ProductResult
from .workers import SearchSignals, SearchWorker


def result_status_counts(results: list[ProductResult]) -> dict[str, int]:
    errors = sum(1 for result in results if result.error)
    blocked = sum(
        1
        for result in results
        if result.error
        and ("차단" in result.error or "blocked automated access" in result.error.lower())
    )
    candidates = sum(1 for result in results if result.candidate_results)
    completed = len(results) - errors
    return {
        "completed": completed,
        "errors": errors,
        "blocked": blocked,
        "candidates": candidates,
    }


class MainWindowSearchMixin:
    def _set_search_state(self, searching: bool):
        self.is_searching = searching
        self.run_btn.setEnabled(not searching)
        self.cancel_btn.setEnabled(searching)
        self.timeout_input.setEnabled(not searching)
        self._chip_input.setEnabled(not searching)
        self.render_chips()
        self._update_run_button()

    def cancel_search(self):
        if not self.is_searching or self.worker is None:
            return
        self.worker.cancel()
        self.cancel_btn.setEnabled(False)
        self.set_status(self._tr("cancel_requested_status"))

    def start_search(self):
        if self.is_searching:
            return
        queries = self.get_queries()
        if not queries:
            QMessageBox.warning(
                self, self._tr("input_required_title"), self._tr("input_required_message")
            )
            return
        try:
            timeout = int(self.timeout_input.text().strip())
            if timeout <= 0:
                raise ValueError
        except ValueError:
            QMessageBox.warning(
                self, self._tr("input_error_title"), self._tr("timeout_error_message")
            )
            return

        self.search_started_at = time.time()
        self._last_query_ts = self.search_started_at
        self.search_total = len(queries)
        self.results = []
        self._query_times = []
        self.latest_share_text = ""
        self._set_search_state(True)
        self._set_strip("searching", self._tr("strip_searching", count=len(queries)), progress=0)
        self._set_api_state("searching")
        self.set_status(self._tr("started_search_status"))
        self.render_results()
        self.save_settings()

        self.search_signals = SearchSignals()
        self.worker = SearchWorker(
            queries, timeout, self.browser_toggle.isChecked(), self.search_signals, self.language
        )
        self.search_signals.progress.connect(self.on_search_progress)
        self.search_signals.finished.connect(self.finish_search)
        self.search_signals.failed.connect(self.fail_search)
        self.search_thread = self._build_search_thread()
        self.search_thread.start()

    def _build_search_thread(self):
        import threading

        return threading.Thread(target=self.worker.run, daemon=True, name="digikey-search")

    def on_search_progress(self, index: int, total: int, query: str):
        now = time.time()
        if index > 1:
            self._query_times.append(now - self._last_query_ts)
        self._last_query_ts = now

        pct = int(((index - 1) / total) * 100)
        self._set_strip(
            "searching",
            self._tr("strip_searching", count=total),
            f"[{index}/{total}] {query}",
            progress=pct,
        )
        self.set_status(self._tr("search_progress", index=index, total=total, query=query))

    def finish_search(self, results: list[ProductResult], show_browser: bool, cancelled: bool):
        self.results = results
        now = time.time()
        for _r in results:
            if _r.scraped_at is None:
                _r.scraped_at = now
        if self._last_query_ts > 0:
            self._query_times.append(now - self._last_query_ts)

        quantities = self.get_quantity_map()
        self.latest_share_text = format_results_text(results, self.language, quantities)
        elapsed = now - self.search_started_at if self.search_started_at > 0 else 0
        avg = elapsed / max(len(results), 1)
        self._last_avg_time = avg
        self._last_bom_total = _calc_bom_total(results, quantities)

        counts = result_status_counts(results)
        completed = counts["completed"]

        label = ", ".join(p["name"] for p in self.parts)
        has_errors = counts["errors"] > 0
        has_candidates = counts["candidates"] > 0
        status = "error" if has_errors else ("warning" if has_candidates else "success")
        self.history.append((label, [p["name"] for p in self.parts], self._tr("history_now"), status))

        for r in results:
            if r.query in self.favorites and not r.error and r.price_rows:
                rows = price_rows(r.price_rows)
                if rows and rows[0][1]:
                    self.favorite_prices[r.query] = rows[0][1]

        if cancelled:
            self._set_strip(
                "cancelled",
                self._tr("strip_cancelled", done=len(results), total=self.search_total),
                progress=int(len(results) / max(self.search_total, 1) * 100),
            )
            self._set_api_state("warning", "검색 취소됨")
            self.set_status(self._tr("search_cancelled_status"))
        else:
            summary = self._tr(
                "strip_completed_summary",
                ok=completed,
                error=counts["errors"],
                blocked=counts["blocked"],
                candidate=counts["candidates"],
            )
            extra = self._tr(
                "strip_avg_bom",
                avg=f"{avg:.1f}",
                qty=sum(quantities.values()),
                total=f"{self._last_bom_total:.2f}",
            )
            self._set_strip(
                "error" if completed == 0 and has_errors else "success",
                summary,
                extra,
                done_tag=self._tr("strip_done_label"),
                progress=100,
            )
            if has_errors:
                self._set_api_state("error", f"오류 {counts['errors']}개")
            else:
                self._set_api_state("warning" if has_candidates else "ok")
            self.set_status(
                self._tr(
                    "search_completed_summary_status",
                    total=len(results),
                    ok=completed,
                    error=counts["errors"],
                    blocked=counts["blocked"],
                    candidate=counts["candidates"],
                )
            )

        self._set_search_state(False)
        self.render_sidebar_lists()
        self.render_results()

        if self.auto_save_toggle.isChecked() and self.latest_share_text.strip():
            try:
                saved = self._auto_save_results()
                if saved:
                    self.set_status(self._tr("auto_save_complete", name=saved.name))
            except Exception as exc:
                self.set_status(self._tr("auto_save_failed", error=exc))

        if not cancelled:
            try:
                self.result_repository.save_search(
                    [p["name"] for p in self.parts], results, self.language
                )
            except Exception:
                pass

        if show_browser and self.worker is not None:
            self.current_driver = self.worker.driver
        self.search_started_at = 0.0
        self.search_total = 0
        self.worker = None
        self.search_thread = None
        self.save_settings()

    def fail_search(self, message: str):
        guide = self._build_failure_guide(message)
        self.results = [ProductResult(query="Error", error=f"{message}\n\nGuide: {guide}")]
        self._query_times = [0.0]
        self.latest_share_text = format_result_text(self.results[0], self.language)
        self._set_strip("error", self._tr("search_failed_strip"), progress=0)
        self._set_api_state("error")
        self.set_status(self._tr("search_failed_status"))
        self._set_search_state(False)
        self.render_results()
        self.search_started_at = 0.0
        self.search_total = 0
        self.worker = None
        self.search_thread = None

    def _build_failure_guide(self, msg: str) -> str:
        m = msg.lower()
        if any(t in m for t in ["chromedriver", "driver", "chrome binary"]):
            return "Check Chrome/ChromeDriver installation and version compatibility."
        if any(t in m for t in ["timeout", "timed out"]):
            return "Check your network and increase the timeout before retrying."
        if any(t in m for t in ["connection", "dns", "refused"]):
            return "Check internet connection and firewall/proxy settings."
        if any(t in m for t in ["403", "429", "captcha", "forbidden"]):
            return "Reduce request rate or enable visible browser mode and retry."
        return "Review the error and retry. Check browser/network environment."
