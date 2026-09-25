"""Редактор рандома -- «Создать рандом»/«Редактировать рандом» из ПКМ на
чипе плейсхолдера в реквизитах конструктора документов (см.
src/ui/main_window.py, _show_chip_context_menu()/_open_random_editor()).

Оператор задаёт тип числа (целое / с плавающей точкой), нижнюю и верхнюю
границы, шаг и -- только для вещественных -- количество знаков после
запятой. Диалог сам ничего не сохраняет: после exec()==Accepted вызывающая
сторона читает `removed` (убрать рандом у поля) либо `spec` (см.
src/services/random_spec.py)."""

from typing import Dict, Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QPushButton,
    QComboBox, QDoubleSpinBox, QSpinBox, QMessageBox,
)

from ..services.random_spec import (
    MAX_DECIMALS, default_random_spec, generate_random_value, validate_random_spec,
)

_QSS = """
QDialog { background: #1c1c1e; }
QDialog QLabel { color: #c7c7cc; font-size: 12px; }
QLabel#randomTitle { color: #e5e5e7; font-size: 13px; font-weight: 600; }
QLabel#randomHint { color: #8e8e93; font-size: 10.5px; }
QLabel#randomPreview { color: #e5e5e7; font-weight: 500; }
QComboBox, QDoubleSpinBox, QSpinBox {
    background: #242426; border: 0.5px solid #38383a; border-radius: 6px;
    color: #e5e5e7; padding: 4px 8px; min-height: 20px;
}
QComboBox:focus, QDoubleSpinBox:focus, QSpinBox:focus { border-color: #0a84ff; }
QComboBox:disabled, QSpinBox:disabled { color: #5a5a5c; }
QPushButton {
    background: #242426; border: 0.5px solid #38383a; color: #c7c7cc;
    padding: 6px 12px; border-radius: 6px;
}
QPushButton:hover { background: #3a3a3c; color: #e5e5e7; }
"""

_BOUND_LIMIT = 1_000_000_000
_INPUT_DECIMALS = 6


class RandomEditorDialog(QDialog):
    """См. докстринг модуля."""

    def __init__(self, field_label: str, existing_spec: Optional[Dict] = None, parent=None):
        super().__init__(parent)
        self.removed = False
        self.spec: Dict = dict(existing_spec) if existing_spec else default_random_spec()

        self.setWindowTitle("Редактор рандома")
        self.setStyleSheet(_QSS)
        self.setMinimumWidth(380)
        self._build_ui(field_label, existing_spec is not None)
        self._apply_kind()
        self._update_preview()

    def _build_ui(self, field_label: str, has_existing: bool):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)

        title = QLabel("Редактор рандома")
        title.setObjectName("randomTitle")
        layout.addWidget(title)
        hint = QLabel(f"Поле: {field_label}")
        hint.setObjectName("randomHint")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        form = QFormLayout()
        form.setSpacing(8)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        layout.addLayout(form)

        self._kind_combo = QComboBox()
        self._kind_combo.addItem("Целое число", "int")
        self._kind_combo.addItem("С плавающей точкой", "float")
        self._kind_combo.setCurrentIndex(0 if self.spec["kind"] == "int" else 1)
        form.addRow("Тип числа", self._kind_combo)

        self._low_spin = self._make_spin(self.spec["low"])
        self._high_spin = self._make_spin(self.spec["high"])
        self._step_spin = self._make_spin(self.spec["step"])
        form.addRow("Нижняя граница", self._low_spin)
        form.addRow("Верхняя граница", self._high_spin)
        form.addRow("Шаг", self._step_spin)

        self._decimals_spin = QSpinBox()
        self._decimals_spin.setRange(0, MAX_DECIMALS)
        self._decimals_spin.setValue(int(self.spec.get("decimals", 2)))
        form.addRow("Знаков после запятой", self._decimals_spin)

        self._preview_label = QLabel()
        self._preview_label.setObjectName("randomPreview")
        form.addRow("Пример значения", self._preview_label)

        self._kind_combo.currentIndexChanged.connect(self._apply_kind)
        for widget in (self._low_spin, self._high_spin, self._step_spin):
            widget.valueChanged.connect(self._update_preview)
        self._decimals_spin.valueChanged.connect(self._update_preview)

        buttons = QHBoxLayout()
        if has_existing:
            remove_btn = QPushButton("Убрать рандом")
            remove_btn.setStyleSheet("QPushButton{background:transparent; border:none; color:#ff453a;}")
            remove_btn.clicked.connect(self._on_remove)
            buttons.addWidget(remove_btn)
        buttons.addStretch()
        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton("Сохранить")
        save_btn.setDefault(True)
        save_btn.setStyleSheet(
            "QPushButton{background:#0a84ff; border:none; color:#fff; font-weight:500; "
            "padding:6px 12px; border-radius:6px;} QPushButton:hover{background:#3391ff;}"
        )
        save_btn.clicked.connect(self._on_save)
        buttons.addWidget(cancel_btn)
        buttons.addWidget(save_btn)
        layout.addLayout(buttons)

    @staticmethod
    def _make_spin(value: float) -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setRange(-_BOUND_LIMIT, _BOUND_LIMIT)
        spin.setDecimals(_INPUT_DECIMALS)
        spin.setValue(float(value))
        spin.setStepType(QDoubleSpinBox.StepType.AdaptiveDecimalStepType)
        return spin

    def _is_int(self) -> bool:
        return self._kind_combo.currentData() == "int"

    def _apply_kind(self):
        """Целое -- границы/шаг без дробной части, знаки после запятой
        недоступны; вещественное -- полная точность ввода."""
        is_int = self._is_int()
        for spin in (self._low_spin, self._high_spin, self._step_spin):
            spin.setDecimals(0 if is_int else _INPUT_DECIMALS)
        self._decimals_spin.setEnabled(not is_int)
        self._update_preview()

    def _current_spec(self) -> Dict:
        return {
            "kind": self._kind_combo.currentData(),
            "low": self._low_spin.value(),
            "high": self._high_spin.value(),
            "step": self._step_spin.value(),
            "decimals": self._decimals_spin.value(),
        }

    def _update_preview(self):
        spec = self._current_spec()
        error = validate_random_spec(spec)
        self._preview_label.setText(f"⚠ {error}" if error else generate_random_value(spec))

    def _on_save(self):
        spec = self._current_spec()
        error = validate_random_spec(spec)
        if error:
            QMessageBox.warning(self, "Редактор рандома", error)
            return
        if spec["kind"] == "int":
            spec = {**spec, "low": int(spec["low"]), "high": int(spec["high"]), "step": int(spec["step"])}
        self.spec = spec
        self.accept()

    def _on_remove(self):
        self.removed = True
        self.accept()
