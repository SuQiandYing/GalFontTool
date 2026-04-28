import os
import json
from PyQt6.QtWidgets import QFileDialog, QMessageBox, QLabel, QHBoxLayout, QPushButton
from PyQt6.QtGui import QColor, QFont, QFontDatabase
from config import THEMES
from core.worker import Worker
from core.system_fonts import encode_system_font_value, decode_system_font_value, is_system_font_value, list_all_system_font_families


def log(main_window, m):
    main_window.log_area.append(m)
    main_window.log_area.verticalScrollBar().setValue(main_window.log_area.verticalScrollBar().maximum())

def browse(main_window, target):
    if target == main_window.map_src or target == main_window.sub_txt or target == main_window.sf_txt or target == main_window.sf_lib:
        d = QFileDialog.getExistingDirectory(main_window, "选择目录")
        if d: target.setText(d)
    else:
        f, _ = QFileDialog.getOpenFileName(main_window, "选择文件", "", "Font/JSON (*.ttf *.otf *.json);;All (*.*)")
        if f:
            target.setText(f)
            if hasattr(main_window, 'add_to_recent_files') and f.lower().endswith(('.ttf', '.otf')):
                main_window.add_to_recent_files(f)

def browse_folder(main_window, line_edit):
    d = QFileDialog.getExistingDirectory(main_window, "选择目录", "")
    if d:
        line_edit.setText(d)


def init_system_font_combos(main_window):
    families = list_all_system_font_families()
    combo_names = [
        'src_system_font_combo',
        'fallback_system_font_combo',
        'pic_system_font_combo',
        'tga_system_font_combo',
        'bmp_system_font_combo',
    ]
    for name in combo_names:
        combo = getattr(main_window, name, None)
        if combo is None:
            continue
        combo.blockSignals(True)
        combo.clear()
        combo.addItem("请选择系统字体...")
        combo.addItems(families)
        combo.blockSignals(False)


def bind_system_font_combo(main_window, combo, target_input, preview=False):
    def _on_changed(text):
        text = text.strip()
        if not text or text == "请选择系统字体...":
            return
        target_input.setText(encode_system_font_value(text))
        if preview:
            main_window.original_font_family = text
            if not main_window.generated_font_family:
                main_window.update_previews()
            if hasattr(main_window, 'chk_lock_file_name') and hasattr(main_window, 'chk_lock_font_name'):
                lock_file = main_window.chk_lock_file_name.isChecked()
                lock_font = main_window.chk_lock_font_name.isChecked()
                if not lock_file:
                    main_window.in_file_name.setText(f"{text}_out.ttf")
                if not lock_font:
                    main_window.in_font_name.setText(f"{text} Custom")

    combo.currentTextChanged.connect(_on_changed)


def try_select_combo_by_font_value(combo, value):
    if combo is None or not value or not is_system_font_value(value):
        return
    family = decode_system_font_value(value)
    idx = combo.findText(family)
    if idx >= 0:
        combo.blockSignals(True)
        combo.setCurrentIndex(idx)
        combo.blockSignals(False)


def reset_to_default(main_window):
    reply = QMessageBox.question(main_window, '确认重置', '确定要清除所有设置并恢复默认值吗？', QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
    if reply == QMessageBox.StandardButton.Yes:
        main_window.settings.clear()
        main_window.in_src.setText("Font.ttf")
        main_window.in_fallback.setText("")
        main_window.in_json.setText("custom_map.json")
        main_window.in_file_name.setText("game.ttf")
        main_window.in_font_name.setText("My Game Font")
        main_window.combo_mode.setCurrentIndex(0)
        main_window.combo_charset.setCurrentIndex(0)
        main_window.apply_theme("🌊 深海 (Ocean)")
        main_window.log_area.clear()
        main_window.log_area.append("✅ 已恢复默认设置。")

def save_preset(main_window):
    preset = {
        'src': main_window.in_src.text(), 'fallback': main_window.in_fallback.text(), 'json': main_window.in_json.text(),
        'file_name': main_window.in_file_name.text(), 'font_name': main_window.in_font_name.text(),
        'mode': main_window.combo_mode.currentIndex(), 'charset': main_window.combo_charset.currentIndex(),
        'theme': main_window.current_theme_name,
        'map_src': main_window.map_src.text(), 'map_out': main_window.map_out.text(), 'map_json': main_window.map_json.text(),
        'map_ext': main_window.map_ext.text(), 'sub_font': main_window.sub_font.text(), 'sub_txt': main_window.sub_txt.text(),
        'sub_json': main_window.sub_json.text(), 'sub_out': main_window.sub_out.text(),
        'pic_font': main_window.pic_font.text(), 'pic_folder': main_window.pic_folder.text(),
        'tga_font': main_window.tga_font.text(), 'bmp_font': main_window.bmp_font.text(),
    }
    save_path, _ = QFileDialog.getSaveFileName(main_window, "保存预设", "my_preset.json", "JSON (*.json)")
    if save_path:
        try:
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(preset, f, ensure_ascii=False, indent=2)
            main_window.log(f"💾 预设已保存: {os.path.basename(save_path)}")
            QMessageBox.information(main_window, "保存成功", f"配置预设已保存到：\n{save_path}")
        except Exception as e:
            main_window.log(f"❌ 保存预设失败: {e}")

def load_preset(main_window):
    load_path, _ = QFileDialog.getOpenFileName(main_window, "加载预设", "", "JSON (*.json)")
    if not load_path: return
    try:
        with open(load_path, 'r', encoding='utf-8') as f:
            preset = json.load(f)

        if 'src' in preset: main_window.in_src.setText(preset['src'])
        if 'fallback' in preset: main_window.in_fallback.setText(preset['fallback'])
        if 'json' in preset: main_window.in_json.setText(preset['json'])
        if 'file_name' in preset: main_window.in_file_name.setText(preset['file_name'])
        if 'font_name' in preset: main_window.in_font_name.setText(preset['font_name'])
        if 'mode' in preset: main_window.combo_mode.setCurrentIndex(preset['mode'])
        if 'charset' in preset: main_window.combo_charset.setCurrentIndex(preset['charset'])
        if 'theme' in preset:
            idx = main_window.combo_theme.findText(preset['theme'])
            if idx >= 0: main_window.combo_theme.setCurrentIndex(idx)
        if 'map_src' in preset: main_window.map_src.setText(preset['map_src'])
        if 'map_out' in preset: main_window.map_out.setText(preset['map_out'])
        if 'map_json' in preset: main_window.map_json.setText(preset['map_json'])
        if 'map_ext' in preset: main_window.map_ext.setText(preset['map_ext'])
        if 'sub_font' in preset: main_window.sub_font.setText(preset['sub_font'])
        if 'sub_txt' in preset: main_window.sub_txt.setText(preset['sub_txt'])
        if 'sub_json' in preset: main_window.sub_json.setText(preset['sub_json'])
        if 'sub_out' in preset: main_window.sub_out.setText(preset['sub_out'])
        if 'pic_font' in preset: main_window.pic_font.setText(preset['pic_font'])
        if 'pic_folder' in preset: main_window.pic_folder.setText(preset['pic_folder'])
        if 'tga_font' in preset: main_window.tga_font.setText(preset['tga_font'])
        if 'bmp_font' in preset: main_window.bmp_font.setText(preset['bmp_font'])

        try_select_combo_by_font_value(getattr(main_window, 'src_system_font_combo', None), main_window.in_src.text())
        try_select_combo_by_font_value(getattr(main_window, 'fallback_system_font_combo', None), main_window.in_fallback.text())
        try_select_combo_by_font_value(getattr(main_window, 'pic_system_font_combo', None), main_window.pic_font.text())
        try_select_combo_by_font_value(getattr(main_window, 'tga_system_font_combo', None), main_window.tga_font.text())
        try_select_combo_by_font_value(getattr(main_window, 'bmp_system_font_combo', None), main_window.bmp_font.text())
        main_window.on_source_font_changed()

        main_window.log(f"📂 预设已加载: {os.path.basename(load_path)}")

        QMessageBox.information(main_window, "加载成功", f"已从预设恢复配置：\n{os.path.basename(load_path)}")

    except Exception as e:
        main_window.log(f"❌ 加载预设失败: {e}")
        QMessageBox.warning(main_window, "加载失败", f"无法加载预设：\n{e}")

def run_worker(main_window, task, conf):
    main_window.set_ui_busy(True)
    main_window.worker = Worker(task, conf)
    main_window.worker.log.connect(main_window.log)
    main_window.worker.prog.connect(main_window.progress.setValue)
    main_window.worker.done.connect(main_window.on_worker_done)
    main_window.worker.finished.connect(lambda: main_window.set_ui_busy(False))
    main_window.worker.start()

def set_ui_busy(main_window, busy):
    main_window.left_card.setEnabled(not busy)
    main_window.right_card.setEnabled(not busy)
    main_window.progress.setValue(0 if busy else 100)
    main_window.lbl_status.setText("正在处理..." if busy else "就绪")

def on_worker_done(main_window, result):
    if result and isinstance(result, str):
        if result.lower().endswith(('.ttf', '.otf', '.woff', '.woff2')):
            main_window.generated_font_path = result
            if result.lower().endswith(('.ttf', '.otf')):
                main_window.pic_font.setText(result)
                main_window.tga_font.setText(result)
                main_window.bmp_font.setText(result)
                family = main_window.load_font_for_preview(result)
                if family:
                    main_window.generated_font_family = family
                    main_window.update_previews()
            main_window.lbl_status.setText("字体已就绪")
        elif result.endswith('.json'):
            main_window.in_json.setText(result)
            main_window.lbl_status.setText("映射表就绪")

    
    if hasattr(main_window, 'update_history_buttons'):
        main_window.update_history_buttons()

def toggle_max(main_window):
    if main_window.is_max:
        main_window.showNormal()
        main_window.is_max = False
    else:
        main_window.showMaximized()
        main_window.is_max = True

def load_settings(main_window):
    main_window.in_src.setText(main_window.settings.value("in_src", "Font.ttf"))
    main_window.in_fallback.setText(main_window.settings.value("in_fallback", ""))
    main_window.in_json.setText(main_window.settings.value("in_json", "custom_map.json"))
    main_window.in_file_name.setText(main_window.settings.value("in_file_name", "game.ttf"))
    main_window.in_font_name.setText(main_window.settings.value("in_font_name", "My Game Font"))
    main_window.chk_lock_file_name.setChecked(main_window.settings.value("lock_file_name", False) == "true" or main_window.settings.value("lock_file_name", False) is True)
    main_window.chk_lock_font_name.setChecked(main_window.settings.value("lock_font_name", False) == "true" or main_window.settings.value("lock_font_name", False) is True)
    if hasattr(main_window, 'in_output_dir'):
        main_window.in_output_dir.setText(main_window.settings.value("output_dir", ""))
    main_window.combo_mode.setCurrentIndex(int(main_window.settings.value("mode", 0)))
    main_window.combo_charset.setCurrentIndex(int(main_window.settings.value("charset", 0)))
    main_window.current_theme_name = main_window.settings.value("theme", "🌊 深海 (Ocean)")
    idx = main_window.combo_theme.findText(main_window.current_theme_name)
    if idx >= 0: main_window.combo_theme.setCurrentIndex(idx)
    if hasattr(main_window, 'load_recent_files'):
        main_window.load_recent_files()
    try_select_combo_by_font_value(getattr(main_window, 'src_system_font_combo', None), main_window.in_src.text())
    try_select_combo_by_font_value(getattr(main_window, 'fallback_system_font_combo', None), main_window.in_fallback.text())
    if hasattr(main_window, 'pic_font'):
        try_select_combo_by_font_value(getattr(main_window, 'pic_system_font_combo', None), main_window.pic_font.text())
    if hasattr(main_window, 'tga_font'):
        try_select_combo_by_font_value(getattr(main_window, 'tga_system_font_combo', None), main_window.tga_font.text())
    if hasattr(main_window, 'bmp_font'):
        try_select_combo_by_font_value(getattr(main_window, 'bmp_system_font_combo', None), main_window.bmp_font.text())
    main_window.on_source_font_changed()

    if hasattr(main_window, 'update_history_buttons'):
        main_window.update_history_buttons()

def load_font_for_preview(main_window, font_path):
    if is_system_font_value(font_path):
        family = decode_system_font_value(font_path)
        main_window.log(f"🔎 预览已切换到系统字体: {family}")
        return family
    if not os.path.exists(font_path):
        return None
    font_id = QFontDatabase.addApplicationFont(font_path)
    if font_id == -1:
        main_window.log(f"⚠️ 预览加载失败: {os.path.basename(font_path)}")
        return None
    family = QFontDatabase.applicationFontFamilies(font_id)[0]
    main_window.log(f"🔎 预览已加载: {family}")
    return family


def update_previews(main_window):
    preview_text = main_window.preview_input.text()
    if not preview_text:
        preview_text = main_window.preview_input.placeholderText()
    main_window.preview_area.setText(preview_text)
    family_to_use = main_window.generated_font_family if main_window.generated_font_family else main_window.original_font_family
    if family_to_use:
        font = QFont(family_to_use, 16)
        main_window.preview_area.setFont(font)
        main_window.preview_area.setToolTip(f"当前预览: {family_to_use}")
    else:
        main_window.preview_area.setToolTip("当前使用系统默认字体")

def on_source_font_changed(main_window):
    src_font_path = main_window.in_src.text().strip()
    family = main_window.load_font_for_preview(src_font_path)
    if family:
        main_window.original_font_family = family
        if not main_window.generated_font_family:
            main_window.update_previews()

    if is_system_font_value(src_font_path):
        base_name = decode_system_font_value(src_font_path)
    elif os.path.exists(src_font_path):
        base_name = os.path.splitext(os.path.basename(src_font_path))[0]
    else:
        return

    lock_file = main_window.chk_lock_file_name.isChecked()
    lock_font = main_window.chk_lock_font_name.isChecked()

    if not lock_file:
        main_window.in_file_name.setText(f"{base_name}_out.ttf")
    if not lock_font:
        main_window.in_font_name.setText(f"{base_name} Custom")
    if os.path.exists(src_font_path) and hasattr(main_window, 'add_to_recent_files'):
        main_window.add_to_recent_files(src_font_path)


def on_mode_change(main_window, index):
    need_json = index in [1, 2]
    main_window.in_json.setEnabled(need_json)
    main_window.btn_json.setEnabled(need_json)

def create_label(main_window, t): return QLabel(t)

def create_file_row(main_window, inp, btn, extra_widgets=None):
    l = QHBoxLayout()
    btn.clicked.connect(lambda: main_window.browse(inp))
    l.addWidget(inp)
    l.addWidget(btn)
    if extra_widgets:
        for widget in extra_widgets:
            l.addWidget(widget)
    return l


def get_scrollbar_style(main_window, accent):
    return f"""
        QScrollBar:vertical {{ border: none; background: rgba(0, 0, 0, 0.05); width: 8px; margin: 0px; border-radius: 4px; }}
        QScrollBar::handle:vertical {{ background: {accent}; min-height: 20px; border-radius: 4px; }}
        QScrollBar::handle:vertical:hover {{ background: {QColor(accent).darker(110).name()}; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}
        QScrollBar:horizontal {{ border: none; background: rgba(0, 0, 0, 0.05); height: 8px; margin: 0px; border-radius: 4px; }}
        QScrollBar::handle:horizontal {{ background: {accent}; min-width: 20px; border-radius: 4px; }}
        QScrollBar::handle:horizontal:hover {{ background: {QColor(accent).darker(110).name()}; }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0px; }}
        QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: none; }}
    """

def apply_theme(main_window, theme_name):
    if theme_name not in THEMES: return
    main_window.current_theme_name = theme_name
    main_window.theme = THEMES[theme_name]
    t = main_window.theme
    main_window.update()

    labels_to_color = [
        main_window.title_label,
        main_window.lbl_map, main_window.lbl_ed, main_window.lbl_sub,
        main_window.lbl_cov, main_window.lbl_merge, main_window.lbl_info, main_window.lbl_cmp,
        getattr(main_window, 'lbl_sf', None), getattr(main_window, 'lbl_woff2', None),
        getattr(main_window, 'lbl_clean', None), getattr(main_window, 'lbl_imgfont', None),
        getattr(main_window, 'lbl_fix', None), getattr(main_window, 'lbl_conv', None)
    ]

    for l in labels_to_color:
        if l: 
            try:
                l.setStyleSheet(f"color: {t['text_main']}; padding-left: 5px;")
            except RuntimeError:
                pass

    for l in [main_window.lbl_theme, main_window.lbl_src, main_window.lbl_font_conf, main_window.lbl_status]: l.setStyleSheet(f"color: {t['text_dim']}; font-weight:bold; font-size:12px; font-family:'Microsoft YaHei';")

    if hasattr(main_window, 'preview_labels'):
        for label in main_window.preview_labels:
            label.setStyleSheet(f"color: {t['text_dim']}; font-family:'Microsoft YaHei'; font-weight:bold; font-size:12px;")

    for btn in [main_window.btn_min, main_window.btn_max, main_window.btn_close]: btn.update_icon_color(t['text_main'])

    main_window.left_card.update_theme(t['card_bg'], t['border'])
    main_window.right_card.update_theme(t['card_bg'], t['border'])

    all_inputs = main_window.findChildren(main_window.IOSInput)
    for i in all_inputs: i.update_theme(t['input_bg'], t['input_focus'], t['accent'], t['text_main'])

    folder_btn_style = f"""
        QPushButton {{
            background-color: {t['input_bg']};
            color: {t['text_main']};
            border-radius: 8px;
            border: 1px solid {t['border']};
            font-size: 14px;
            padding: 4px;
        }}
        QPushButton:hover {{
            background-color: {t['accent']};
            color: white;
            border: none;
        }}
        QPushButton:disabled {{
            background-color: rgba(0,0,0,0.1);
            color: rgba(0,0,0,0.3);
        }}
    """
    
    from PyQt6.QtWidgets import QPushButton
    for btn in main_window.findChildren(QPushButton):
        if btn.text() == "📁":
            btn.setStyleSheet(folder_btn_style)

    main_window.btn_reset.setStyleSheet(f"QPushButton {{background-color: transparent; color: {t['text_dim']}; border: 1px dashed {t['text_dim']}; border-radius: 5px;}} QPushButton:hover {{background-color: {t['accent']}; color: white; border:none;}}")

    history_btn_style = f"QPushButton {{background-color: rgba(255,255,255,0.6); color: {t['text_main']}; border-radius: 5px; border: 1px solid rgba(128,128,128,0.2); font-size: 12px; padding: 2px 8px;}} QPushButton:hover {{background-color: {t['accent']}; color: white;}} QPushButton:disabled {{background-color: rgba(0,0,0,0.05); color: rgba(0,0,0,0.3); border-color: transparent;}}"
    for btn in [main_window.btn_undo, main_window.btn_redo, main_window.btn_history]:
        if btn: btn.setStyleSheet(history_btn_style)

    for b in [main_window.btn_gen_font, main_window.btn_run_map, main_window.btn_run_subset, main_window.btn_checkup_map, main_window.btn_checkup_subset,
              main_window.btn_preview_map, getattr(main_window, 'btn_restore_map', None), main_window.btn_run_coverage, main_window.btn_run_merge,
              main_window.btn_read_info, main_window.btn_save_info, main_window.btn_run_compare, main_window.btn_export_diff,
              main_window.btn_run_smart, getattr(main_window, 'btn_run_convert', None), getattr(main_window, 'btn_run_imgfont', None)]:
        if b: b.set_theme_color(t['accent'])
    
    sb_style = get_scrollbar_style(main_window, t['accent'])
    combo_style = f"""
        QComboBox {{ 
            border: 1px solid rgba(128,128,128,0.2); 
            border-radius: 10px; 
            padding: 0 10px; 
            background: {t['input_bg']}; 
            color: {t['text_main']}; 
            height: 38px;
            font-size: 13px;
        }}
        QComboBox:focus {{
            border: 1px solid {t['accent']};
            background-color: {t['input_focus']};
        }}
        QComboBox::drop-down {{ 
            border: none; 
            width: 30px;
        }}
        QComboBox::down-arrow {{
            image: none;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 5px solid {t['text_dim']};
            margin-right: 10px;
        }}
        QComboBox QAbstractItemView {{ 
            background: {t['card_bg']}; 
            selection-background-color: {t['accent']}; 
            color: {t['text_main']}; 
            border: 1px solid rgba(128,128,128,0.2);
            border-radius: 8px;
            outline: none;
        }}
        {sb_style}
    """
    main_window.combo_theme.setStyleSheet(combo_style)
    main_window.combo_mode.setStyleSheet(combo_style)
    main_window.combo_charset.setStyleSheet(combo_style)
    for combo_name in ['src_system_font_combo', 'fallback_system_font_combo', 'pic_system_font_combo', 'tga_system_font_combo', 'bmp_system_font_combo']:
        combo = getattr(main_window, combo_name, None)
        if combo:
            combo.setStyleSheet(combo_style)

    main_window.tab_container.setStyleSheet(f"background: {t['input_bg']}; border-radius: 15px;")
    main_window.tab_scroll_area.setStyleSheet(f"QScrollArea {{ background: transparent; border: none; }} {sb_style}")
    main_window.switch_tab(main_window.stack.currentIndex())
    bg_log = "rgba(255,255,255,0.1)" if "Night" in theme_name else "rgba(0,0,0,0.03)"
    main_window.log_area.update_theme(t['text_main'], bg_log, sb_style)
    main_window.progress.setStyleSheet(f"QProgressBar {{border:none; background:rgba(0,0,0,0.1); border-radius:3px;}} QProgressBar::chunk {{background: {t['accent']}; border-radius:3px;}}")
    main_window.help_browser.setStyleSheet(f"QTextEdit {{ background: transparent; border: none; font-size: 13px; line-height: 150%; color: {t['text_main']}; }} {sb_style}")
    if hasattr(main_window, 'preview_area'):
        main_window.preview_area.setStyleSheet(f"QTextEdit {{ background-color: {t['input_bg']}; border-radius: 8px; border: 1px solid rgba(128,128,128,0.2); color: {t['text_main']}; padding: 2px; }} {sb_style}")
    common_te_style = f"QTextEdit {{ background: rgba(0,0,0,0.03); border-radius: 8px; padding: 10px; font-family: 'Consolas', monospace; color: {t['text_main']}; }} {sb_style}"
    if hasattr(main_window, 'cov_result'): main_window.cov_result.setStyleSheet(common_te_style)
    if hasattr(main_window, 'info_display'): main_window.info_display.setStyleSheet(common_te_style)
    if hasattr(main_window, 'cmp_result'): main_window.cmp_result.setStyleSheet(common_te_style)
    if hasattr(main_window, 'map_table'):
         main_window.map_table.setStyleSheet(f"QTableWidget {{ background-color: {t['input_bg']}; color: {t['text_main']}; border: none; }} {sb_style}")
    if hasattr(main_window, 'sf_table'):
         main_window.sf_table.setStyleSheet(f"QTableWidget {{ background-color: {t['input_bg']}; color: {t['text_main']}; border: none; }} {sb_style}")

def switch_tab(main_window, idx):
    main_window.stack.setCurrentIndex(idx)
    t = main_window.theme
    base = "border:none; border-radius: 12px; font-weight: bold; font-family: 'Microsoft YaHei';"
    active = f"{base} background-color: {t['accent']}; color: white;"
    inactive = f"{base} background-color: transparent; color: {t['text_dim']};"
    for i, b in enumerate(main_window.tabs): b.setChecked(i == idx); b.setStyleSheet(active if i == idx else inactive)

def set_help_content(main_window):
    html = """
    <style>
        h3 { color: #2196F3; margin-top: 12px; margin-bottom: 5px; font-family: 'Microsoft YaHei'; }
        h4 { color: #555; margin-bottom: 2px; font-weight: bold; }
        li { margin-bottom: 4px; color: #444; line-height: 140%; }
        p { color: #666; line-height: 140%; font-size: 13px; margin-top:2px; }
        code { background: rgba(0,0,0,0.08); padding: 2px 6px; border-radius: 4px; font-family: Consolas; }
        .tip { background: #E3F2FD; padding: 8px 12px; border-radius: 6px; border-left: 3px solid #2196F3; margin: 8px 0; font-size: 13px; }
        .warn { background: #FFF3E0; padding: 8px 12px; border-radius: 6px; border-left: 3px solid #FF9800; margin: 8px 0; font-size: 13px; }
    </style>
    <h3 style='text-align:center; border-bottom: 1px solid #ddd; padding-bottom:10px;'>Galgame 字体工具箱 完整使用指南</h3>

    <h3>快速入门</h3>
    <p>本工具专为游戏本地化（汉化）设计。典型工作流：</p>
    <ol>
        <li><b>扫描文本</b> - 在【映射表】功能中导入含中文的翻译文本目录。</li>
        <li><b>生成映射</b> - 自动生成“原中文 -> 日文生僻字”的字符映射表 (JSON)。</li>
        <li><b>制作伪装字体</b> - 主界面选择“模式1”，基于原版字体与生成的映射表，制作出能被游戏引擎正常读取的伪装日文字体。</li>
    </ol>
    <div class='tip'>💡 拖拽功能：软件内所有路径输入框都支持直接拖拽文件或文件夹。</div>

    <h3>快捷键</h3>
    <ul>
        <li><code>Ctrl+O</code> 打开主字体文件</li>
        <li><code>Ctrl+S</code> 另存当前配置为 JSON 预设</li>
        <li><code>Ctrl+E</code> 导出完整配置状态（包括界面状态）</li>
        <li><code>Ctrl+I</code> 导入 JSON 或状态预设</li>
        <li><code>Ctrl+Z / Y</code> 跨文本框的撤销/重做</li>
        <li><code>Ctrl+G</code> 一键生成最终字体</li>
        <li><code>F5</code> 刷新当前操作面板和预览选项</li>
        <li><code>Ctrl+1~5</code> 快速切换主标签页</li>
    </ul>

    <h3>处理模式说明 (主界面左侧)</h3>
    <ul>
        <li><b>模式1 - 日繁映射 (推荐)</b>：配合映射字典，将需要渲染的中文字符映射到日文字形的位置上，这是突破引擎日文编码限制的最常用手法。</li>
        <li><b>模式2 - 逆向映射</b>：模式1的反操作。</li>
        <li><b>模式3 - 仅伪装</b>：不改变内部字形排列，仅仅修改字体的外部文件头信息伪装成原版日文字体以通过游戏引擎的基础校验。</li>
        <li><b>模式4 / 模式5</b>：自带繁简转换算法，一键对中文字体内的全部字形进行繁简 / 简繁转化。</li>
    </ul>

    <h3>右侧功能区详解</h3>
    <h4>ℹ️ 字体信息</h4>
    <p>查看、编辑和提取字体元数据（字体名称、版本号、版权、设计师等），双击表格单元格直接修改参数去深度伪装，骗过部分严苛的引擎校验。</p>
    
    <h4>🔠 映射表</h4>
    <p>核心翻译辅助功能组，主要包含：</p>
    <ul>
        <li><b>扫描/生成映射</b>：基于翻译文本抽出需要用到且不重复的所有汉字，生成供后续使用的字典映射表。</li>
        <li><b>检查缺字</b>：结合目标字体检查翻译文本是否超出该字库渲染范围。</li>
        <li><b>预览替换</b>：快速预览映射字典替换后的全乱码文本视觉效果。</li>
        <li><b>还原文本</b>：支持将已被映射工具处理成乱码的外文文本，利用旧版 JSON 映射表逆向恢复为清晰的中文原文本。</li>
    </ul>
    
    <h4>📊 分析对比</h4>
    <p>交叉对比两个不同字体的字符集差异，分析字体对各语言区块（如基本汉字、中日扩展区、假名、符号等）的精准覆盖率，辅助选择底字库。</p>
    
    <h4>✂️ 精简瘦身 (Subset)</h4>
    <p>仅保留翻译文本中切实使用到的字符，删除所有的多余无用字形，大幅减小字体文件体积（一般可将几十MB缩减至两三MB以内，显著加快系统载入）。</p>
    
    <h4>➕ 合并补字 & 智能补字</h4>
    <p>当主游戏字体缺字时，自动在补全字体（如思源黑体）中抽取字形拼接到主字体中。智能补字更支持自动分析本地系统字库来源，一键推荐并补全所有缺失的罕见汉字。</p>
    
    <h4>🖼️ 图片字库 (ImgFont)</h4>
    <p>游戏 UI 设计和古董引擎利器。一键将矢量字体散列并生成 PNG / WebP / TGA / BMP 及 BMFont 格式的等宽、纹理图片字库集合。</p>
    
    <h4>🌐 Web转换</h4>
    <p>将传统的 TTF / OTF 字体直接转换为网页友好的 WOFF2 格式，实现极限体积压缩，极其适合浏览器和 Web H5 环境的引擎移植（如各种网页端运行的 Galgame 或 RPG Maker MV）。</p>
    
    <h4>📐 度量修复</h4>
    <p>可以手动或全自动调整字体的宽高比界限、行距 (Ascender/Descender/LineGap) 等垂直度量。能彻底解决汉化后文字在对话框UI中偏上偏下、出界或被莫名截断显示不全的顽疾。</p>
    
    <h4>🧹 兼容清理</h4>
    <p>物理移除字体中现代的高级 OpenType 渲染特性表（如GSUB/GPOS/hdmx/vdmx等），极大提高底边古老游戏引擎或自研引擎对魔改字体的兼容性，有效防止文字渲染系统崩溃或卡死。</p>

    <h3>常见问题 FAQ</h3>
    <div class='warn'>❓ <b>文字显示变成了方块或问号？</b><br>缺字现象。请在【映射表】模块中使用“检查缺字”功能排查。如果是使用了精简功能，确保你扫描了<b>所有</b>会显示在屏幕上的文本和系统 UI 词条！</div>
    <div class='warn'>❓ <b>文字位置总是偏上/偏下对不齐？</b><br>这是中日字体度量差异造成的。使用【度量修复】功能，选择原版游戏罗马音字体作为“标杆指标”，点击“自动计算”来硬对齐原版游戏字体的高度标准即可。</div>
    <div class='warn'>❓ <b>替换字体后游戏直接闪退？</b><br>极大概率是游戏原生引擎不识别高级字体特性表。尝试并在最后一步对其进行【兼容清理】，勾选“暴力清除所有高级特性表”。同时对于只支持 TTF 的老游戏，确保不要喂给它们 OTF 格式的改版字体（遇到 OTF 本工具已默认自动转为 TTF 处理）。</div>

    <p style='text-align:center; font-size:11px; color:#999; margin-top:20px;'>
        所有输入框支持拖拽 | 工具自动保存操作状态 | 本指南随时更新 | 祝工作顺利！✨
    </p>
    """
    main_window.help_browser.setHtml(html)