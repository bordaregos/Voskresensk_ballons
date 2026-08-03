"""Сервис генерации документов Word и CSV."""

import csv
import os
from pathlib import Path
from typing import List, Dict, Any

from docxtpl import DocxTemplate

from ..config import OUTPUT_DIR, FORMAT_SETTINGS
from ..models.balloon import Report, Balloon
from ..services.calculations import CalculationsService


class DocumentGenerator:
    """Генератор документов для заключений на баллоны."""
    
    def __init__(self, template_path: Path = None):
        """
        Инициализация генератора документов.
        
        Args:
            template_path: Путь к шаблону Word. Если None, используется шаблон по умолчанию.
        """
        from ..config import find_template
        self.template_path = template_path or find_template()
    
    def generate_report(self, report: Report, output_dir: Path = None) -> str:
        """
        Генерация Word-документа заключения.
        
        Args:
            report: Модель заключения
            output_dir: Директория для сохранения. Если None, используется OUTPUT_DIR
            
        Returns:
            Путь к сохранённому файлу
        """
        if output_dir is None:
            output_dir = OUTPUT_DIR
        
        # Валидация
        errors = report.validate()
        if errors:
            raise ValueError(f"Ошибки в данных заключения: {'; '.join(errors)}")
        
        # Подготовка контекста
        context = self._prepare_context(report)
        
        # Загрузка и заполнение шаблона
        doc = DocxTemplate(self.template_path)
        doc.render(context)
        
        # Генерация имени файла
        filename = self._generate_filename(report)
        output_path = output_dir / filename
        
        # Сохранение
        os.makedirs(output_dir, exist_ok=True)
        doc.save(output_path)
        
        return str(output_path)
    
    def generate_csv(self, report: Report, output_dir: Path = None) -> str:
        """
        Генерация CSV-файла с данными баллонов.
        
        Args:
            report: Модель заключения
            output_dir: Директория для сохранения. Если None, используется OUTPUT_DIR
            
        Returns:
            Путь к сохранённому файлу
        """
        if output_dir is None:
            output_dir = OUTPUT_DIR
        
        # Подготовка данных
        rows = self._prepare_csv_data(report)
        
        # Генерация имени файла
        filename = f"Баллоны_{report.registration_number}.csv"
        output_path = output_dir / filename
        
        # Сохранение CSV
        os.makedirs(output_dir, exist_ok=True)
        
        with open(output_path, 'w', newline='', encoding=FORMAT_SETTINGS["csv_encoding"]) as file:
            writer = csv.DictWriter(
                file,
                fieldnames=list(rows[0].keys()),
                delimiter=FORMAT_SETTINGS["csv_delimiter"],
                quoting=csv.QUOTE_NONNUMERIC
            )
            writer.writeheader()
            writer.writerows(rows)
        
        return str(output_path)
    
    def _prepare_context(self, report: Report) -> Dict[str, Any]:
        """
        Подготовка контекста для шаблона Word.
        
        Args:
            report: Модель заключения
            
        Returns:
            Словарь с данными для шаблона
        """
        # Общие данные
        context = {
            "zakl_number": report.report_number,
            "reg_number": report.registration_number,
            "dataZakl": report.creation_date.strftime("%d.%m.%Y"),
            "place": report.section_name,
            "g_vvod": report.date_of_injection,
            "rab_sreda": report.test_medium,
            "gost": report.gost,
            "volume_total": report.total_volume,
            "p_rab_MPa": report.working_pressure,
            "p_rab": str(report.working_pressure).replace('.', ','),
            "p_gidro": report.hydro_test_pressure,
            "p_pnevma": report.pneumatic_test_pressure,
            "p_pnevma_kgs": str(report.test_pressure_pneumatic_kgs).replace('.', ','),
            "pasp_pg_amount": report.total_count,
            "amount": report.total_count,
        }
        
        # Данные о баллонах
        context["ballony"] = self._prepare_ballons_data(report)
        
        # Минимальная толщина
        context["s_min_total"] = str(report.min_wall_thickness).replace('.', ',')
        context["zav_s_min"] = report.min_wall_thickness_serial
        
        # Годы изготовления
        context["min_year"] = report.year_range
        
        # Расчётные параметры
        context["sigma"] = str(report.calculated_sigma).replace('.', ',')
        context["sigma_gidro"] = str(report.calculated_sigma_hydro).replace('.', ',')
        context["s_rasch"] = str(report.calculated_thickness).replace('.', ',')
        context["s_rasch_gidro"] = str(report.calculated_thickness_hydro).replace('.', ',')
        context["s_max_rasch"] = str(report.max_calculated_thickness).replace('.', ',')
        context["p_dop"] = str(report.permissible_pressure).replace('.', ',')
        
        # Остаточный ресурс
        context["a_corr"] = str(report.corrosion_rate).replace('.', ',')
        context["tk_years"] = str(int(report.remaining_life)) if report.remaining_life > 0 else "0"
        context["tk_just"] = report.remaining_life_comment
        
        # Твёрдость
        context["hb_min"] = str(report.hardness_min).replace('.', ',')
        context["hb_max"] = str(report.hardness_max).replace('.', ',')
        context["tverdost_data"] = self._prepare_hardness_data(report)
        
        # Овальность
        context["bal_oval"] = self._prepare_ovalness_data(report)
        
        return context
    
    def _prepare_ballons_data(self, report: Report) -> List[Dict[str, Any]]:
        """
        Подготовка данных по баллонам.
        
        Args:
            report: Модель заключения
            
        Returns:
            Список данных по баллонам
        """
        ballons_data = []
        
        for i, balloon in enumerate(report.balloons, 1):
            ballon_data = {
                "n": i,
                "zav": balloon.serial_number,
                "reg": balloon.registration_number or "",
                "v": balloon.nominal_volume,
                "massa": balloon.mass,
                "s_min": str(balloon.min_thickness).replace('.', ','),
                "g_i_bal": balloon.year_of_manufacture,
                "place": balloon.manufacturer,
            }
            
            # Добавить измерения толщины (s1-s20)
            for j, measurement in enumerate(balloon.thickness_measurements, 1):
                ballon_data[f"s{j}"] = str(measurement).replace('.', ',')
            
            ballons_data.append(ballon_data)
        
        return ballons_data
    
    def _prepare_hardness_data(self, report: Report) -> List[Dict[str, Any]]:
        """
        Подготовка данных по твёрдости.
        
        Args:
            report: Модель заключения
            
        Returns:
            Список данных по твёрдости
        """
        if not report.hardness_measurements:
            return []
        
        hardness_data = []
        for i, measurements in enumerate(report.hardness_measurements, 1):
            hardness_data.append({
                "zav": report.balloons[i-1].serial_number if i <= len(report.balloons) else "",
            })
            
            for j, hb in enumerate(measurements, 1):
                hardness_data[-1][f"hb_{j}"] = str(int(hb))
        
        return hardness_data
    
    def _prepare_ovalness_data(self, report: Report) -> List[Dict[str, Any]]:
        """
        Подготовка данных по овальности.
        
        Args:
            report: Модель заключения
            
        Returns:
            Список данных по овальности
        """
        if not report.ovalness_measurements:
            return []
        
        ovalness_data = []
        for item in report.ovalness_measurements:
            ovalness_data.append({
                "z_n": item["serial_number"],
            })
            
            for j, (d_min, d_max, oval) in enumerate(item["measurements"], 0):
                ovalness_data[-1][f"d_min_rand{j}"] = str(int(d_min))
                ovalness_data[-1][f"d_max_rand{j}"] = str(int(d_max))
                ovalness_data[-1][f"oval{j}"] = str(oval)
        
        return ovalness_data
    
    def _prepare_csv_data(self, report: Report) -> List[Dict[str, Any]]:
        """
        Подготовка данных для CSV-файла.
        
        Args:
            report: Модель заключения
            
        Returns:
            Список строк данных
        """
        rows = []
        
        # Заголовки
        headers = [
            "№", "Зав. №", "Раб. давление", "Объём", "Масса",
            "Год изготовления", "Sмин", "Sсредн", "Sмакс"
        ]
        
        for i, balloon in enumerate(report.balloons, 1):
            row = {
                headers[0]: i,
                headers[1]: balloon.serial_number,
                headers[2]: str(balloon.working_pressure).replace('.', ','),
                headers[3]: balloon.nominal_volume,
                headers[4]: balloon.mass,
                headers[5]: balloon.year_of_manufacture,
                headers[6]: str(balloon.min_thickness).replace('.', ','),
                headers[7]: str(round(balloon.avg_thickness, 1)).replace('.', ','),
                headers[8]: str(balloon.max_thickness).replace('.', ','),
            }
            rows.append(row)
        
        return rows
    
    def _generate_filename(self, report: Report) -> str:
        """
        Генерация имени файла на основе данных заключения.
        
        Args:
            report: Модель заключения
            
        Returns:
            Имя файла
        """
        # Формат: закл_{номер}_рег-{регистрационный}_р-{давление}_{среда}_кбХиммаш_{кол-во}шт.docx
        filename = (
            f"закл_{report.report_number}_"
            f"рег-{report.registration_number}_"
            f"р-{str(report.working_pressure).replace('.', '-')}_"
            f"{report.test_medium}_"
            f"кбХиммаш_{report.total_count}шт.docx"
        )
        
        # Очистка от недопустимых символов
        filename = filename.replace('/', '_').replace('\\', '_')
        
        return filename
