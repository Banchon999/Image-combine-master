"""Auto-align properties controller and optional Qt panel."""

import threading

from ...alignment.auto import align_automatically
from ...pipeline import CancelToken, Cancelled


class AutoAlignController:
    """Run a backend away from the UI thread and marshal only its outcome back.

    ``dispatch`` must schedule a callable on the UI event loop (Qt callers use
    a signal); it defaults to direct dispatch for headless applications/tests.
    Images and layers remain owned by the caller. The worker returns only a
    transform or an exception.
    """

    def __init__(self, dispatch=None):
        self.dispatch = dispatch or (lambda callback: callback())
        self.cancel_token = None
        self.thread = None

    @property
    def running(self):
        return self.thread is not None and self.thread.is_alive()

    def start(self, source_layer, reference_layer, backend=None,
              on_done=None, on_error=None):
        if self.running:
            raise RuntimeError("auto-alignment is already running")
        self.cancel_token = CancelToken()
        source, reference = source_layer.image, reference_layer.image

        def work():
            try:
                result = align_automatically(source, reference, backend,
                                             self.cancel_token)
            except Cancelled:
                return
            except Exception as error:
                if on_error:
                    self.dispatch(lambda: on_error(error))
            else:
                # Mutation occurs in this dispatched UI-thread callback only.
                def apply_result():
                    source_layer.transform = result
                    if on_done:
                        on_done(result)
                self.dispatch(apply_result)

        self.thread = threading.Thread(target=work, name="imbine-auto-align",
                                       daemon=True)
        self.thread.start()
        return self.thread

    def cancel(self):
        if self.cancel_token is not None:
            self.cancel_token.cancel()


try:
    from PySide6.QtCore import Signal
    from PySide6.QtWidgets import QCheckBox, QLabel, QVBoxLayout, QWidget
except ImportError:
    AlignmentPropertiesPanel = None
else:
    class AlignmentPropertiesPanel(QWidget):
        """Properties widget whose toggle starts/cancels the worker."""

        resultReady = Signal(object)
        errorReady = Signal(object)

        def __init__(self, parent=None):
            super().__init__(parent)
            self.source_layer = self.reference_layer = None
            self.backend = None
            self.status = QLabel("Auto-align is off")
            self.auto_toggle = QCheckBox("Auto-Align")
            layout = QVBoxLayout(self)
            layout.addWidget(self.auto_toggle)
            layout.addWidget(self.status)
            self.controller = AutoAlignController(
                lambda callback: self.resultReady.emit(callback))
            self.resultReady.connect(lambda callback: callback())
            self.errorReady.connect(self._show_error)
            self.auto_toggle.toggled.connect(self._toggle)

        def set_layers(self, source, reference):
            self.source_layer, self.reference_layer = source, reference

        def _toggle(self, enabled):
            if not enabled:
                self.controller.cancel()
                self.status.setText("Auto-align cancelled")
                return
            if self.source_layer is None or self.reference_layer is None:
                self.status.setText("Choose source and reference layers first")
                self.auto_toggle.setChecked(False)
                return
            self.status.setText("Auto-aligning…")
            self.controller.start(
                self.source_layer, self.reference_layer, self.backend,
                on_done=lambda result: self.status.setText("Auto-align complete"),
                on_error=lambda error: self.errorReady.emit(error))

        def _show_error(self, error):
            self.status.setText(str(error))
            self.auto_toggle.setChecked(False)
