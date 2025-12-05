"""PySide6 GUI for running and visualizing the gold outlook workflow."""

from __future__ import annotations

import io
import json
import logging
import re
import sys
import traceback
from functools import partial
from pathlib import Path
from typing import Any, Callable, Dict

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, Signal, QUrl
from PySide6.QtGui import QDesktopServices, QPixmap, QTextCursor
from PySide6.QtWidgets import (
    QApplication,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QStatusBar,
    QTabWidget,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from autogentest1.config.settings import get_settings
from autogentest1.utils import logging as logging_utils
from autogentest1.services.risk_gate import HardRiskBreachError
from autogentest1.workflows.gold_outlook import build_conversation_context, run_gold_outlook


class WorkflowWorkerSignals(QObject):
    """Signals emitted by the workflow background runner."""

    finished = Signal(dict, str, str)
    error = Signal(str)
    log = Signal(str)
    chart = Signal(str)
    context = Signal(dict)


class WorkflowWorker(QRunnable):
    """Run the gold outlook workflow in a background thread."""

    def __init__(self, symbol: str, days: int) -> None:
        super().__init__()
        self.symbol = symbol
        self.days = days
        self.signals = WorkflowWorkerSignals()
        self._cancel_requested = False

    def request_cancel(self) -> None:
        self._cancel_requested = True

    @property
    def is_cancelled(self) -> bool:
        return self._cancel_requested

    def run(self) -> None:  # pragma: no cover - GUI worker
        log_buffer = io.StringIO()
        context_payload: Dict[str, Any] | None = None
        context_history: Any | None = None

        class SignalLoggingHandler(logging.Handler):
            def __init__(self, outer: "WorkflowWorker", stream_buffer: io.StringIO) -> None:
                super().__init__(level=logging.INFO)
                self._outer = outer
                self._buffer = stream_buffer
                self.setFormatter(
                    logging.Formatter("%(asctime)s | %(levelname)s | %(message)s", "%H:%M:%S")
                )

            def emit(self, record: logging.LogRecord) -> None:  # pragma: no cover - background logging
                msg = self.format(record)
                if self._outer._cancel_requested:
                    return
                self._buffer.write(msg + "\n")
                self._outer.signals.log.emit(msg + "\n")

        class SignalTextWriter(io.TextIOBase):
            def __init__(self, outer: "WorkflowWorker", stream_buffer: io.StringIO) -> None:
                super().__init__()
                self._outer = outer
                self._buffer = stream_buffer

            def writable(self) -> bool:  # pragma: no cover - simple override
                return True

            def write(self, s: str) -> int:  # pragma: no cover - background logging
                if not s:
                    return 0
                if self._outer._cancel_requested:
                    return len(s)
                self._buffer.write(s)
                self._outer.signals.log.emit(s)
                return len(s)

            def flush(self) -> None:  # pragma: no cover - noop
                self._buffer.flush()

        handler = SignalLoggingHandler(self, log_buffer)
        stdout_writer = SignalTextWriter(self, log_buffer)
        stderr_writer = SignalTextWriter(self, log_buffer)

        original_configure = logging_utils.configure_logging

        def configure_wrapper(level_name: str = "INFO") -> None:
            original_configure(level_name)
            root_logger = logging.getLogger()
            if handler not in root_logger.handlers:
                root_logger.addHandler(handler)

        try:
            logging_utils.configure_logging = configure_wrapper  # type: ignore[assignment]
            original_stdout, original_stderr = sys.stdout, sys.stderr
            sys.stdout = stdout_writer  # type: ignore[assignment]
            sys.stderr = stderr_writer  # type: ignore[assignment]
            if self._cancel_requested:
                return
            settings = get_settings()
            context_payload, context_history = build_conversation_context(
                symbol=self.symbol,
                days=self.days,
                settings=settings,
            )
            self.signals.context.emit(context_payload)
            if self._cancel_requested:
                return
            result = run_gold_outlook(
                symbol=self.symbol,
                days=self.days,
                settings=settings,
                context_payload=context_payload,
                history=context_history,
            )
            if self._cancel_requested:
                return
            logs = log_buffer.getvalue()
            chart_path = self._find_chart_path()
            if self._cancel_requested:
                return
            if chart_path:
                self.signals.chart.emit(chart_path)
            if not self._cancel_requested:
                self.signals.finished.emit(result, logs, chart_path)
        except HardRiskBreachError as exc:
            if self._cancel_requested:
                return
            logs = log_buffer.getvalue()
            chart_path = self._find_chart_path()
            payload: Dict[str, Any] = {}
            if isinstance(exc.partial_result, dict):
                payload = dict(exc.partial_result)
            if context_payload and "context" not in payload:
                payload["context"] = context_payload
            payload.setdefault("hard_risk_breach", True)
            payload.setdefault("hard_risk_message", str(exc))
            if chart_path:
                self.signals.chart.emit(chart_path)
            self.signals.finished.emit(payload, logs, chart_path)
        except Exception:  # pragma: no cover - surfaced via GUI
            if self._cancel_requested:
                return
            error_text = traceback.format_exc()
            self.signals.error.emit(error_text)
        finally:
            sys.stdout = original_stdout  # type: ignore[assignment]
            sys.stderr = original_stderr  # type: ignore[assignment]
            logging_utils.configure_logging = original_configure  # type: ignore[assignment]
            root_logger = logging.getLogger()
            if handler in root_logger.handlers:
                root_logger.removeHandler(handler)
            handler.close()

    def _find_chart_path(self) -> str:
        outputs_dir = Path(__file__).resolve().parents[2] / "outputs"
        candidate = outputs_dir / f"{self.symbol.lower()}_close.png"
        return str(candidate) if candidate.exists() else ""


class MainWindow(QMainWindow):
    """Main application window for interacting with the workflow."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("AutoGen 金市晨会助手")
        self.resize(1100, 750)

        self.thread_pool = QThreadPool()
        self.chart_pixmap: QPixmap | None = None

        self.symbol_edit = QLineEdit("XAUUSD")
        self.days_spin = QSpinBox()
        self.days_spin.setRange(1, 365)
        self.days_spin.setValue(14)

        self.run_button = QPushButton("运行工作流")
        self.run_button.clicked.connect(self._handle_run_clicked)
        self.cancel_button = QPushButton("强制结束")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self._handle_cancel_clicked)

        form_layout = QFormLayout()
        form_layout.addRow("交易品种", self.symbol_edit)
        form_layout.addRow("回看天数", self.days_spin)

        controls_layout = QHBoxLayout()
        controls_layout.addLayout(form_layout)
        controls_layout.addWidget(self.run_button, alignment=Qt.AlignmentFlag.AlignLeft)
        controls_layout.addWidget(self.cancel_button, alignment=Qt.AlignmentFlag.AlignLeft)
        controls_layout.addStretch()

        # Summary tab
        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        summary_tab = QWidget()
        summary_layout = QVBoxLayout(summary_tab)
        summary_layout.addWidget(self.summary_text)

        # Details tab
        self.detail_tree = QTreeWidget()
        self.detail_tree.setHeaderLabels(["键", "取值"])
        self.detail_tree.header().setStretchLastSection(True)
        details_tab = QWidget()
        details_layout = QVBoxLayout(details_tab)
        details_layout.addWidget(self.detail_tree)

        # Raw JSON tab
        self.json_text = QTextEdit()
        self.json_text.setReadOnly(True)
        json_tab = QWidget()
        json_layout = QVBoxLayout(json_tab)
        json_layout.addWidget(self.json_text)

        # Logs tab
        self.logs_text = QTextEdit()
        self.logs_text.setReadOnly(True)
        logs_tab = QWidget()
        logs_layout = QVBoxLayout(logs_tab)
        logs_layout.addWidget(self.logs_text)

        # News tab
        self.news_info_label = QLabel("暂无新闻数据")
        self.news_info_label.setWordWrap(True)
        self.news_tree = QTreeWidget()
        self.news_tree.setHeaderLabels(["来源", "标题", "情绪分数", "发布时间"])
        self.news_tree.header().setStretchLastSection(True)
        self.news_tree.setUniformRowHeights(True)
        self.news_tree.setColumnWidth(0, 120)
        self.news_tree.itemActivated.connect(self._open_news_url)
        news_tab = QWidget()
        news_layout = QVBoxLayout(news_tab)
        news_layout.addWidget(self.news_info_label)
        news_layout.addWidget(self.news_tree)

        # Handoff tab
        self.handoff_tree = QTreeWidget()
        self.handoff_tree.setHeaderLabels(["来源代理", "下一代理", "说明"])
        self.handoff_tree.header().setStretchLastSection(True)
        handoff_tab = QWidget()
        handoff_layout = QVBoxLayout(handoff_tab)
        handoff_layout.addWidget(self.handoff_tree)

        # Chart tab
        self.chart_label = QLabel("暂无图表输出")
        self.chart_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.chart_label.setMinimumHeight(280)
        chart_tab = QWidget()
        chart_layout = QVBoxLayout(chart_tab)
        chart_layout.addWidget(self.chart_label)

        self.tabs = QTabWidget()
        self.tabs.addTab(summary_tab, "概要")
        self.tabs.addTab(details_tab, "结构化明细")
        self.tabs.addTab(json_tab, "原始 JSON")
        self.tabs.addTab(logs_tab, "运行日志")
        self.tabs.addTab(news_tab, "新闻资讯")
        self.tabs.addTab(handoff_tab, "代理交接")
        self.tabs.addTab(chart_tab, "价格图表")

        central_widget = QWidget()
        central_layout = QVBoxLayout(central_widget)
        central_layout.addLayout(controls_layout)
        central_layout.addWidget(self.tabs)

        self.setCentralWidget(central_widget)
        self.setStatusBar(QStatusBar())

        self._handoff_sender: str | None = None
        self._sender_regex = re.compile(r"sender=([A-Za-z0-9_]+)")
        self._route_scribe_regex = re.compile(r"路由至书记官，来源代理：([A-Za-z0-9_]+)")
        self._scribe_route_regex = re.compile(r"书记官(?:遵循提示路由至|按预设顺序路由至)：([A-Za-z0-9_]+)")
        self._next_regex = re.compile(r"Next speaker:\s*([A-Za-z0-9_]+)")
        self._chart_saved_regex = re.compile(r"价格曲线已保存：\s*(.+)$")
        self._active_worker: WorkflowWorker | None = None
        self._worker_signal_refs: Dict[int, Dict[str, Callable[..., None]]] = {}

    def _handle_run_clicked(self) -> None:
        if self._active_worker is not None:
            QMessageBox.information(self, "任务进行中", "当前仍有工作流在运行，请先等待或强制结束。")
            return
        symbol = self.symbol_edit.text().strip().upper()
        if not symbol:
            QMessageBox.warning(self, "输入错误", "请填写交易品种代码，例如 XAUUSD。")
            return
        days = int(self.days_spin.value())
        had_previous_results = self._prepare_for_run()
        if had_previous_results:
            self.statusBar().showMessage("工作流执行中（显示为上一轮结果），请稍候…")
        else:
            self.statusBar().showMessage("工作流执行中，请稍候…")
        self.run_button.setEnabled(False)
        self.logs_text.clear()

        worker = WorkflowWorker(symbol, days)
        self._active_worker = worker
        self._connect_worker_signals(worker)
        self.cancel_button.setEnabled(True)
        self.logs_text.append("=== 启动新一轮工作流 ===\n")
        self.thread_pool.start(worker)

    def _on_worker_finished(
        self, worker: WorkflowWorker, result: Dict[str, Any], logs: str, chart_path: str
    ) -> None:
        if self._active_worker is not worker or worker.is_cancelled:
            return
        self._disconnect_worker_signals(worker)
        self._active_worker = None
        self.cancel_button.setEnabled(False)
        self.run_button.setEnabled(True)
        self._on_workflow_finished(result, logs, chart_path)
        if self._is_hard_risk_breach(result):
            message = result.get("hard_risk_message") or "流程因硬风控终止，已保留当前结果。"
            self.statusBar().showMessage(message, 7000)
            QMessageBox.warning(self, "硬风控触发", message)
        else:
            self.statusBar().showMessage("工作流执行完成", 5000)

    def _on_workflow_finished(self, result: Dict[str, Any], logs: str, chart_path: str) -> None:
        final_payload = self._extract_final_payload(result)

        if final_payload is not None:
            self._update_summary(final_payload)
            self._populate_tree(final_payload)
            self.json_text.setPlainText(json.dumps(final_payload, indent=2, ensure_ascii=False))
        else:
            fallback_text = "尚未生成最终报告。请查看日志了解详情。"
            self._update_summary({"summary": fallback_text})
            self._populate_tree(result)
            try:
                self.json_text.setPlainText(json.dumps(result, indent=2, ensure_ascii=False))
            except Exception:
                self.json_text.setPlainText(fallback_text)
        self.logs_text.setPlainText(logs if logs.strip() else "（无日志输出）")
        self._populate_news(result.get("context"))

        if chart_path:
            self._update_chart_from_path(chart_path)
        else:
            self.chart_pixmap = None
            self.chart_label.setText("暂无图表输出")

    def _on_worker_error(self, worker: WorkflowWorker, error: str) -> None:
        if self._active_worker is not worker or worker.is_cancelled:
            return
        self._disconnect_worker_signals(worker)
        self._active_worker = None
        self.cancel_button.setEnabled(False)
        self.run_button.setEnabled(True)
        self.statusBar().clearMessage()
        QMessageBox.critical(self, "运行失败", error)
        if not self.news_tree.topLevelItemCount():
            self.news_info_label.setText("工作流失败，未获取到新闻数据")

    def _append_log_line(self, line: str) -> None:
        if not line:
            return
        cursor = self.logs_text.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(line)
        self.logs_text.setTextCursor(cursor)
        self.logs_text.ensureCursorVisible()
        self._maybe_refresh_chart_from_log(line)
        self._process_handoff_from_log(line)

    def _on_worker_log(self, worker: WorkflowWorker, line: str) -> None:
        if self._active_worker is not worker or worker.is_cancelled:
            return
        self._append_log_line(line)

    def _on_worker_chart(self, worker: WorkflowWorker, chart_path: str) -> None:
        if self._active_worker is not worker or worker.is_cancelled:
            return
        self._update_chart_from_path(chart_path)

    def _on_worker_context(self, worker: WorkflowWorker, context: Dict[str, Any]) -> None:
        if self._active_worker is not worker or worker.is_cancelled:
            return
        self._populate_news(context)
        self.statusBar().showMessage("新闻资讯已更新（实时刷新）", 3000)

    def _update_chart_from_path(self, chart_path: str) -> None:
        pixmap = QPixmap(chart_path)
        if not pixmap.isNull():
            self.chart_pixmap = pixmap
            self._update_chart_pixmap()
            self.chart_label.setToolTip(chart_path)
        else:
            self.chart_pixmap = None
            self.chart_label.setText("图表加载失败")

    def _process_handoff_from_log(self, line: str) -> None:
        line_stripped = line.strip()
        if not line_stripped:
            return

        sender_match = self._sender_regex.search(line_stripped)
        if sender_match:
            self._handoff_sender = sender_match.group(1)

        route_scribe_match = self._route_scribe_regex.search(line_stripped)
        if route_scribe_match:
            source = route_scribe_match.group(1)
            self._add_handoff_item(source, "ScribeAgent", line_stripped)
            self._handoff_sender = "ScribeAgent"

        scribe_route_match = self._scribe_route_regex.search(line_stripped)
        if scribe_route_match:
            target = scribe_route_match.group(1)
            source = self._handoff_sender or "ScribeAgent"
            self._add_handoff_item(source, target, line_stripped)
            self._handoff_sender = target

        next_match = self._next_regex.search(line_stripped)
        if next_match:
            target = next_match.group(1)
            source = self._handoff_sender or "系统"
            self._add_handoff_item(source, target, line_stripped)
            self._handoff_sender = target

    def _add_handoff_item(self, source: str, target: str, note: str) -> None:
        item = QTreeWidgetItem([source, target, note])
        self.handoff_tree.addTopLevelItem(item)
        self.handoff_tree.scrollToItem(item)

    def _maybe_refresh_chart_from_log(self, line: str) -> None:
        match = self._chart_saved_regex.search(line.strip())
        if match:
            chart_path = match.group(1).strip()
            if chart_path:
                self._update_chart_from_path(chart_path)

    def _populate_news(self, context: Any) -> None:
        self.news_tree.clear()
        if not isinstance(context, dict):
            self.news_info_label.setText("未获取到新闻数据")
            return

        sentiment = context.get("news_sentiment")
        if not isinstance(sentiment, dict):
            self.news_info_label.setText("未获取到新闻数据")
            return

        score = sentiment.get("score")
        confidence = sentiment.get("confidence")
        classification = sentiment.get("classification")
        trend = sentiment.get("score_trend")
        topics = sentiment.get("topics") if isinstance(sentiment.get("topics"), list) else []

        info_parts: list[str] = []
        if isinstance(score, (int, float)):
            info_parts.append(f"综合得分：{score:.3f}")
        if isinstance(confidence, (int, float)):
            info_parts.append(f"置信度：{confidence:.3f}")
        if isinstance(classification, str):
            info_parts.append(f"情绪：{classification}")
        if isinstance(trend, (int, float)):
            info_parts.append(f"趋势：{trend:+.3f}")
        if topics:
            info_parts.append("主题关键词：" + ", ".join(str(topic) for topic in topics[:6]))
        if not info_parts:
            info_parts.append("暂无有效情绪指标")
        self.news_info_label.setText("；".join(info_parts))

        headlines = sentiment.get("headlines")
        if not isinstance(headlines, list) or not headlines:
            empty_item = QTreeWidgetItem(["-", "暂无新闻", "-", "-"])
            self.news_tree.addTopLevelItem(empty_item)
            return

        for entry in headlines:
            if not isinstance(entry, dict):
                continue
            source = str(entry.get("source") or "-")
            title = str(entry.get("title") or "(无标题)")
            score_value = entry.get("score")
            score_text = f"{score_value:.3f}" if isinstance(score_value, (int, float)) else "-"
            published = str(entry.get("published") or "-")
            item = QTreeWidgetItem([source, title, score_text, published])
            summary = entry.get("summary")
            if isinstance(summary, str) and summary.strip():
                tooltip = summary.strip()
                item.setToolTip(0, tooltip)
                item.setToolTip(1, tooltip)
            url = entry.get("url")
            if isinstance(url, str) and url.strip():
                clean_url = url.strip()
                item.setData(0, Qt.ItemDataRole.UserRole, clean_url)
                item.setData(1, Qt.ItemDataRole.UserRole, clean_url)
                item.setToolTip(2, clean_url)
            self.news_tree.addTopLevelItem(item)

        self.news_tree.resizeColumnToContents(0)
        self.news_tree.resizeColumnToContents(2)
        self.news_tree.scrollToTop()

    def _open_news_url(self, item: QTreeWidgetItem, column: int) -> None:
        if item is None:
            return
        url = item.data(0, Qt.ItemDataRole.UserRole)
        if not isinstance(url, str) or not url.strip():
            url = item.data(1, Qt.ItemDataRole.UserRole)
        if isinstance(url, str) and url.strip():
            QDesktopServices.openUrl(QUrl(url.strip()))

    def _prepare_for_run(self) -> bool:
        self.logs_text.clear()
        self.handoff_tree.clear()
        self._handoff_sender = None
        if self.chart_pixmap:
            self._update_chart_pixmap()
        had_results = bool(
            self.summary_text.toPlainText()
            or self.detail_tree.topLevelItemCount()
            or self.json_text.toPlainText()
            or self.chart_pixmap
            or self.news_tree.topLevelItemCount()
        )
        self.news_tree.clear()
        self.news_info_label.setText("正在获取最新新闻……")
        return had_results

    def _handle_cancel_clicked(self) -> None:
        if not self._active_worker:
            return
        worker = self._active_worker
        worker.request_cancel()
        self._disconnect_worker_signals(worker)
        self._active_worker = None
        self.run_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.statusBar().showMessage("已强制结束当前任务", 5000)
        self.logs_text.append("\n=== 本轮工作流已强制结束 ===\n")
        self.news_info_label.setText("本轮已强制结束，列表保留上一轮新闻数据")

    def _connect_worker_signals(self, worker: WorkflowWorker) -> None:
        worker_id = id(worker)
        slots: Dict[str, Callable[..., None]] = {}
        log_slot = partial(self._on_worker_log, worker)
        worker.signals.log.connect(log_slot)
        slots["log"] = log_slot

        finish_slot = partial(self._on_worker_finished, worker)
        worker.signals.finished.connect(finish_slot)
        slots["finished"] = finish_slot

        error_slot = partial(self._on_worker_error, worker)
        worker.signals.error.connect(error_slot)
        slots["error"] = error_slot

        chart_slot = partial(self._on_worker_chart, worker)
        worker.signals.chart.connect(chart_slot)
        slots["chart"] = chart_slot

        context_slot = partial(self._on_worker_context, worker)
        worker.signals.context.connect(context_slot)
        slots["context"] = context_slot

        self._worker_signal_refs[worker_id] = slots

    def _disconnect_worker_signals(self, worker: WorkflowWorker) -> None:
        worker_id = id(worker)
        slots = self._worker_signal_refs.pop(worker_id, {})
        for name, slot in slots.items():
            try:
                if name == "log":
                    worker.signals.log.disconnect(slot)
                elif name == "finished":
                    worker.signals.finished.disconnect(slot)
                elif name == "error":
                    worker.signals.error.disconnect(slot)
                elif name == "chart":
                    worker.signals.chart.disconnect(slot)
                elif name == "context":
                    worker.signals.context.disconnect(slot)
            except (TypeError, RuntimeError):  # signal already disconnected or worker done
                continue

    @staticmethod
    def _is_hard_risk_breach(result: Dict[str, Any]) -> bool:
        if not isinstance(result, dict):
            return False
        if result.get("hard_risk_breach"):
            return True
        gate = result.get("hard_risk_gate")
        if isinstance(gate, dict) and gate.get("breached"):
            return True
        return False

    @staticmethod
    def _extract_final_payload(result: Dict[str, Any]) -> Dict[str, Any] | None:
        if not isinstance(result, dict):
            return None
        parsed = result.get("response_parsed")
        if isinstance(parsed, dict):
            return parsed
        raw = result.get("response")
        if isinstance(raw, dict):
            return raw
        if isinstance(raw, str) and raw.strip():
            try:
                candidate = json.loads(raw)
                if isinstance(candidate, dict):
                    return candidate
            except Exception:
                return None
        return None

    def _update_summary(self, result: Dict[str, Any]) -> None:
        phase = result.get("phase")
        status = result.get("status")
        summary = result.get("summary")
        details = result.get("details") if isinstance(result.get("details"), dict) else {}

        lines = []
        if phase:
            lines.append(f"阶段：{phase}")
        if status:
            lines.append(f"状态：{status}")
        if summary:
            lines.append(f"摘要：{summary}")

        if details:
            highlights = []
            for key, value in details.items():
                if isinstance(value, (str, int, float)):
                    highlights.append(f"{key}: {value}")
                elif isinstance(value, list):
                    highlights.append(f"{key}: {len(value)} 条")
                elif isinstance(value, dict):
                    highlights.append(f"{key}: {len(value)} 项")
            if highlights:
                lines.append("详情概览：")
                lines.extend(f"  - {item}" for item in highlights[:10])
        self.summary_text.setPlainText("\n".join(lines))

    def _populate_tree(self, data: Any, parent: QTreeWidgetItem | None = None) -> None:
        if parent is None:
            self.detail_tree.clear()
        current_parent = parent or self.detail_tree.invisibleRootItem()

        if isinstance(data, dict):
            for key, value in data.items():
                child = QTreeWidgetItem([str(key), self._format_leaf(value)])
                current_parent.addChild(child)
                if isinstance(value, (dict, list)):
                    child.setText(1, "")
                    self._populate_tree(value, child)
        elif isinstance(data, list):
            for index, value in enumerate(data):
                child = QTreeWidgetItem([f"[{index}]", self._format_leaf(value)])
                current_parent.addChild(child)
                if isinstance(value, (dict, list)):
                    child.setText(1, "")
                    self._populate_tree(value, child)

        if parent is None:
            self.detail_tree.expandAll()

    @staticmethod
    def _format_leaf(value: Any) -> str:
        if value is None:
            return "null"
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, (dict, list)):
            return ""
        return str(value)

    def resizeEvent(self, event) -> None:  # pragma: no cover - UI behavior
        super().resizeEvent(event)
        self._update_chart_pixmap()

    def _update_chart_pixmap(self) -> None:
        if self.chart_pixmap:
            self.chart_label.setPixmap(
                self.chart_pixmap.scaled(
                    self.chart_label.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )


def main() -> None:  # pragma: no cover - entry point
    app = QApplication.instance() or QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":  # pragma: no cover - script execution
    main()
