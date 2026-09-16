"""Открытие файла с явным выбором приложения (Word, Pages, OnlyOffice,
LibreOffice, ...) -- в отличие от QDesktopServices.openUrl(), который молча
открывает системным приложением по умолчанию без выбора.

В Qt нет кросс-платформенного диалога выбора приложения, поэтому на каждой
ОС используется её штатный системный диалог «Открыть с помощью»:
  - macOS: AppleScript "choose file" с фильтром по типу
    "com.apple.application-bundle" и стартовой папкой /Applications --
    обычный файловый диалог выбора (НЕ "choose application": та команда
    возвращает ссылку на приложение, а не файловый путь, и превращение её
    в путь ("as alias"/"as text") ненадёжно -- реально наблюдалось на
    ONLYOFFICE: "as alias" падает с error -1700, "as text" вместо полного
    пути отдаёт голое имя приложения без каталога, дальше open -a получает
    мусорный путь и не находит файл). POSIX path of результата choose file
    всегда реальный, рабочий путь. Выбранный путь запоминается
    (PREFERRED_EDITOR_FILE, src/config.py) -- следующий вызов на этой ОС
    открывает тем же приложением напрямую (простой `open -a <app> <file>`,
    без AppleScript и без диалога), пока файл приложения не пропадёт с
    диска или сам не откажется открыть файл (тогда диалог выбора
    показывается заново).
  - Windows: rundll32 shell32.dll,OpenAs_RunDLL -- системный диалог
    «Открыть с помощью». Запомнить выбор здесь НЕЛЬЗЯ: диалог асинхронный,
    им управляет Проводник, и то, что пользователь в итоге выбрал, этому
    процессу не возвращается -- каждый вызов на Windows спрашивает заново.
  - остальные (Linux и т.п.): устойчивого штатного эквивалента нет,
    используется QDesktopServices.openUrl() (приложение по умолчанию без
    выбора) как честный fallback -- запоминать нечего, выбора и так нет."""

import json
import subprocess
import sys
from pathlib import Path

from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QMessageBox, QWidget

from ..config import PREFERRED_EDITOR_FILE


def _load_remembered_app() -> str:
    if not PREFERRED_EDITOR_FILE.exists():
        return ""
    try:
        data = json.loads(PREFERRED_EDITOR_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    return data.get("app_path", "")


def _remember_app(app_path: str) -> None:
    PREFERRED_EDITOR_FILE.parent.mkdir(parents=True, exist_ok=True)
    PREFERRED_EDITOR_FILE.write_text(
        json.dumps({"app_path": app_path}, ensure_ascii=False), encoding="utf-8"
    )


def open_with_prompt(path: Path, parent: QWidget = None) -> None:
    if sys.platform == "darwin":
        remembered = _load_remembered_app()
        if remembered and Path(remembered).exists():
            result = subprocess.run(["open", "-a", remembered, str(path)], capture_output=True, text=True)
            if result.returncode == 0:
                return
            # Запомненное приложение пропало или не смогло открыть файл --
            # не молчим, спрашиваем заново тем же диалогом, что и при
            # самом первом открытии (код ниже).

        escaped = str(path).replace("\\", "\\\\").replace('"', '\\"')
        script = (
            'set appFile to choose file with prompt "Открыть документ в приложении:" '
            'of type {"com.apple.application-bundle"} default location (path to applications folder)\n'
            'set appPath to POSIX path of appFile\n'
            f'do shell script "open -a " & quoted form of appPath & " " & quoted form of "{escaped}"\n'
            'return appPath'
        )
        result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
        if result.returncode != 0:
            stderr = (result.stderr or "").strip()
            if "-128" in stderr:
                return  # пользователь отменил выбор приложения -- не ошибка
            QMessageBox.warning(
                parent, "Не удалось открыть документ",
                stderr or "Неизвестная ошибка при попытке открыть файл выбранным приложением.",
            )
            return
        chosen_app = (result.stdout or "").strip()
        if chosen_app:
            _remember_app(chosen_app)
    elif sys.platform == "win32":
        subprocess.run(["rundll32.exe", "shell32.dll,OpenAs_RunDLL", str(path)])
    else:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
