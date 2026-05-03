import os
import re
import json
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
                             QTextEdit, QFrame, QLineEdit, QComboBox, QCheckBox,
                             QGridLayout, QScrollArea, QTableWidget, QTableWidgetItem,
                             QHeaderView, QSizePolicy, QSplitter, QStackedWidget, QGroupBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


from .widgets import IOSInput, IOSButton
from config import HAS_BROTLI

FONT_PRESET_CONFIG_PATH = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), "font_presets.json"))
DEFAULT_FONT_PRESETS = {
    38: {
        "font_size": 38,
        "img_w": 1024,
        "img_h": 640,
        "offset_x": 5,
        "offset_y": 11,
        "cell_w": 48,
        "cell_h": 48,
        "columns": 19,
        "rows": 10,
    },
    31: {
        "font_size": 31,
        "img_w": 800,
        "img_h": 440,
        "offset_x": 5,
        "offset_y": 10,
        "cell_w": 41,
        "cell_h": 41,
        "columns": 19,
        "rows": 10,
    },
}

def _load_pic_font_presets():
    presets = dict(DEFAULT_FONT_PRESETS)
    if not os.path.exists(FONT_PRESET_CONFIG_PATH):
        return presets
    try:
        with open(FONT_PRESET_CONFIG_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        loaded = {}
        for raw_size, raw_preset in dict(data).items():
            size = int(raw_size)
            loaded[size] = {
                'font_size': int(raw_preset['font_size']),
                'img_w': int(raw_preset['img_w']),
                'img_h': int(raw_preset['img_h']),
                'offset_x': int(raw_preset['offset_x']),
                'offset_y': int(raw_preset['offset_y']),
                'cell_w': int(raw_preset['cell_w']),
                'cell_h': int(raw_preset['cell_h']),
                'columns': int(raw_preset['columns']),
                'rows': int(raw_preset['rows']),
            }
        return loaded or presets
    except Exception:
        return presets

def apply_pic_font_size_preset(main_window):
    if not hasattr(main_window, 'pic_fs'):
        return
    text = main_window.pic_fs.text().strip()
    if not text.isdigit():
        return
    size = int(text)
    presets = _load_pic_font_presets()
    preset = presets.get(size)
    if not preset:
        return

    font_size = preset['font_size']
    cell_w = preset['cell_w']
    cell_h = preset['cell_h']
    gap_x = max(0, cell_w - font_size)
    gap_y = max(0, cell_h - font_size)

    main_window.pic_cnt.setText(str(preset['columns']))
    main_window.pic_cw.setText(str(font_size))
    main_window.pic_ch.setText(str(font_size))
    main_window.pic_iw.setText(str(gap_x))
    main_window.pic_ih.setText(str(gap_y))
    main_window.pic_imw.setText(str(preset['img_w']))
    main_window.pic_imh.setText(str(preset['img_h']))
    main_window.pic_ix.setText(str(preset['offset_x']))
    main_window.pic_iy.setText(str(preset['offset_y']))

    current_folder = main_window.pic_folder.text().strip() if hasattr(main_window, 'pic_folder') else ''
    if not current_folder or re.fullmatch(r'image\d+', current_folder):
        main_window.pic_folder.setText(f'image{size}')

def setup_image_font_ui(main_window, parent_widget):

    """统一的图片字库生成界面，通过下拉框选择不同模式"""
    l = QVBoxLayout(parent_widget)
    
    main_window.lbl_imgfont = QLabel("图片字库生成")
    main_window.lbl_imgfont.setAlignment(Qt.AlignmentFlag.AlignCenter)
    main_window.lbl_imgfont.setFont(QFont("Microsoft YaHei", 14, QFont.Weight.Bold))
    l.addWidget(main_window.lbl_imgfont)
    
    mode_layout = QHBoxLayout()
    mode_layout.addWidget(QLabel("生成模式:"))
    main_window.imgfont_mode = QComboBox()
    main_window.imgfont_mode.addItems([
        "📷 PNG/WebP 图片字库",
        "🎮 TGA 字库 (游戏引擎)",
        "🖼️ BMP 字库 (位图)",
        "📝 BMFont (FNT格式)"
    ])
    main_window.imgfont_mode.setFixedHeight(38)
    main_window.imgfont_mode.currentIndexChanged.connect(lambda idx: main_window.imgfont_stack.setCurrentIndex(idx))
    mode_layout.addWidget(main_window.imgfont_mode)
    l.addLayout(mode_layout)
    
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setStyleSheet("background: rgba(0,0,0,0.1);")
    l.addWidget(line)
    
    main_window.imgfont_stack = QStackedWidget()
    
    # === 模式 0: PNG/WebP 图片字库 ===
    p_pic = QWidget()
    l_pic = QVBoxLayout(p_pic)
    l_pic.setContentsMargins(0, 10, 0, 0)
    gd_pic = QGridLayout()
    gd_pic.setSpacing(10)
    main_window.pic_font = IOSInput("输入字体路径", "game.ttf")
    main_window.pic_font.setToolTip("用于生成图片的源字体")
    btn_pic_font = QPushButton("📁")
    btn_pic_font.setFixedSize(40, 38)
    main_window.pic_folder = IOSInput("保存目录", "image38")
    main_window.pic_folder.setToolTip("生成的图片将保存在该文件夹下")
    main_window.pic_fmt = IOSInput("扩展名 (如 webp)", "webp")
    main_window.pic_fmt.setToolTip("图片格式：png 或 webp")
    gd_pic.addWidget(QLabel("使用字体:"), 0, 0)
    gd_pic.addLayout(main_window.create_file_row(main_window.pic_font, btn_pic_font), 0, 1)
    main_window.pic_system_font_combo = QComboBox()
    main_window.pic_system_font_combo.setFixedHeight(32)
    main_window.pic_system_font_combo.setToolTip("选择系统已安装字体作为图片字库源字体")
    gd_pic.addWidget(QLabel("系统字体:"), 1, 0)
    gd_pic.addWidget(main_window.pic_system_font_combo, 1, 1)
    gd_pic.addWidget(QLabel("保存目录:"), 2, 0)
    gd_pic.addWidget(main_window.pic_folder, 2, 1)
    gd_pic.addWidget(QLabel("图片格式:"), 3, 0)
    gd_pic.addWidget(main_window.pic_fmt, 3, 1)
    main_window.pic_fs = IOSInput("38", "38")
    main_window.pic_fs.setToolTip("字体渲染大小")
    main_window.pic_cnt = IOSInput("19", "19")
    main_window.pic_cnt.setToolTip("每行包含多少个字符")
    gd_pic.addWidget(QLabel("字体大小(px):"), 0, 2)
    gd_pic.addWidget(main_window.pic_fs, 0, 3)
    main_window.pic_fs.textChanged.connect(lambda _text: apply_pic_font_size_preset(main_window))

    gd_pic.addWidget(QLabel("每行字符数:"), 1, 2)
    gd_pic.addWidget(main_window.pic_cnt, 1, 3)
    main_window.pic_cw = IOSInput("W", "38")
    main_window.pic_ch = IOSInput("H", "38")
    main_window.pic_iw = IOSInput("IX", "10")
    main_window.pic_ih = IOSInput("Y", "10")
    gd_pic.addWidget(QLabel("单字符宽高:"), 2, 2)
    box_wh = QHBoxLayout()
    box_wh.addWidget(main_window.pic_cw)
    box_wh.addWidget(main_window.pic_ch)
    gd_pic.addLayout(box_wh, 2, 3)
    gd_pic.addWidget(QLabel("间距/行距:"), 3, 2)
    box_int = QHBoxLayout()
    box_int.addWidget(main_window.pic_iw)
    box_int.addWidget(main_window.pic_ih)
    gd_pic.addLayout(box_int, 3, 3)
    main_window.pic_imw = IOSInput("W", "1024")
    main_window.pic_imh = IOSInput("H", "640")
    main_window.pic_ix = IOSInput("X", "10")
    main_window.pic_iy = IOSInput("Y", "12")
    gd_pic.addWidget(QLabel("单图总尺寸:"), 4, 0)
    box_im = QHBoxLayout()
    box_im.addWidget(main_window.pic_imw)
    box_im.addWidget(main_window.pic_imh)
    gd_pic.addLayout(box_im, 4, 1)
    gd_pic.addWidget(QLabel("起始偏移XY:"), 4, 2)
    box_xy = QHBoxLayout()
    box_xy.addWidget(main_window.pic_ix)
    box_xy.addWidget(main_window.pic_iy)
    gd_pic.addLayout(box_xy, 4, 3)
    l_pic.addLayout(gd_pic)

    adv_group = QGroupBox("高级渲染设置")
    adv_group.setStyleSheet("QGroupBox { border: none; margin-top: 8px; } QGroupBox::title { subcontrol-origin: margin; left: 0px; padding: 0 4px 0 0; }")
    adv_layout = QGridLayout(adv_group)
    adv_layout.setSpacing(10)

    main_window.pic_bold_s = IOSInput("2", "2")
    main_window.pic_out_w = IOSInput("1", "1")
    main_window.pic_shd_x = IOSInput("2", "2")
    main_window.pic_shd_y = IOSInput("1", "1")

    adv_layout.addWidget(QLabel("粗体强度:"), 0, 0)
    adv_layout.addWidget(main_window.pic_bold_s, 0, 1)
    adv_layout.addWidget(QLabel("描边宽度:"), 0, 2)
    adv_layout.addWidget(main_window.pic_out_w, 0, 3)
    adv_layout.addWidget(QLabel("阴影偏移X:"), 0, 4)
    adv_layout.addWidget(main_window.pic_shd_x, 0, 5)
    adv_layout.addWidget(QLabel("阴影偏移Y:"), 0, 6)
    adv_layout.addWidget(main_window.pic_shd_y, 0, 7)

    main_window.pic_color_f = IOSInput("(255,255,255,255)", "(255,255,255,255)")
    main_window.pic_color_o = IOSInput("(0,0,0,255)", "(0,0,0,255)")
    main_window.pic_color_s = IOSInput("(0,0,0,255)", "(0,0,0,255)")
    main_window.pic_color_b = IOSInput("(0,0,0,0)", "(0,0,0,0)")

    adv_layout.addWidget(QLabel("填充颜色:"), 1, 0)
    adv_layout.addWidget(main_window.pic_color_f, 1, 1)
    adv_layout.addWidget(QLabel("描边颜色:"), 1, 2)
    adv_layout.addWidget(main_window.pic_color_o, 1, 3)
    adv_layout.addWidget(QLabel("阴影颜色:"), 1, 4)
    adv_layout.addWidget(main_window.pic_color_s, 1, 5)
    adv_layout.addWidget(QLabel("背景颜色:"), 1, 6)
    adv_layout.addWidget(main_window.pic_color_b, 1, 7)

    main_window.pic_kw_b = IOSInput("太", "太")
    main_window.pic_kw_o = IOSInput("袋", "袋")
    main_window.pic_kw_s = IOSInput("影", "影")
    main_window.pic_add_char = IOSInput("･", "･")

    adv_layout.addWidget(QLabel("粗体关键字:"), 2, 0)
    adv_layout.addWidget(main_window.pic_kw_b, 2, 1)
    adv_layout.addWidget(QLabel("描边关键字:"), 2, 2)
    adv_layout.addWidget(main_window.pic_kw_o, 2, 3)
    adv_layout.addWidget(QLabel("阴影关键字:"), 2, 4)
    adv_layout.addWidget(main_window.pic_kw_s, 2, 5)
    adv_layout.addWidget(QLabel("缺字填充符:"), 2, 6)
    adv_layout.addWidget(main_window.pic_add_char, 2, 7)

    main_window.pic_sym_ll = IOSInput("，、。．；：！？", "，、。．；：！？")
    main_window.pic_sym_left = IOSInput("“”‘’'\"°′″", "“”‘’'\"°′″")
    main_window.pic_sym_ellipsis = IOSInput("…", "…")
    main_window.pic_sym_bottom = IOSInput("…？", "…？")
    main_window.pic_sym_center = IOSInput("‥·", "‥·")

    adv_layout.addWidget(QLabel("左下标点:"), 3, 0)
    adv_layout.addWidget(main_window.pic_sym_ll, 3, 1)
    adv_layout.addWidget(QLabel("贴左字符:"), 3, 2)
    adv_layout.addWidget(main_window.pic_sym_left, 3, 3)
    adv_layout.addWidget(QLabel("省略号类:"), 3, 4)
    adv_layout.addWidget(main_window.pic_sym_ellipsis, 3, 5)
    adv_layout.addWidget(QLabel("底部对齐:"), 3, 6)
    adv_layout.addWidget(main_window.pic_sym_bottom, 3, 7)

    main_window.pic_punc_x = IOSInput("2", "2")
    main_window.pic_punc_y = IOSInput("1", "1")
    main_window.pic_ellipsis_y = IOSInput("4", "4")
    main_window.pic_bottom_pad = IOSInput("0", "0")
    main_window.pic_center_y = IOSInput("2", "2")
    main_window.pic_left_pad = IOSInput("0", "0")

    adv_layout.addWidget(QLabel("左下X偏移:"), 4, 0)
    adv_layout.addWidget(main_window.pic_punc_x, 4, 1)
    adv_layout.addWidget(QLabel("左下Y偏移:"), 4, 2)
    adv_layout.addWidget(main_window.pic_punc_y, 4, 3)
    adv_layout.addWidget(QLabel("省略号Y偏移:"), 4, 4)
    adv_layout.addWidget(main_window.pic_ellipsis_y, 4, 5)
    adv_layout.addWidget(QLabel("底部留白:"), 4, 6)
    adv_layout.addWidget(main_window.pic_bottom_pad, 4, 7)

    adv_layout.addWidget(QLabel("视觉居中字符:"), 5, 0)
    adv_layout.addWidget(main_window.pic_sym_center, 5, 1)
    adv_layout.addWidget(QLabel("视觉居中Y偏移:"), 5, 2)
    adv_layout.addWidget(main_window.pic_center_y, 5, 3)
    adv_layout.addWidget(QLabel("贴左内边距:"), 5, 4)
    adv_layout.addWidget(main_window.pic_left_pad, 5, 5)
    l_pic.addWidget(adv_group)
    apply_pic_font_size_preset(main_window)
  
    l_pic.addStretch()
    main_window.imgfont_stack.addWidget(p_pic)

    
    # === 模式 1: TGA 字库 ===
    p_tga = QWidget()
    l_tga = QVBoxLayout(p_tga)
    l_tga.setContentsMargins(0, 10, 0, 0)
    gd_tga = QGridLayout()
    main_window.tga_font = IOSInput("输入字体", "game.ttf")
    btn_tga_font = QPushButton("📁")
    btn_tga_font.setFixedSize(40, 38)
    main_window.tga_dat = IOSInput("DAT文件名", "text")
    main_window.tga_dat.setToolTip("生成的索引文件名，不含后缀")
    main_window.tga_eng_n = IOSInput("引擎内字体名", "M+ 1c")
    main_window.tga_eng_n.setToolTip("游戏引擎内部识别的字体名称")
    main_window.tga_eng_p = IOSInput("虚拟路径", "IMG/text.tga")
    main_window.tga_eng_p.setToolTip("游戏内部读取纹理的虚拟路径")
    gd_tga.addWidget(QLabel("字体路径:"), 0, 0)
    gd_tga.addLayout(main_window.create_file_row(main_window.tga_font, btn_tga_font), 0, 1)
    main_window.tga_system_font_combo = QComboBox()
    main_window.tga_system_font_combo.setFixedHeight(32)
    main_window.tga_system_font_combo.setToolTip("选择系统已安装字体作为 TGA 字库源字体")
    gd_tga.addWidget(QLabel("系统字体:"), 1, 0)
    gd_tga.addWidget(main_window.tga_system_font_combo, 1, 1)
    gd_tga.addWidget(QLabel("索引文件名:"), 2, 0)
    gd_tga.addWidget(main_window.tga_dat, 2, 1)
    gd_tga.addWidget(QLabel("内部识别名:"), 3, 0)
    gd_tga.addWidget(main_window.tga_eng_n, 3, 1)
    gd_tga.addWidget(QLabel("游戏内路径:"), 4, 0)
    gd_tga.addWidget(main_window.tga_eng_p, 4, 1)
    main_window.tga_fs = IOSInput("", "22")
    main_window.tga_cw = IOSInput("W", "24")
    main_window.tga_ch = IOSInput("H", "24")
    main_window.tga_iw = IOSInput("X", "1")
    main_window.tga_ih = IOSInput("Y", "0")
    main_window.tga_w = IOSInput("W", "1024")
    main_window.tga_h = IOSInput("H", "4096")
    gd_tga.addWidget(QLabel("字号:"), 0, 2)
    gd_tga.addWidget(main_window.tga_fs, 0, 3)
    gd_tga.addWidget(QLabel("单字宽高:"), 1, 2)
    box_twh = QHBoxLayout()
    box_twh.addWidget(main_window.tga_cw)
    box_twh.addWidget(main_window.tga_ch)
    gd_tga.addLayout(box_twh, 1, 3)
    gd_tga.addWidget(QLabel("间距偏移:"), 2, 2)
    box_ti = QHBoxLayout()
    box_ti.addWidget(main_window.tga_iw)
    box_ti.addWidget(main_window.tga_ih)
    gd_tga.addLayout(box_ti, 2, 3)
    gd_tga.addWidget(QLabel("图集尺寸:"), 3, 2)
    box_tim = QHBoxLayout()
    box_tim.addWidget(main_window.tga_w)
    box_tim.addWidget(main_window.tga_h)
    gd_tga.addLayout(box_tim, 3, 3)
    l_tga.addLayout(gd_tga)
    l_tga.addStretch()
    main_window.imgfont_stack.addWidget(p_tga)
    
    # === 模式 2: BMP 字库 ===
    p_bmp = QWidget()
    l_bmp = QVBoxLayout(p_bmp)
    l_bmp.setContentsMargins(0, 10, 0, 0)
    gd_bmp = QGridLayout()
    main_window.bmp_font = IOSInput("输入字体", "game.ttf")
    btn_bmp_font = QPushButton("📁")
    btn_bmp_font.setFixedSize(40, 38)
    main_window.bmp_fs = IOSInput("Size", "60")
    main_window.bmp_sz = IOSInput("WxH", "64")
    main_window.bmp_cnt = IOSInput("Count", "16")
    main_window.bmp_w = IOSInput("Width", "1024")
    main_window.bmp_scale = IOSInput("Scale", "1.0")
    main_window.bmp_depth = IOSInput("Depth", "32")
    gd_bmp.addWidget(QLabel("字体路径:"), 0, 0)
    gd_bmp.addLayout(main_window.create_file_row(main_window.bmp_font, btn_bmp_font), 0, 1)
    main_window.bmp_system_font_combo = QComboBox()
    main_window.bmp_system_font_combo.setFixedHeight(32)
    main_window.bmp_system_font_combo.setToolTip("选择系统已安装字体作为 BMP 字库源字体")
    gd_bmp.addWidget(QLabel("系统字体:"), 1, 0)
    gd_bmp.addWidget(main_window.bmp_system_font_combo, 1, 1)
    gd_bmp.addWidget(QLabel("字号(pt/px):"), 2, 0)
    gd_bmp.addWidget(main_window.bmp_fs, 2, 1)
    gd_bmp.addWidget(QLabel("单字格大小:"), 3, 0)
    gd_bmp.addWidget(main_window.bmp_sz, 3, 1)
    gd_bmp.addWidget(QLabel("每行字数:"), 4, 0)
    gd_bmp.addWidget(main_window.bmp_cnt, 4, 1)
    gd_bmp.addWidget(QLabel("纹理宽度:"), 5, 0)
    gd_bmp.addWidget(main_window.bmp_w, 5, 1)
    gd_bmp.addWidget(QLabel("缩放倍率:"), 6, 0)
    gd_bmp.addWidget(main_window.bmp_scale, 6, 1)
    gd_bmp.addWidget(QLabel("颜色位深:"), 7, 0)
    gd_bmp.addWidget(main_window.bmp_depth, 7, 1)
    l_bmp.addLayout(gd_bmp)
    l_bmp.addStretch()
    main_window.imgfont_stack.addWidget(p_bmp)
    
    # === 模式 3: BMFont ===
    p_bmfont = QWidget()
    l_bmfont = QVBoxLayout(p_bmfont)
    l_bmfont.setContentsMargins(0, 10, 0, 0)
    gd_bm = QGridLayout()
    gd_bm.setSpacing(10)
    main_window.bm_font = IOSInput("请拖入字体文件", "game.ttf")
    main_window.bm_char_txt = IOSInput("请拖入包含所需字符的文本文件 (.txt)", "chars.txt")
    main_window.bm_out = IOSInput("输出文件名", "font.fnt")
    main_window.bm_size = IOSInput("字体大小 (pt)", "32")
    main_window.bm_tex_size = QComboBox()
    main_window.bm_tex_size.addItems(["512", "1024", "2048", "4096"])
    main_window.bm_tex_size.setCurrentIndex(1)
    main_window.bm_tex_size.setFixedHeight(38)
    btn_font = QPushButton("📁"); btn_font.setFixedSize(40, 38)
    btn_txt = QPushButton("📁"); btn_txt.setFixedSize(40, 38); btn_txt.clicked.connect(lambda: main_window.browse_folder(main_window.bm_char_txt))
    gd_bm.addWidget(QLabel("输入字体:"), 0, 0)
    gd_bm.addLayout(main_window.create_file_row(main_window.bm_font, btn_font), 0, 1)
    gd_bm.addWidget(QLabel("字符来源:"), 1, 0)
    l_txt = QHBoxLayout()
    l_txt.addWidget(main_window.bm_char_txt)
    l_txt.addWidget(btn_txt)
    gd_bm.addLayout(l_txt, 1, 1)
    gd_bm.addWidget(QLabel("输出文件:"), 2, 0)
    gd_bm.addWidget(main_window.bm_out, 2, 1)
    gd_bm.addWidget(QLabel("字体大小:"), 3, 0)
    gd_bm.addWidget(main_window.bm_size, 3, 1)
    gd_bm.addWidget(QLabel("纹理尺寸:"), 4, 0)
    gd_bm.addWidget(main_window.bm_tex_size, 4, 1)
    l_bmfont.addLayout(gd_bm)
    info_bm = QLabel(
        "<b>BMFont 格式用途：</b><br>"
        "针对标准位图字体格式的引擎。<br>"
        "字符来源支持 .txt 文件或文件夹 (将自动扫描包含的文本)"
    )
    info_bm.setStyleSheet("background: rgba(0,0,0,0.05); padding: 10px; border-radius: 8px; font-size: 11px;")
    l_bmfont.addWidget(info_bm)
    l_bmfont.addStretch()
    main_window.imgfont_stack.addWidget(p_bmfont)
    
    l.addWidget(main_window.imgfont_stack)
    if hasattr(main_window, 'init_system_font_combos'):
        main_window.init_system_font_combos()
    if hasattr(main_window, 'bind_system_font_combo'):
        main_window.bind_system_font_combo(main_window.pic_system_font_combo, main_window.pic_font)
        main_window.bind_system_font_combo(main_window.tga_system_font_combo, main_window.tga_font)
        main_window.bind_system_font_combo(main_window.bmp_system_font_combo, main_window.bmp_font)
    l.addStretch()
    
    main_window.btn_run_imgfont = IOSButton("开始生成")
    main_window.btn_run_imgfont.clicked.connect(main_window.do_gen_imgfont)
    l.addWidget(main_window.btn_run_imgfont)

def setup_mapping_manager_ui(main_window, parent_widget):
    main_layout = QHBoxLayout(parent_widget)
    splitter = QSplitter(Qt.Orientation.Horizontal)
    
    left_panel = QWidget()
    l_map = QVBoxLayout(left_panel)
    l_map.setContentsMargins(0, 0, 10, 0)
    main_window.lbl_map = QLabel("映射表生成")
    main_window.lbl_map.setAlignment(Qt.AlignmentFlag.AlignCenter)
    main_window.lbl_map.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
    l_map.addWidget(main_window.lbl_map)
    gd_map = QGridLayout()
    main_window.map_src = IOSInput("选择包含翻译文本的目录", "cn_text")
    main_window.map_src.setToolTip("请直接拖入文件夹到此输入框，或点击右侧按钮选择")
    main_window.btn_map_src = QPushButton("📁")
    main_window.btn_map_src.setFixedSize(40, 38)
    main_window.btn_map_src.clicked.connect(lambda: main_window.browse_folder(main_window.map_src))
    main_window.map_out = IOSInput("替换后文本保存目录", "cn_text_mapped")
    main_window.map_json = IOSInput("输出的JSON文件名", "custom_map.json")
    main_window.map_ext = IOSInput("txt; json", "txt; json")
    main_window.map_limit_font = IOSInput("可选：限制映射范围的字体", "")
    main_window.map_limit_font.setToolTip("只映射到该字体中存在的字符上")
    btn_limit_font = QPushButton("📁")
    btn_limit_font.setFixedSize(40, 38)
    gd_map.addWidget(QLabel("输入文本目录:"), 0, 0)
    box_ms = QHBoxLayout()
    box_ms.addWidget(main_window.map_src)
    box_ms.addWidget(main_window.btn_map_src)
    gd_map.addLayout(box_ms, 0, 1)
    gd_map.addWidget(QLabel("输出文本目录:"), 1, 0)
    gd_map.addWidget(main_window.map_out, 1, 1)
    gd_map.addWidget(QLabel("输出码表路径:"), 2, 0)
    gd_map.addWidget(main_window.map_json, 2, 1)
    gd_map.addWidget(QLabel("扫描文件类型:"), 3, 0)
    gd_map.addWidget(main_window.map_ext, 3, 1)
    gd_map.addWidget(QLabel("限制字体(选):"), 4, 0)
    gd_map.addLayout(main_window.create_file_row(main_window.map_limit_font, btn_limit_font), 4, 1)
    l_map.addLayout(gd_map)
    info_txt = QLabel("将包含翻译文本的文件夹直接拖入上方输入框即可")
    info_txt.setStyleSheet("color: gray; font-size: 11px;")
    l_map.addWidget(info_txt)
    main_window.btn_run_map = IOSButton("扫描并生成映射")
    main_window.btn_run_map.clicked.connect(main_window.do_gen_map)
    main_window.btn_checkup_map = IOSButton("检查缺字")
    main_window.btn_checkup_map.clicked.connect(lambda: main_window.do_checkup('map'))
    main_window.btn_preview_map = IOSButton("预览替换")
    main_window.btn_preview_map.clicked.connect(main_window.do_preview_mapping)
    main_window.btn_restore_map = IOSButton("还原文本")
    main_window.btn_restore_map.clicked.connect(main_window.do_restore_map)
    l_map.addStretch()
    btn_row_map = QHBoxLayout()
    btn_row_map.addWidget(main_window.btn_run_map)
    btn_row_map.addWidget(main_window.btn_preview_map)
    btn_row_map.addWidget(main_window.btn_restore_map)
    btn_row_map.addWidget(main_window.btn_checkup_map)
    l_map.addLayout(btn_row_map)
    
    right_panel = QWidget()
    l_edit = QVBoxLayout(right_panel)
    l_edit.setContentsMargins(10, 0, 0, 0)
    main_window.lbl_ed = QLabel("映射表编辑器")
    main_window.lbl_ed.setAlignment(Qt.AlignmentFlag.AlignCenter)
    main_window.lbl_ed.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
    l_edit.addWidget(main_window.lbl_ed)
    top_bar = QHBoxLayout()
    btn_load = QPushButton("读取JSON")
    btn_load.clicked.connect(main_window.load_json_to_table)
    btn_save = QPushButton("保存JSON")
    btn_save.clicked.connect(main_window.save_table_to_json)
    top_bar.addWidget(btn_load)
    top_bar.addWidget(btn_save)
    l_edit.addLayout(top_bar)
    main_window.map_table = QTableWidget()
    main_window.map_table.setColumnCount(3)
    main_window.map_table.setHorizontalHeaderLabels(["原文 (CN)", "映射 (CP932)", "备注"])
    header = main_window.map_table.horizontalHeader()
    header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
    header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
    header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
    main_window.map_table.setAlternatingRowColors(True)
    l_edit.addWidget(main_window.map_table)
    bot_bar = QHBoxLayout()
    main_window.in_new_key = QLineEdit()
    main_window.in_new_key.setPlaceholderText("原文")
    main_window.in_new_val = QLineEdit()
    main_window.in_new_val.setPlaceholderText("映射字")
    btn_add = QPushButton("添加")
    btn_add.clicked.connect(main_window.add_mapping_row)
    btn_del = QPushButton("删除选中")
    btn_del.clicked.connect(main_window.remove_mapping_row)
    bot_bar.addWidget(main_window.in_new_key)
    bot_bar.addWidget(main_window.in_new_val)
    bot_bar.addWidget(btn_add)
    bot_bar.addWidget(btn_del)
    l_edit.addLayout(bot_bar)
    
    splitter.addWidget(left_panel)
    splitter.addWidget(right_panel)
    splitter.setStretchFactor(0, 1)
    splitter.setStretchFactor(1, 1)
    main_layout.addWidget(splitter)

def setup_font_analysis_ui(main_window, parent_widget):
    main_layout = QHBoxLayout(parent_widget)
    splitter = QSplitter(Qt.Orientation.Horizontal)
    
    left_panel = QWidget()
    l_cmp = QVBoxLayout(left_panel)
    l_cmp.setContentsMargins(0, 0, 10, 0)
    main_window.lbl_cmp = QLabel("字符集对比")
    main_window.lbl_cmp.setAlignment(Qt.AlignmentFlag.AlignCenter)
    main_window.lbl_cmp.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
    l_cmp.addWidget(main_window.lbl_cmp)
    gd = QGridLayout()
    gd.setSpacing(10)
    main_window.cmp_font1 = IOSInput("字体 A", "fontA.ttf")
    main_window.cmp_font2 = IOSInput("字体 B", "fontB.ttf")
    btn_cmp_font1 = QPushButton("📁")
    btn_cmp_font1.setFixedSize(40, 38)
    btn_cmp_font2 = QPushButton("📁")
    btn_cmp_font2.setFixedSize(40, 38)
    gd.addWidget(QLabel("字体 A:"), 0, 0)
    gd.addLayout(main_window.create_file_row(main_window.cmp_font1, btn_cmp_font1), 0, 1)
    gd.addWidget(QLabel("字体 B:"), 1, 0)
    gd.addLayout(main_window.create_file_row(main_window.cmp_font2, btn_cmp_font2), 1, 1)
    l_cmp.addLayout(gd)
    main_window.cmp_result = QTextEdit()
    main_window.cmp_result.setReadOnly(True)
    main_window.cmp_result.setStyleSheet("background: rgba(0,0,0,0.03); border-radius: 8px; padding: 10px; font-family: 'Consolas', monospace;")
    main_window.cmp_result.setPlainText("点击下方按钮开始对比...")
    l_cmp.addWidget(main_window.cmp_result)
    btn_row = QHBoxLayout()
    main_window.btn_run_compare = IOSButton("开始对比")
    main_window.btn_export_diff = IOSButton("导出差异")
    main_window.btn_run_compare.clicked.connect(main_window.do_compare_fonts)
    main_window.btn_export_diff.clicked.connect(main_window.do_export_diff)
    btn_row.addWidget(main_window.btn_run_compare)
    btn_row.addWidget(main_window.btn_export_diff)
    l_cmp.addLayout(btn_row)
    main_window._compare_result = {}
    
    right_panel = QWidget()
    l_cov = QVBoxLayout(right_panel)
    l_cov.setContentsMargins(10, 0, 0, 0)
    main_window.lbl_cov = QLabel("字符覆盖率分析")
    main_window.lbl_cov.setAlignment(Qt.AlignmentFlag.AlignCenter)
    main_window.lbl_cov.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
    l_cov.addWidget(main_window.lbl_cov)
    gd_cov = QGridLayout()
    gd_cov.setSpacing(10)
    main_window.cov_font = IOSInput("请拖入要分析的字体", "game.ttf")
    btn_cov_font = QPushButton("📁")
    btn_cov_font.setFixedSize(40, 38)
    gd_cov.addWidget(QLabel("字体文件:"), 0, 0)
    gd_cov.addLayout(main_window.create_file_row(main_window.cov_font, btn_cov_font), 0, 1)
    l_cov.addLayout(gd_cov)
    main_window.cov_result = QTextEdit()
    main_window.cov_result.setReadOnly(True)
    main_window.cov_result.setStyleSheet("background: rgba(0,0,0,0.03); border-radius: 8px; padding: 10px; font-family: 'Consolas', monospace;")
    main_window.cov_result.setPlainText("点击下方按钮开始分析...")
    l_cov.addWidget(main_window.cov_result)
    main_window.btn_run_coverage = IOSButton("分析覆盖率")
    main_window.btn_run_coverage.clicked.connect(main_window.do_coverage_analysis)
    l_cov.addWidget(main_window.btn_run_coverage)
    
    splitter.addWidget(left_panel)
    splitter.addWidget(right_panel)
    splitter.setStretchFactor(0, 1)
    splitter.setStretchFactor(1, 1)
    main_layout.addWidget(splitter)

def setup_unified_fix_ui(main_window, parent_widget):
    l = QVBoxLayout(parent_widget)
    
    main_window.lbl_fix = QLabel("度量修复") 
    main_window.lbl_fix.setAlignment(Qt.AlignmentFlag.AlignCenter)
    main_window.lbl_fix.setFont(QFont("Microsoft YaHei", 14, QFont.Weight.Bold))
    l.addWidget(main_window.lbl_fix)

    gd = QGridLayout()
    gd.setSpacing(10)
    main_window.fix_src = IOSInput("拖入目标字体", "target.ttf")
    main_window.fix_ref = IOSInput("拖入参考字体", "ref.ttf")
    main_window.fix_out = IOSInput("输出文件名", "fixed.ttf")
    
    btn_src = QPushButton("📁")
    btn_src.setFixedSize(40, 38)
    btn_ref = QPushButton("📁")
    btn_ref.setFixedSize(40, 38)
    
    gd.addWidget(QLabel("1. 目标字体:"), 0, 0)
    gd.addLayout(main_window.create_file_row(main_window.fix_src, btn_src), 0, 1)
    gd.addWidget(QLabel("2. 参考字体:"), 1, 0)
    gd.addLayout(main_window.create_file_row(main_window.fix_ref, btn_ref), 1, 1)
    gd.addWidget(QLabel("3. 输出文件:"), 2, 0)
    gd.addWidget(main_window.fix_out, 2, 1)
    l.addLayout(gd)

    line = QFrame(); line.setFrameShape(QFrame.Shape.HLine); line.setStyleSheet("background:rgba(0,0,0,0.1)")
    l.addWidget(line)

    l.addWidget(QLabel("<b>字形调整</b> (可选)"))
    
    row_deform = QHBoxLayout()
    
    main_window.fix_scale_x = IOSInput("1.00", "1.00")
    main_window.fix_scale_y = IOSInput("1.00", "1.00")
    main_window.fix_spacing = IOSInput("0", "0")
    
    main_window.fix_scale_x.setToolTip("宽度倍率：小于1变瘦")
    main_window.fix_scale_y.setToolTip("高度倍率：小于1变矮")
    main_window.fix_spacing.setToolTip("额外字间距：像素单位")

    row_deform.addWidget(QLabel("字宽:"))
    row_deform.addWidget(main_window.fix_scale_x)
    row_deform.addSpacing(15)
    row_deform.addWidget(QLabel("字高:"))
    row_deform.addWidget(main_window.fix_scale_y)
    row_deform.addSpacing(15)
    row_deform.addWidget(QLabel("字间距:"))
    row_deform.addWidget(main_window.fix_spacing)
    
    l.addLayout(row_deform)
    l.addSpacing(5)

    tool_bar = QHBoxLayout()
    
    lbl_metrics = QLabel("<b>垂直度量</b> (Asc/Desc)")
    lbl_metrics.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    tool_bar.addWidget(lbl_metrics)
    
    btn_auto = QPushButton("自动计算")
    btn_auto.clicked.connect(main_window.read_unified_metrics)
    btn_auto.setCursor(Qt.CursorShape.PointingHandCursor)
    btn_auto.setFixedWidth(160)
    btn_auto.setStyleSheet("""
        QPushButton { 
            background-color: #E1F5FE; color: #0277BD; border: 1px solid #B3E5FC; 
            border-radius: 15px; padding: 4px; font-weight: bold;
        }
        QPushButton:hover { background-color: #81D4FA; color: white;}
    """)
    tool_bar.addWidget(btn_auto)
    
    l.addLayout(tool_bar)

    row_metrics = QHBoxLayout()
    
    main_window.fix_asc = IOSInput("上行高度", "880")
    main_window.fix_desc = IOSInput("下行高度", "-120")
    main_window.fix_gap = IOSInput("行间距", "0")
    
    row_metrics.addWidget(QLabel("上行高度:"))
    row_metrics.addWidget(main_window.fix_asc)
    row_metrics.addSpacing(10)
    row_metrics.addWidget(QLabel("下行高度:"))
    row_metrics.addWidget(main_window.fix_desc)
    row_metrics.addSpacing(10)
    row_metrics.addWidget(QLabel("行间距:"))
    row_metrics.addWidget(main_window.fix_gap)
    
    l.addLayout(row_metrics)
    
    l.addStretch()
    
    main_window.btn_do_fix = IOSButton("执行修复")
    main_window.btn_do_fix.clicked.connect(main_window.do_unified_fix)
    l.addWidget(main_window.btn_do_fix)

def setup_metrics_ui(main_window, parent_widget):
    l_metrics = QVBoxLayout(parent_widget)
    main_window.lbl_met = QLabel("字体垂直度量修正")
    main_window.lbl_met.setAlignment(Qt.AlignmentFlag.AlignCenter)
    main_window.lbl_met.setFont(QFont("Microsoft YaHei", 14, QFont.Weight.Bold))
    l_metrics.addWidget(main_window.lbl_met)

    gd_met = QGridLayout()
    gd_met.setSpacing(10)

    main_window.met_font_path = IOSInput("请拖入待修复字体", "fixed.ttf")
    main_window.met_ref_path = IOSInput("参考字体 (原版JP字体)", "original.ttf")

    main_window.in_ascender = IOSInput("Ascender (上行)", "880")
    main_window.in_descender = IOSInput("Descender (下行)", "-120")
    main_window.in_linegap = IOSInput("LineGap (行距)", "0")

    btn_read_met = QPushButton("读取数值")
    btn_read_met.setFixedHeight(38)
    btn_read_met.clicked.connect(main_window.read_font_metrics)
    main_window.btn_apply_met = IOSButton("应用并保存")
    main_window.btn_apply_met.clicked.connect(main_window.apply_font_metrics)

    gd_met.addWidget(QLabel("目标字体:"), 0, 0)
    gd_met.addWidget(main_window.met_font_path, 0, 1)
    gd_met.addWidget(QLabel("参考字体:"), 1, 0)
    gd_met.addWidget(main_window.met_ref_path, 1, 1)
    gd_met.addWidget(btn_read_met, 2, 0, 1, 2)

    gd_met.addWidget(QLabel("上行高度"), 3, 0)
    gd_met.addWidget(main_window.in_ascender, 3, 1)
    gd_met.addWidget(QLabel("下行高度:"), 4, 0)
    gd_met.addWidget(main_window.in_descender, 4, 1)
    gd_met.addWidget(QLabel("行间距"), 5, 0)
    gd_met.addWidget(main_window.in_linegap, 5, 1)

    l_metrics.addLayout(gd_met)
    l_metrics.addWidget(QLabel("用于解决翻译后文字在游戏中偏上、偏下或被截断的问题"))
    l_metrics.addStretch()
    l_metrics.addWidget(main_window.btn_apply_met)

def setup_subset_ui(main_window, parent_widget):
    l_sub = QVBoxLayout(parent_widget)
    main_window.lbl_sub = QLabel("精简瘦身")
    main_window.lbl_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
    main_window.lbl_sub.setFont(QFont("Microsoft YaHei", 14, QFont.Weight.Bold))
    l_sub.addWidget(main_window.lbl_sub)

    gd = QGridLayout()
    gd.setSpacing(10)

    main_window.sub_font = IOSInput("请拖入源字体 (通常是包含2万字的思源黑体)", "Source.ttf")
    main_window.sub_txt = IOSInput("文本目录 (用于扫描用字)", "cn_text")
    main_window.sub_json = IOSInput("映射表 (可选, 也会被包含)", "custom_map.json")
    main_window.sub_out = IOSInput("输出文件名", "game_subset.ttf")

    btn_scan_dir = QPushButton("📁")
    btn_scan_dir.setFixedSize(40, 38)
    btn_font = QPushButton("📁")
    btn_font.setFixedSize(40, 38)

    gd.addWidget(QLabel("1. 源字体:"), 0, 0)
    gd.addLayout(main_window.create_file_row(main_window.sub_font, btn_font), 0, 1)
    gd.addWidget(QLabel("2. 文本目录:"), 1, 0)
    gd.addLayout(main_window.create_file_row(main_window.sub_txt, btn_scan_dir), 1, 1)
    gd.addWidget(QLabel("3. 映射表(选):"), 2, 0)
    gd.addWidget(main_window.sub_json, 2, 1)
    gd.addWidget(QLabel("4. 输出文件:"), 3, 0)
    gd.addWidget(main_window.sub_out, 3, 1)

    l_sub.addLayout(gd)

    info = QLabel("""
    <b>功能说明：</b><br>
    <font color='#2196F3'>强制保留：ASCII + 日文假名 + 常用标点</font><br>
    <font color='#4CAF50'>智能扫描：仅保留文本目录和映射表中出现过的汉字和特殊符号</font><br>
    <font color='#F44336'>自动剔除：未使用的汉字、韩文、生僻符号将被删除</font><br>
    此模式可最大程度减小体积 (如 20MB -> 2~5MB)
    """)
    info.setStyleSheet("background: rgba(0,0,0,0.05); padding: 10px; border-radius: 8px; font-size: 12px;")
    l_sub.addWidget(info)

    l_sub.addStretch()

    main_window.btn_run_subset = IOSButton("开始精简")
    main_window.btn_run_subset.clicked.connect(main_window.do_subset)
    main_window.btn_checkup_subset = IOSButton("检查缺字")
    main_window.btn_checkup_subset.clicked.connect(lambda: main_window.do_checkup('subset'))

    btn_row_sub = QHBoxLayout()
    btn_row_sub.addWidget(main_window.btn_run_subset)
    btn_row_sub.addWidget(main_window.btn_checkup_subset)
    l_sub.addLayout(btn_row_sub)

def setup_merge_ui(main_window, parent_widget):
    l_merge = QVBoxLayout(parent_widget)
    main_window.lbl_merge = QLabel("合并补字")
    main_window.lbl_merge.setAlignment(Qt.AlignmentFlag.AlignCenter)
    main_window.lbl_merge.setFont(QFont("Microsoft YaHei", 14, QFont.Weight.Bold))
    l_merge.addWidget(main_window.lbl_merge)

    gd = QGridLayout()
    gd.setSpacing(10)

    main_window.merge_base = IOSInput("基础字体 (缺字的字体)", "base.ttf")
    main_window.merge_add = IOSInput("来源字体 (有字的字体)", "source.ttf")
    main_window.merge_out = IOSInput("输出文件名", "merged.ttf")
    main_window.merge_filter = IOSInput("可选：仅添加这些字符 (留空则添加所有缺字)", "")
    main_window.merge_filter.setToolTip("在此输入您想从来源字体中提取的具体字符（如'♥★'）。\n如果不填，程序会自动把来源字体中所有基础字体没有的字都补进去。")
    main_window.merge_replace = IOSInput("可选：强制替换这些字符", "")
    main_window.merge_replace.setToolTip("即使基础字体中已经有了这些字符，也会强制使用来源字体中的字形替换它们。")

    btn_merge_base = QPushButton("📁")
    btn_merge_base.setFixedSize(40, 38)
    btn_merge_add = QPushButton("📁")
    btn_merge_add.setFixedSize(40, 38)

    gd.addWidget(QLabel("1. 基础字体:"), 0, 0)
    gd.addLayout(main_window.create_file_row(main_window.merge_base, btn_merge_base), 0, 1)
    gd.addWidget(QLabel("2. 来源字体:"), 1, 0)
    gd.addLayout(main_window.create_file_row(main_window.merge_add, btn_merge_add), 1, 1)
    gd.addWidget(QLabel("3. 输出文件:"), 2, 0)
    gd.addWidget(main_window.merge_out, 2, 1)
    gd.addWidget(QLabel("4. 仅补这些字:"), 3, 0)
    gd.addWidget(main_window.merge_filter, 3, 1)
    gd.addWidget(QLabel("5. 强制替换字:"), 4, 0)
    gd.addWidget(main_window.merge_replace, 4, 1)

    l_merge.addLayout(gd)

    info = QLabel("""
    <b>功能说明：</b><br>
    将<b>来源字体</b>中的字形合并到<b>基础字体</b>中。<br>
    <font color='#2196F3'>场景：字体1缺了几个字，想从字体2里拿过来</font><br>
    <font color='#4CAF50'>用法：在"指定字符"框中输入那几个字，点击合并即可</font>
    """)
    info.setStyleSheet("background: rgba(0,0,0,0.05); padding: 10px; border-radius: 8px; font-size: 12px;")
    l_merge.addWidget(info)

    l_merge.addStretch()

    main_window.btn_run_merge = IOSButton("开始合并")
    main_window.btn_run_merge.clicked.connect(main_window.do_merge_fonts)
    l_merge.addWidget(main_window.btn_run_merge)

def setup_info_ui(main_window, parent_widget):
    l_info = QVBoxLayout(parent_widget)
    
    main_window.lbl_info = QLabel("字体信息编辑")
    main_window.lbl_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
    main_window.lbl_info.setFont(QFont("Microsoft YaHei", 14, QFont.Weight.Bold))
    l_info.addWidget(main_window.lbl_info)

    gd = QGridLayout()
    gd.setSpacing(10)
    main_window.info_font = IOSInput("拖入字体文件", "font.ttf")
    
    btn_browse = QPushButton("📁")
    btn_browse.setFixedSize(40, 38)
    
    gd.addWidget(QLabel("字体文件:"), 0, 0)
    gd.addLayout(main_window.create_file_row(main_window.info_font, btn_browse), 0, 1)
    l_info.addLayout(gd)

    main_window.info_table = QTableWidget()
    main_window.info_table.setColumnCount(3)
    main_window.info_table.setHorizontalHeaderLabels(["ID", "字段名称", "内容 (双击修改)"])
    
    header = main_window.info_table.horizontalHeader()
    header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
    header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
    header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
    
    main_window.info_table.verticalHeader().setVisible(False)
    main_window.info_table.setAlternatingRowColors(True)
    
    l_info.addWidget(main_window.info_table)

    btn_row = QHBoxLayout()
    main_window.btn_read_info = IOSButton("读取信息")
    main_window.btn_save_info = IOSButton("保存修改")
    
    main_window.btn_read_info.clicked.connect(main_window.do_read_font_info)
    main_window.btn_save_info.clicked.connect(main_window.do_save_font_info)
    
    btn_row.addWidget(main_window.btn_read_info)
    btn_row.addWidget(main_window.btn_save_info)
    l_info.addLayout(btn_row)

def setup_compare_ui(main_window, parent_widget):
    l_cmp = QVBoxLayout(parent_widget)
    main_window.lbl_cmp = QLabel("字符集对比")
    main_window.lbl_cmp.setAlignment(Qt.AlignmentFlag.AlignCenter)
    main_window.lbl_cmp.setFont(QFont("Microsoft YaHei", 14, QFont.Weight.Bold))
    l_cmp.addWidget(main_window.lbl_cmp)

    gd = QGridLayout()
    gd.setSpacing(10)
    main_window.cmp_font1 = IOSInput("字体 A", "fontA.ttf")
    main_window.cmp_font2 = IOSInput("字体 B", "fontB.ttf")
    gd.addWidget(QLabel("字体 A:"), 0, 0)
    gd.addWidget(main_window.cmp_font1, 0, 1)
    gd.addWidget(QLabel("字体 B:"), 1, 0)
    gd.addWidget(main_window.cmp_font2, 1, 1)
    l_cmp.addLayout(gd)

    main_window.cmp_result = QTextEdit()
    main_window.cmp_result.setReadOnly(True)
    main_window.cmp_result.setStyleSheet("background: rgba(0,0,0,0.03); border-radius: 8px; padding: 10px; font-family: 'Consolas', monospace;")
    main_window.cmp_result.setPlainText("点击下方按钮开始对比...")
    l_cmp.addWidget(main_window.cmp_result)

    btn_row = QHBoxLayout()
    main_window.btn_run_compare = IOSButton("开始对比")
    main_window.btn_export_diff = IOSButton("导出差异")
    main_window.btn_run_compare.clicked.connect(main_window.do_compare_fonts)
    main_window.btn_export_diff.clicked.connect(main_window.do_export_diff)
    btn_row.addWidget(main_window.btn_run_compare)
    btn_row.addWidget(main_window.btn_export_diff)
    l_cmp.addLayout(btn_row)

    main_window._compare_result = {}

def setup_smart_fallback_ui(main_window, parent_widget):
    l_smart = QVBoxLayout(parent_widget)
    lbl = QLabel("智能补字")
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lbl.setFont(QFont("Microsoft YaHei", 14, QFont.Weight.Bold))
    lbl.setStyleSheet(f"color: {main_window.theme['text_main']};")
    l_smart.addWidget(lbl)
    gd = QGridLayout()
    gd.setSpacing(10)
    main_window.sf_primary = IOSInput("主字体 (缺字的那个)", "game.ttf")
    btn_sf_primary = QPushButton("📁")
    btn_sf_primary.setFixedSize(40, 38)
    main_window.sf_txt = IOSInput("文本目录 (检查这些文本里的字)", "cn_text")
    main_window.sf_lib = IOSInput("补全库目录 (存放很多字体的文件夹)", "fonts_library")
    btn_scan_txt = QPushButton("📁")
    btn_scan_txt.setFixedSize(40, 38)
    btn_scan_lib = QPushButton("📁")
    btn_scan_lib.setFixedSize(40, 38)
    gd.addWidget(QLabel("1. 主字体:"), 0, 0)
    gd.addLayout(main_window.create_file_row(main_window.sf_primary, btn_sf_primary), 0, 1)
    gd.addWidget(QLabel("2. 文本源:"), 1, 0)
    gd.addLayout(main_window.create_file_row(main_window.sf_txt, btn_scan_txt), 1, 1)
    gd.addWidget(QLabel("3. 补全库:"), 2, 0)
    gd.addLayout(main_window.create_file_row(main_window.sf_lib, btn_scan_lib), 2, 1)
    l_smart.addLayout(gd)
    main_window.sf_table = QTableWidget()
    main_window.sf_table.setColumnCount(3)
    main_window.sf_table.setHorizontalHeaderLabels(["缺失字符", "Unicode", "推荐来源字体"])
    main_window.sf_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
    l_smart.addWidget(main_window.sf_table)
    btn_box = QHBoxLayout()
    main_window.btn_run_smart = IOSButton("开始分析")
    main_window.btn_run_smart.clicked.connect(main_window.do_smart_fallback_scan)
    main_window.btn_export_smart = QPushButton("导出补全清单")
    main_window.btn_export_smart.setFixedHeight(45)
    main_window.btn_export_smart.clicked.connect(main_window.export_smart_result)
    btn_box.addWidget(main_window.btn_run_smart)
    btn_box.addWidget(main_window.btn_export_smart)
    l_smart.addLayout(btn_box)
    hint = QLabel("工具会扫描库中所有字体，优先推荐包含缺字数量最多的那个")
    hint.setStyleSheet("color: gray; font-size: 11px;")
    l_smart.addWidget(hint)

def setup_woff2_ui(main_window, parent_widget):
    l = QVBoxLayout(parent_widget)
    main_window.lbl_woff2 = QLabel("Web转换")
    main_window.lbl_woff2.setAlignment(Qt.AlignmentFlag.AlignCenter)
    main_window.lbl_woff2.setFont(QFont("Microsoft YaHei", 14, QFont.Weight.Bold))
    l.addWidget(main_window.lbl_woff2)

    if not HAS_BROTLI:
        warn = QLabel("未安装 brotli 模块，无法使用此功能。\n请在终端运行: pip install brotli")
        warn.setStyleSheet("color: red; padding: 20px; font-size: 14px; background: rgba(255,0,0,0.1); border-radius: 10px;")
        warn.setAlignment(Qt.AlignmentFlag.AlignCenter)
        l.addWidget(warn)
        l.addStretch()
        return

    gd = QGridLayout()
    gd.setSpacing(10)
    main_window.woff2_src = IOSInput("请拖入 TTF/OTF 字体", "font.ttf")
    main_window.woff2_out = IOSInput("输出文件名", "webfont.woff2")
    btn = QPushButton("📁")
    btn.setFixedSize(40, 38)
    
    gd.addWidget(QLabel("源字体:"), 0, 0)
    gd.addLayout(main_window.create_file_row(main_window.woff2_src, btn), 0, 1)
    gd.addWidget(QLabel("输出文件:"), 1, 0)
    gd.addWidget(main_window.woff2_out, 1, 1)
    l.addLayout(gd)

    info = QLabel(
        "<b>WOFF2 格式用途：</b><br>"
        "1. Web 游戏 / H5 游戏<br>"
        "2. 基于 Electron 的游戏引擎<br>"
        "3. RPG Maker MZ 等支持 WOFF2 的引擎<br>"
        "WOFF2 具有极高的压缩率，通常比 TTF 小 40-70%"
    )
    info.setStyleSheet("background: rgba(0,0,0,0.05); padding: 15px; border-radius: 8px; font-size: 12px; line-height: 150%;")
    l.addWidget(info)
    l.addStretch()

    main_window.btn_run_woff2 = IOSButton("开始压缩转换")
    main_window.btn_run_woff2.clicked.connect(main_window.do_gen_woff2)
    l.addWidget(main_window.btn_run_woff2)

def setup_cleanup_ui(main_window, parent_widget):
    l = QVBoxLayout(parent_widget)
    main_window.lbl_clean = QLabel("兼容清理")
    main_window.lbl_clean.setAlignment(Qt.AlignmentFlag.AlignCenter)
    main_window.lbl_clean.setFont(QFont("Microsoft YaHei", 14, QFont.Weight.Bold))
    l.addWidget(main_window.lbl_clean)

    gd = QGridLayout()
    gd.setSpacing(10)
    main_window.clean_src = IOSInput("请拖入字体文件", "game.ttf")
    main_window.clean_out = IOSInput("输出文件名", "game_clean.ttf")
    btn = QPushButton("📁")
    btn.setFixedSize(40, 38)
    
    gd.addWidget(QLabel("源字体:"), 0, 0)
    gd.addLayout(main_window.create_file_row(main_window.clean_src, btn), 0, 1)
    gd.addWidget(QLabel("输出文件:"), 1, 0)
    gd.addWidget(main_window.clean_out, 1, 1)
    l.addLayout(gd)

    l.addWidget(QLabel("选择要移除的表 (提高老引擎兼容性):"))
    
    main_window.chk_gsub = QCheckBox("移除 Ligatures (连字, GSUB)")
    main_window.chk_gpos = QCheckBox("移除 Kerning (字距, GPOS)")
    main_window.chk_hdmx = QCheckBox("移除 Device Metrics (hdmx)")
    main_window.chk_vdmx = QCheckBox("移除 Vertical Device Metrics (VDMX)")
    main_window.chk_hint = QCheckBox("移除 Hinting (微调指令)")
    main_window.chk_name = QCheckBox("精简 Name 表 (仅保留核心信息)")
    
    config_layout = QGridLayout()
    config_layout.addWidget(main_window.chk_gsub, 0, 0)
    config_layout.addWidget(main_window.chk_gpos, 0, 1)
    config_layout.addWidget(main_window.chk_hdmx, 1, 0)
    config_layout.addWidget(main_window.chk_vdmx, 1, 1)
    config_layout.addWidget(main_window.chk_hint, 2, 0)
    config_layout.addWidget(main_window.chk_name, 2, 1)
    
    main_window.chk_gsub.setChecked(True)
    main_window.chk_gpos.setChecked(True)
    main_window.chk_hdmx.setChecked(True)
    main_window.chk_vdmx.setChecked(True)
    
    l.addLayout(config_layout)

    info = QLabel(
        "<b>用途：</b><br>"
        "针对无法正确解析复杂 OpenType 特性的引擎。<br>"
        "表现为：游戏崩溃、文字重叠、行距异常。<br>"
        "使用此功能清理掉不需要的高级表，可以显著提高兼容性并减小体积。"
    )
    info.setStyleSheet("background: rgba(0,0,0,0.05); padding: 15px; border-radius: 8px; font-size: 12px; line-height: 150%;")
    l.addWidget(info)
    l.addStretch()

    main_window.btn_run_clean = IOSButton("开始清理")
    main_window.btn_run_clean.clicked.connect(main_window.do_cleanup)
    l.addWidget(main_window.btn_run_clean)

def setup_preview_ui(main_window, parent_layout):
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setStyleSheet("background: rgba(0,0,0,0.1);")
    parent_layout.addWidget(line)
    parent_layout.addSpacing(5)

    main_window.lbl_preview_title = main_window.create_label("效果预览")
    main_window.lbl_preview_title.setFont(QFont("Microsoft YaHei", 10, QFont.Weight.Bold))
    parent_layout.addWidget(main_window.lbl_preview_title)

    main_window.preview_input = IOSInput("输入预览文本...", "测试文本 Test 123")
    main_window.preview_input.setToolTip("输入您想预览的文本")
    main_window.preview_input.textChanged.connect(main_window.update_previews)
    main_window.preview_input.setFixedHeight(30)
    parent_layout.addWidget(main_window.preview_input)

    main_window.preview_area = QTextEdit("预览")
    main_window.preview_area.setReadOnly(True)
    main_window.preview_area.setFontPointSize(16)
    main_window.preview_area.setFixedHeight(70)
    main_window.preview_area.setToolTip("字体预览")
    parent_layout.addWidget(main_window.preview_area)

    main_window.preview_labels = [main_window.lbl_preview_title]