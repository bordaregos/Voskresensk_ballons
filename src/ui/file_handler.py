"""Импорт и экспорт данных в UI."""

from pathlib import Path
from typing import List, Dict, Any

from PyQt6.QtWidgets import QFileDialog, QMessageBox, QTableWidgetItem, QDialog

from src.services.importer import (
    import_balloon_list_from_csv,
)
from src.services.exporter import (
    export_balloon_list_to_csv,
)
from src.models.project import Project
from src.config import OUTPUT_DIR
from src.ui.widget_names_pipeline import SEGMENT_TYPES, AE_CLASS_TYPES


class FileHandler:
    """Обработчик файлов для импорта/экспорта."""
    
    def __init__(self, main_window):
        """
        Инициализация обработчика файлов.
        
        Args:
            main_window: Экземпляр MainWindow
        """
        self.main_window = main_window
    
    def import_csv_balloon_list(self):
        """
        Импорт списка баллонов из CSV файла.
        
        Открывает диалог выбора файла и загружает данные в таблицу баллонов.
        """
        file_path, _ = QFileDialog.getOpenFileName(
            self.main_window,
            "Выберите CSV файл с баллонами",
            str(OUTPUT_DIR),
            "CSV файлы (*.csv);;All files (*.*)"
        )
        
        if not file_path:
            return
        
        try:
            # Импорт данных
            balloons_data = import_balloon_list_from_csv(Path(file_path))
            
            if not balloons_data:
                self.main_window.show_message(
                    "Ошибка",
                    "Файл не содержит данных баллонов",
                    QMessageBox.Icon.Warning
                )
                return
            
            # Заполнение таблицы баллонов
            self._fill_balloon_table_from_data(balloons_data)
            
            self.main_window.show_message(
                "Успех",
                f"Загружено {len(balloons_data)} баллонов из CSV",
                QMessageBox.Icon.Information
            )
            
        except Exception as e:
            self.main_window.show_message(
                "Ошибка импорта",
                f"Ошибка при импорте CSV: {str(e)}",
                QMessageBox.Icon.Critical
            )
    
    def export_csv_balloon_list(self):
        """
        Экспорт списка баллонов в CSV файл.
        
        Сохраняет данные из таблицы баллонов в CSV файл.
        """
        file_path, _ = QFileDialog.getSaveFileName(
            self.main_window,
            "Выберите место для сохранения CSV",
            str(OUTPUT_DIR / "баллоны.csv"),
            "CSV файлы (*.csv);;All files (*.*)"
        )
        
        if not file_path:
            return
        
        try:
            # Получение данных из таблицы
            balloons_data = self._get_balloon_data_from_table()
            
            if not balloons_data:
                self.main_window.show_message(
                    "Ошибка",
                    "Таблица баллонов пуста",
                    QMessageBox.Icon.Warning
                )
                return
            
            # Экспорт в CSV
            export_balloon_list_to_csv(balloons_data, Path(file_path))
            
            self.main_window.show_message(
                "Успех",
                f"Данные сохранены в {file_path}",
                QMessageBox.Icon.Information
            )
            
        except Exception as e:
            self.main_window.show_message(
                "Ошибка экспорта",
                f"Ошибка при экспорте в CSV: {str(e)}",
                QMessageBox.Icon.Critical
            )
    
    def _save_current_project(self):
        """Сохраняет текущий документ в main_window._current_document_path
        напрямую, без диалога и без сообщения об успехе -- общая часть
        save_project_json() (когда путь уже есть) и тихого автосохранения
        при переключении документа в дереве объектов, см.
        MainWindow._open_document(). Вызывающая сторона отвечает за то,
        что _current_document_path не None."""
        project = self._create_project()
        project.save_to_file(self.main_window._current_document_path)
        # Индикатор несохранённых изменений (Фаза 5.4) -- есть только у
        # трубопровода; hasattr-проверка, чтобы не задевать баллоны.
        if hasattr(self.main_window, "_document_dirty"):
            self.main_window._document_dirty = False
            self.main_window._update_dirty_indicator()

    def _prompt_document_path(self) -> bool:
        """Для трубопровода и конструктора документов (у обоих есть
        дерево "папка -> документ", см. workspace.py) одним диалогом
        (см. src/ui/save_project_dialog.py:SaveProjectDialog) спрашивает
        имя файла и папку -- КАЖДЫЙ раз при явном нажатии «Сохранить
        проект», а не только при первой привязке. Папка выбирается из
        плоского списка ВСЕХ папок дерева произвольной вложенности (не
        только верхнего уровня, как было раньше) либо создаётся новая
        (всегда на верхнем уровне, см. SaveProjectDialog). Имя JSON-
        проекта должно всегда быть ручным вводом пользователя в диалоге
        сохранения, а не тихой перезаписью в уже известный путь.

        Если документ уже привязан к какой-то папке
        (main_window._current_document_path), эта папка предвыбрана в
        диалоге по умолчанию, на любой глубине вложенности -- но её всё
        равно можно сменить прямо тут же, без отдельного шага.

        Тихое автосохранение при переключении документа в дереве
        объектов (MainWindow._open_document()/_open_constructor_document()
        -> _save_current_project()) этот метод не вызывает и не
        затрагивает -- иначе каждый клик по дереву превращался бы в
        диалог.

        У баллонов концепции объектов/дерева нет; hasattr(mw, "objectsTree")
        как маркер "это окно с деревом" -- тот же приём, что и везде в
        этом файле (Фаза 5.4/6); save_project_json() вызывает этот метод
        только когда он истинен.

        Возвращает False, если пользователь отменил диалог -- вызывающая
        сторона обязана прервать сохранение целиком, не писать файл ни
        в старое, ни в частично выбранное новое место."""
        mw = self.main_window
        path = mw._current_document_path

        from src.services import workspace
        from src.ui.save_project_dialog import SaveProjectDialog

        default_folder = path.parent if path is not None else workspace.OUTPUT_DIR
        default_filename = path.stem if path is not None else "документ"

        dialog = SaveProjectDialog(mw, default_folder, default_filename, path)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return False
        folder_dir, filename = dialog.result_values()
        new_path = folder_dir / f"{workspace.sanitize_object_name(filename)}.json"

        mw._current_document_path = new_path
        mw._refresh_objects_tree()
        mw._update_breadcrumb()
        return True

    def save_project_json(self):
        """
        Сохранение проекта в JSON файл.

        Трубопровод и конструктор документов (hasattr(mw, "objectsTree") --
        оба используют одно и то же дерево "объект (папка) -> документ",
        см. src/services/workspace.py и MainWindow._refresh_objects_tree()):
        имя файла и папка-объект -- всегда ручной ввод пользователя в
        диалоге сохранения, см. _prompt_document_path(); не важно,
        сохранялся документ раньше в этом сеансе или нет -- тихой
        перезаписи в уже известный путь нет ни разу. Для конструктора это
        и есть «Сохранить проект спрашивает, в какую папку сохранить» --
        отдельного диалога выбора папки заводить не пришлось, тот же
        _prompt_document_path(), что и у трубопровода.

        Баллоны: поведение не менялось -- если main_window.
        _current_document_path уже указывает куда сохранять (документ
        уже сохранялся в этом сеансе), пишем туда напрямую без диалога;
        иначе -- обычный "Сохранить как", а выбранный путь запоминается
        как текущий документ.
        """
        mw = self.main_window
        uses_object_tree = hasattr(mw, "objectsTree")
        existing_path = getattr(mw, "_current_document_path", None)

        try:
            if uses_object_tree:
                old_path = existing_path
                if not self._prompt_document_path():
                    return
                self._save_current_project()
                file_path = str(mw._current_document_path)
                # Ввод другого имени в диалоге -- это переименование
                # текущего документа, а не сохранение копии: старый файл
                # под прежним именем не должен оставаться сиротой в
                # папке объекта (ярлык в дереве -- это и есть имя файла,
                # см. workspace.list_documents() -- сирота выглядела бы
                # как отдельный документ-дубликат).
                if old_path is not None and old_path != mw._current_document_path and old_path.exists():
                    old_path.unlink()
                    mw._refresh_objects_tree()
                    mw._update_breadcrumb()
            elif existing_path is not None:
                self._save_current_project()
                file_path = str(mw._current_document_path)
            else:
                file_path, _ = QFileDialog.getSaveFileName(
                    mw,
                    "Выберите место для сохранения проекта",
                    str(OUTPUT_DIR / "проект.json"),
                    "JSON файлы (*.json);;All files (*.*)"
                )
                if not file_path:
                    return

                project = self._create_project()
                project.save_to_file(Path(file_path))
                mw._current_document_path = Path(file_path)

            mw.show_message(
                "Успех",
                f"Проект сохранён в {file_path}",
                QMessageBox.Icon.Information
            )

        except Exception as e:
            self.main_window.show_message(
                "Ошибка",
                f"Ошибка при сохранении проекта: {str(e)}",
                QMessageBox.Icon.Critical
            )
    
    def open_project_json(self):
        """
        Загрузка проекта из JSON файла.
        
        Загружает все данные проекта из JSON файла.
        """
        file_path, _ = QFileDialog.getOpenFileName(
            self.main_window,
            "Выберите JSON файл проекта",
            str(OUTPUT_DIR),
            "JSON файлы (*.json);;All files (*.*)"
        )
        
        if not file_path:
            return
        
        try:
            # Загрузка проекта
            project = Project.load_from_file(Path(file_path))

            # Форма сбрасывается перед наполнением -- иначе поля/строки
            # таблиц, которых нет в загружаемом JSON (старый формат, ручное
            # редактирование файла и т.п.), остались бы от предыдущего
            # документа, а не были бы честно пустыми. См. _reset_form()/
            # _reset_constructor_form() (у конструктора свой сброс -- по
            # слотам title/intro, а не по спискам виджетов).
            if self.main_window.equipment_type.id == "pipeline":
                self.main_window._reset_form()
            elif self.main_window.equipment_type.id == "constructor":
                self.main_window._reset_constructor_form()

            # Заполнение UI данными
            self._fill_ui_from_project(project)
            self.main_window._current_document_path = Path(file_path)

            # table_specialists заполняется выше generic-веткой TABLE_WIDGET
            # (_fill_ui_from_project), но комбобоксы выбора специалиста
            # (program_specialist и т.п.) сами по себе не обновляются --
            # раньше это происходило при переключении вкладки, вкладок
            # больше нет, см. MainWindow._refresh_program_specialist_combo().
            # saved_indices -- какую строку table_specialists выбрать в
            # каждом комбобоксе -- восстанавливаем из report_data, иначе
            # выбор всегда откатывался на первую строку (комбобоксы ещё
            # пустые в момент _fill_ui_from_project(), собственного
            # "текущего выбора" сохранить не могут).
            if self.main_window.equipment_type.id == "pipeline":
                saved_indices = {
                    name: project.report_data.get(name)
                    for name in self.main_window.SPECIALIST_COMBO_NAMES
                }
                self.main_window._refresh_program_specialist_combo(saved_indices)

            self.main_window.show_message(
                "Успех",
                f"Проект загружен из {file_path}",
                QMessageBox.Icon.Information
            )
            
        except Exception as e:
            self.main_window.show_message(
                "Ошибка",
                f"Ошибка при загрузке проекта: {str(e)}",
                QMessageBox.Icon.Critical
            )
    
    def _fill_balloon_table_from_data(self, balloons_data: List[Dict[str, Any]]):
        """
        Заполнение таблицы баллонов данными из списка.
        
        Args:
            balloons_data: Список словарей с данными баллонов
        """
        table = self.main_window.table_ballons
        table.setRowCount(len(balloons_data))
        
        for row, balloon_data in enumerate(balloons_data):
            # Заводской номер
            serial = balloon_data.get('serial_number', '')
            item = QTableWidgetItem(str(serial))
            table.setItem(row, 0, item)
            
            # Минимальная толщина (если есть)
            min_thick = balloon_data.get('min_thickness')
            if min_thick is not None:
                item = QTableWidgetItem(str(min_thick).replace('.', ','))
                table.setItem(row, 1, item)
            
            # Год изготовления - миграция старого формата
            # В старом JSON: max_thickness содержал год, year_of_manufacture сод��ржал массу
            # В новом JSON: year_of_manufacture - год, mass - масса
            
            # 1. Сначала проверяем max_thickness на год (старый формат)
            year = None
            max_thick_val = balloon_data.get('max_thickness')
            if max_thick_val is not None:
                val = float(str(max_thick_val).replace(',', '.'))
                if val > 1900:  # это год в старом формате
                    year = int(val)
                elif val < 100:  # это толщина
                    item = QTableWidgetItem(str(val).replace('.', ','))
                    table.setItem(row, 1, item)
            
            # 2. Проверяем year_of_manufacture (может быть масса в старом формате)
            # В старом формате year_of_manufacture содержал массу, а не год
            year_val = balloon_data.get('year_of_manufacture')
            if year_val is not None:
                val = float(str(year_val).replace(',', '.'))
                if val > 1900:  # это год (новый формат)
                    if year is None:  # не нашли год в max_thickness
                        year = int(val)
                elif val < 100:  # это масса (в старом или новом формате)
                    mass = val
                    item = QTableWidgetItem(str(mass).replace('.', ','))
                    table.setItem(row, 3, item)
            
            # 3. Если год найден, заполняем его в таблицу
            if year is not None:
                item = QTableWidgetItem(str(year))
                table.setItem(row, 2, item)
            
            # 4. Проверяем mass (новый формат)
            mass = balloon_data.get('mass')
            if mass is not None:
                item = QTableWidgetItem(str(mass).replace('.', ','))
                if table.item(row, 3) is None:  # не заполнили уже
                    table.setItem(row, 3, item)
            
            # Масса - пытаемся найти в mass
            mass = balloon_data.get('mass')
            if mass is not None:
                # Проверяем не заполнили ли мы уже массу из year_of_manufacture
                if table.item(row, 3) is None:
                    item = QTableWidgetItem(str(mass).replace('.', ','))
                    table.setItem(row, 3, item)
            
            # Миграция: если max_thickness есть и > 100, это масса
            max_thick = balloon_data.get('max_thickness')
            if max_thick is not None and table.item(row, 3) is None:
                val = float(str(max_thick).replace(',', '.'))
                if val > 100:  # это масса
                    item = QTableWidgetItem(str(val).replace('.', ','))
                    table.setItem(row, 3, item)
            
            # Миграция: если max_thickness < 100 и не заполнена толщина, это может быть Sмакс
            if max_thick is not None and table.item(row, 1) is None:
                val = float(str(max_thick).replace(',', '.'))
                if val < 100:  # это толщина
                    item = QTableWidgetItem(str(val).replace('.', ','))
                    table.setItem(row, 1, item)
        
        # Обновление с_min_lst для последующих расчётов
        self.main_window.s_min_lst = []
        for row in range(table.rowCount()):
            item = table.item(row, 1)
            if item and item.text():
                try:
                    self.main_window.s_min_lst.append(float(item.text().replace(',', '.')))
                except ValueError:
                    pass
    
    def _get_balloon_data_from_table(self) -> List[Dict[str, Any]]:
        """
        Получение данных баллонов из таблицы.
        
        Returns:
            Список словарей с данными баллонов
        """
        table = self.main_window.table_ballons
        balloons = []
        
        for row in range(table.rowCount()):
            balloon = {}
            
            # Заводской номер
            item = table.item(row, 0)
            if item and item.text():
                balloon['serial_number'] = item.text()
            
            # Минимальная толщина
            item = table.item(row, 1)
            if item and item.text():
                balloon['min_thickness'] = float(item.text().replace(',', '.'))
            
            # Год изготовления - теперь это 3 колонка
            item = table.item(row, 2)
            if item and item.text():
                # Год должен быть целым числом
                balloon['year_of_manufacture'] = int(float(item.text().replace(',', '.')))
            
            # Масса - теперь это 4 колонка
            item = table.item(row, 3)
            if item and item.text():
                balloon['mass'] = float(item.text().replace(',', '.'))
            
            if balloon.get('serial_number'):
                balloons.append(balloon)
        
        return balloons
    
    def _create_project(self) -> Project:
        """
        Создание объекта Project из текущих данных UI.

        Returns:
            Объект Project
        """
        equipment_type_id = self.main_window.equipment_type.id
        form_data = self.main_window.get_form_data()

        if equipment_type_id == "pipeline":
            # employee_id сотрудника справочника «Сотрудники» для каждой
            # строки table_specialists, по порядку строк -- не Qt-виджет и
            # не входит в TABLE_WIDGET/get_form_data(), сохраняем отдельно,
            # чтобы связь со специалистом (и его клише) пережила «Открыть
            # проект», см. _add_specialist_row()/_fill_ui_from_project().
            form_data["specialists_employee_ids"] = list(
                self.main_window._specialist_employee_ids
            )

        if equipment_type_id == "constructor":
            # Включённый блок слота (карточка в included_list -- title/
            # intro-вариант, перетащенный из сайдбара) нигде в form_data не
            # лежит -- сами реквизиты (PLAIN_TEXT_EDIT_NAMES) регистрируются
            # динамически только пока блок включён (см.
            # MainWindow._render_slot_fields()), но САМ выбор варианта
            # для каждого слота без этого терялся бы при «Открыть проект»
            # -- includedBlockList возвращался бы в пустое состояние,
            # значения реквизитов было бы некуда класть (виджеты под них ещё
            # не созданы), см. _fill_ui_from_project()/
            # MainWindow._restore_included_variant().
            form_data["_included_title_variant_id"] = self.main_window._filled_slot_variant("title")
            form_data["_included_intro_variant_id"] = self.main_window._filled_slot_variant("intro")

        if equipment_type_id != "balloon":
            # Для не-баллонных типов таблицы уже внутри form_data (см.
            # get_form_data() -- TABLE_WIDGET кладётся туда же), отдельное
            # поле под них не нужно.
            return Project(
                equipment_type=equipment_type_id,
                report_data=form_data,
                output_dir=str(OUTPUT_DIR),
            )

        # Получение данных баллонов
        balloons_data = self._get_balloon_data_from_table()

        project = Project(
            equipment_type=equipment_type_id,
            report_data=form_data,
            balloons_data=balloons_data,
            settings={
                'working_pressure': form_data.get('p_rab_MPa', 39.0),
                'hydro_test_pressure': form_data.get('p_gidro', 59.0),
                'pneumatic_test_pressure': form_data.get('p_pnevma', 45.0),
            },
            output_dir=str(OUTPUT_DIR),
        )

        return project
    
    def _fill_ui_from_project(self, project: Project):
        """
        Заполнение UI данными из проекта.
        
        Args:
            project: Объект Project
        """
        from PyQt6.QtCore import QDate, QLocale

        if self.main_window.equipment_type.id == "constructor":
            # Включённые блоки (title/intro) -- ПЕРЕД генеричным циклом ниже:
            # он раскладывает значения реквизитов по getattr(main_window,
            # key), а виджеты под эти реквизиты создаются только вместе с
            # включением блока (см. _create_project()/
            # MainWindow._restore_included_variant()) -- без восстановления
            # блока сейчас у сохранённых значений реквизитов просто не было
            # бы виджета-получателя.
            for slot in ("title", "intro"):
                variant_id = project.report_data.get(f"_included_{slot}_variant_id")
                if variant_id:
                    self.main_window._restore_included_variant(slot, variant_id)

        # Заполнение форм данными из report_data
        specialist_combo_names = getattr(self.main_window, "SPECIALIST_COMBO_NAMES", ())
        for key, value in project.report_data.items():
            if key in specialist_combo_names:
                # Индекс строки table_specialists, не текст -- setCurrentText()
                # ниже был бы бессмысленным вызовом на ещё пустом комбобоксе
                # (сам список пунктов появляется только в
                # _refresh_specialist_combo(), после этого цикла). Восстановление
                # -- отдельным проходом после _refresh_program_specialist_combo(),
                # см. вызывающую сторону (open_project_json()/_open_document()).
                continue
            widget = getattr(self.main_window, key, None)
            if widget is not None:
                if hasattr(widget, 'setPlainText'):
                    # Пустое сохранённое значение неотличимо от "поля ещё не
                    # было, когда сохраняли проект" (старые project.json без
                    # добавленных позже полей вроде calc_k/calc_years_operation)
                    # -- не затираем им уже выставленный текст виджета (в т.ч.
                    # предзаполненные умолчания calc_k="1,0" и т.п.).
                    if str(value):
                        widget.setPlainText(str(value))
                elif hasattr(widget, 'setCurrentText'):
                    if str(value):
                        widget.setCurrentText(str(value))
                elif hasattr(widget, 'setValue'):
                    try:
                        # Заменяем запятую на точку перед преобразованием
                        val = float(str(value).replace(',', '.'))
                        widget.setValue(int(val))
                    except (ValueError, TypeError):
                        pass
                elif hasattr(widget, 'setDate'):
                    # Обработка QDateEdit
                    if isinstance(value, str):
                        # Пытаемся распарсить дату в формате dd.MM.yyyy или dd MMMM yyyy
                        try:
                            # Сначала пытаемся как dd.MM.yyyy
                            date_parts = value.split('.')
                            if len(date_parts) == 3:
                                day = int(date_parts[0])
                                month = int(date_parts[1])
                                year = int(date_parts[2])
                                widget.setDate(QDate(year, month, day))
                            else:
                                # get_form_data() (main_window.py) пишет сюда не
                                # "голую" dd MMMM yyyy, а текст для самого
                                # Word-документа: «19» августа 2026 г. (report_date,
                                # ёлочки-кавычки) или 19 августа 2026 г. (остальные
                                # даты трубопровода, суффикс " г.") -- один и тот же
                                # словарь report_data уходит и в шаблон, и в JSON
                                # проекта. QLocale.toDate() со строгим форматом
                                # 'dd MMMM yyyy' не прощает ни кавычки, ни суффикс
                                # -- без очистки дата не парсилась НИКОГДА (кроме
                                # final_deadline_date, у него в шаблоне уже своё
                                # "года", суффикс не добавляется), а widget молча
                                # оставался с прежним значением (по умолчанию --
                                # сегодняшняя дата).
                                cleaned = value.replace('«', '').replace('»', '').strip()
                                if cleaned.endswith(' г.'):
                                    cleaned = cleaned[:-len(' г.')].strip()
                                locale = QLocale('ru_RU')
                                date = locale.toDate(cleaned, 'dd MMMM yyyy')
                                if date.isValid():
                                    widget.setDate(date)
                        except (ValueError, IndexError):
                            pass
                    elif isinstance(value, (int, float)):
                        # Если передан год, создаем дату (например, 2026 -> 01.01.2026)
                        widget.setDate(QDate(int(value), 1, 1))

        if self.main_window.equipment_type.id == "balloon":
            self._fill_balloon_table_from_data(project.balloons_data)
        else:
            # Для не-баллонных типов таблицы лежат прямо в report_data под
            # своим именем (см. _create_project) -- восстанавливаем каждую
            # генерически, без баллонной миграционной логики.
            for name in self.main_window.TABLE_WIDGET:
                rows = project.report_data.get(name)
                if not rows:
                    continue
                table = getattr(self.main_window, name, None)
                if table is None:
                    continue
                table.setRowCount(len(rows))
                for row_idx, row_values in enumerate(rows):
                    for col_idx, cell_text in enumerate(row_values):
                        # table_segments, колонка 1 -- выпадающий список типа
                        # элемента (QComboBox), не обычный текстовый item.
                        if name == "table_segments" and col_idx == 1:
                            self.main_window._install_segment_type_combo(
                                table, row_idx, str(cell_text) or SEGMENT_TYPES[0]
                            )
                        # table_pnevmo_ae, колонка 2 -- выпадающий список
                        # класса источника (QComboBox), тот же приём.
                        elif name == "table_pnevmo_ae" and col_idx == 2:
                            self.main_window._install_ae_class_combo(
                                table, row_idx, str(cell_text) or AE_CLASS_TYPES[0]
                            )
                        else:
                            table.setItem(row_idx, col_idx, QTableWidgetItem(str(cell_text)))

            if self.main_window.equipment_type.id == "pipeline":
                # employee_id по строкам table_specialists (см. _create_project())
                # -- восстанавливаем после того, как generic-цикл выше уже
                # воссоздал строки таблицы, длину приводим к фактическому
                # числу строк (обрезаем/дополняем None) на случай старого
                # проекта без этого поля или отредактированного вручную JSON.
                saved_specialist_ids = project.report_data.get("specialists_employee_ids", [])
                specialists_row_count = self.main_window.table_specialists.rowCount()
                self.main_window._specialist_employee_ids = (
                    list(saved_specialist_ids) + [None] * specialists_row_count
                )[:specialists_row_count]

                # Схема НК (Приложение 7) -- не виджет, generic-цикл выше её
                # не восстанавливает (getattr(main_window, "nk_scheme_filename")
                # не находит widget), нужен явный шаг.
                nk_filename = project.report_data.get("nk_scheme_filename")
                self.main_window.data["nk_scheme_filename"] = nk_filename
                self.main_window._set_nk_scheme_preview(nk_filename)

                # График нагружения (Приложение 8) -- тот же приём.
                pnevmo_graph_filename = project.report_data.get("pnevmo_graph_filename")
                self.main_window.data["pnevmo_graph_filename"] = pnevmo_graph_filename
                self.main_window._set_pnevmo_graph_preview(pnevmo_graph_filename)

                # "Зеркала, пока не тронуты" (calc_years_operation и др., см.
                # MainWindow._sync_mirror_field()) восстановлены выше generic-
                # веткой как обычный текст -- их внутреннее состояние
                # "тронуто/не тронуто" в JSON не попадает, без явного
                # восстановления оно осталось бы неинициализированным, и
                # правка source-поля (например years_of_operation) после
                # открытия проекта переставала бы подхватываться.
                self.main_window._seed_mirror_states_after_load()

        if self.main_window.equipment_type.id == "constructor":
            # Предзаполнение одинаковых плейсхолдеров между слотами
            # (MainWindow._cross_slot_placeholder_value()) срабатывает
            # только в момент СОЗДАНИЯ виджета -- для документов,
            # сохранённых ДО этой фичи (или просто заполненных только в
            # одном из двух слотов на момент сохранения), поля второго
            # слота уже существуют пустыми к этому моменту и сами не
            # подхватят чужое значение. Досылаем синхронизацию явно, уже
            # после того, как оба слота восстановлены и заполнены
            # generic-циклом выше.
            self.main_window._sync_cross_slot_placeholders()
