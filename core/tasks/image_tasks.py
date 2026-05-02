import json
import os
import struct
import threading
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont
from core.system_fonts import resolve_font_path, resolve_font_spec


FONT_RENDER_THREAD_STATE = threading.local()
FONT_STYLE_DIRS = [
    "源ノ角ゴシック",
    "源ノ角ゴシック_影",
    "源ノ角ゴシック_影袋",
    "源ノ角ゴシック_太",
    "源ノ角ゴシック_太影",
    "源ノ角ゴシック_太影袋",
    "源ノ角ゴシック_太袋",
    "源ノ角ゴシック_袋",
]
FONT_PRESET_FIELDS = ("font_size", "img_w", "img_h", "offset_x", "offset_y", "cell_w", "cell_h", "columns", "rows")
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
FONT_PRESET_CONFIG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'font_presets.json'))

def _get_default_font_presets():
    return {int(size): dict(preset) for size, preset in DEFAULT_FONT_PRESETS.items()}

def _normalize_font_presets(presets=None):
    source = presets if presets is not None else _get_default_font_presets()
    normalized = {}
    for raw_size, raw_preset in dict(source).items():
        size = int(raw_size)
        if size <= 0:
            raise ValueError(f"字号必须大于 0: {raw_size}")
        if not isinstance(raw_preset, dict):
            raise ValueError(f"字号 {size} 的预设格式无效")
        preset = {}
        for field in FONT_PRESET_FIELDS:
            if field not in raw_preset:
                raise ValueError(f"字号 {size} 缺少字段: {field}")
            value = int(raw_preset[field])
            if field in {"offset_x", "offset_y"}:
                preset[field] = value
            elif value <= 0:
                raise ValueError(f"字号 {size} 的 {field} 必须大于 0")
            else:
                preset[field] = value
        normalized[size] = preset
    return dict(sorted(normalized.items()))

def _load_font_presets():
    defaults = _get_default_font_presets()
    if not os.path.exists(FONT_PRESET_CONFIG_PATH):
        return defaults
    try:
        with open(FONT_PRESET_CONFIG_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return _normalize_font_presets(data)
    except Exception:
        return defaults

def _get_pic_preset(conf):
    raw_size = conf.get('preset_size', conf.get('fsize'))
    try:
        size = int(raw_size)
    except (TypeError, ValueError):
        return None
    presets = _load_font_presets()
    return presets.get(size)

def _apply_pic_preset(conf):
    normalized = dict(conf)
    preset = _get_pic_preset(conf)
    if not preset:
        return normalized
    normalized['preset_size'] = int(conf.get('preset_size', conf.get('fsize', preset['font_size'])))
    normalized['fsize'] = preset['font_size']
    normalized['count'] = preset['columns']
    normalized['cw'] = preset['cell_w']
    normalized['ch'] = preset['cell_h']
    normalized['img_w'] = preset['img_w']
    normalized['img_h'] = preset['img_h']
    normalized['ix'] = preset['offset_x']
    normalized['iy'] = preset['offset_y']
    normalized['rows'] = preset['rows']
    return normalized


def _get_jp_chars():
    fl = list(range(0x81, 0xA0)) + list(range(0xE0, 0xF1)) + list(range(0xFA, 0xFD))
    sl = list(range(0x40, 0x7F)) + list(range(0x80, 0xFD))
    return fl, sl


def _split_tokens(value, default):
    if value is None:
        return tuple(default)
    if isinstance(value, (list, tuple, set)):
        tokens = []
        for item in value:
            tokens.extend(_split_tokens(item, ()))
        return tuple(dict.fromkeys(token for token in tokens if token)) or tuple(default)
    text = str(value).strip()
    if not text:
        return tuple(default)
    parts = [part.strip() for part in text.replace("，", ",").replace(";", ",").split(",")]
    tokens = [part for part in parts if part]
    return tuple(dict.fromkeys(tokens)) or tuple(default)


def _split_chars(value, default):
    if value is None:
        return tuple(default)
    if isinstance(value, (list, tuple, set)):
        chars = []
        for item in value:
            chars.extend(_split_chars(item, ()))
        return tuple(dict.fromkeys(char for char in chars if char)) or tuple(default)
    text = str(value).strip()
    if not text:
        return tuple(default)
    if "," in text or "，" in text or ";" in text:
        parts = [part.strip() for part in text.replace("，", ",").replace(";", ",").split(",")]
        chars = [part for part in parts if part]
    else:
        chars = [char for char in text if not char.isspace()]
    return tuple(dict.fromkeys(chars)) or tuple(default)


def _normalize_pic_conf(conf):

    normalized = _apply_pic_preset(conf)
    normalized['bold_s'] = max(0, int(conf.get('bold_s', 2)))
    normalized['out_w'] = max(0, int(conf.get('out_w', 1)))
    normalized['shd_x'] = int(conf.get('shd_x', 2))
    normalized['shd_y'] = int(conf.get('shd_y', 1))
    normalized['count'] = max(1, int(normalized['count']))
    normalized['cw'] = max(1, int(normalized['cw']))
    normalized['ch'] = max(1, int(normalized['ch']))
    normalized['img_w'] = max(1, int(normalized['img_w']))
    normalized['img_h'] = max(1, int(normalized['img_h']))
    normalized['fsize'] = max(1, int(normalized['fsize']))
    normalized['ix'] = int(normalized['ix'])
    normalized['iy'] = int(normalized['iy'])
    normalized['rows'] = max(1, int(normalized.get('rows', 9999)))
    normalized['workers'] = max(1, min(8, int(conf.get('workers', os.cpu_count() or 1))))
    normalized['kw_b'] = _split_tokens(conf.get('kw_b', '太'), ('太',))
    normalized['kw_o'] = _split_tokens(conf.get('kw_o', '袋'), ('袋',))
    normalized['kw_s'] = _split_tokens(conf.get('kw_s', '影'), ('影',))
    normalized['add_char'] = str(conf.get('add_char', '･') or '･')[0]
    normalized['format'] = str(conf.get('format', 'png')).lower()
    normalized['sym_ll'] = _split_chars(conf.get('sym_ll', '，、。．；：！？'), ('，', '、', '。', '．', '；', '：', '！', '？'))
    normalized['sym_left'] = _split_chars(conf.get('sym_left', '“”‘’\'"°′″'), ('“', '”', '‘', '’', "'", '"', '°', '′', '″'))
    normalized['sym_ellipsis'] = _split_chars(conf.get('sym_ellipsis', '…'), ('…',))
    normalized['sym_bottom'] = _split_chars(conf.get('sym_bottom', '…？'), ('…', '？'))
    normalized['sym_center'] = _split_chars(conf.get('sym_center', '‥·'), ('‥', '·'))
    normalized['punc_x'] = max(0, int(conf.get('punc_x', 2)))
    normalized['punc_y'] = int(conf.get('punc_y', 1))
    normalized['ellipsis_y'] = int(conf.get('ellipsis_y', 4))
    normalized['bottom_pad'] = int(conf.get('bottom_pad', 0))
    normalized['center_y'] = int(conf.get('center_y', 2))
    normalized['left_pad'] = int(conf.get('left_pad', 0))
    return normalized



def _build_cp932_page_map(add_char='･'):
    fl, sl = _get_jp_chars()
    page_map = []
    for lead in fl:
        entries = []
        valid = 0
        for slot_index, trail in enumerate(sl):
            try:
                char = bytes((lead, trail)).decode('cp932')
                valid += 1
            except UnicodeDecodeError:
                char = add_char
            entries.append((slot_index, trail, char))
        if valid > 0:
            page_map.append({'lead': lead, 'entries': entries, 'valid': valid})
    return page_map


def _build_bold_offsets(strength: int):
    return [(step, 0) for step in range(1, max(0, int(strength)) + 1)]

def _shift_mask(mask, offset_x: int, offset_y: int):
    shifted = Image.new("L", mask.size, 0)
    w, h = mask.size
    sx0 = max(0, -offset_x)
    sy0 = max(0, -offset_y)
    sx1 = min(w, w - offset_x)
    sy1 = min(h, h - offset_y)
    if sx0 >= sx1 or sy0 >= sy1:
        return shifted
    region = mask.crop((sx0, sy0, sx1, sy1))
    shifted.paste(region, (max(0, offset_x), max(0, offset_y)))
    return shifted

def _colored_mask_image(mask, color):
    if mask.getbbox() is None:
        return None
    layer = Image.new("RGBA", mask.size, color)
    layer.putalpha(mask)
    return layer

def _baseline_y_for_cell(font, y: int, cell_height: int) -> float:
    ascent, descent = font.getmetrics()
    return y + (cell_height - (ascent + descent)) / 2 + ascent

def _create_pil_font(font_spec, font_size):
    font_path = str((font_spec or {}).get('path') or '')
    font_number = int((font_spec or {}).get('font_number', 0) or 0)
    return ImageFont.truetype(font_path, font_size, index=font_number)


def _get_font_render_context(font_spec, font_size):
    font_path = str((font_spec or {}).get('path') or '')
    font_number = int((font_spec or {}).get('font_number', 0) or 0)
    key = (os.path.abspath(font_path), font_number, int(font_size))
    context = getattr(FONT_RENDER_THREAD_STATE, 'render_context', None)
    if context is None or context['key'] != key:
        context = {
            'key': key,
            'font': _create_pil_font(font_spec, font_size),
            'glyph_metrics_cache': {},
        }
        FONT_RENDER_THREAD_STATE.render_context = context
    return context


def _detect_pic_style(dirname, conf):
    return {
        "bold": any(token in dirname for token in conf.get('kw_b', ('太',))),
        "outline": any(token in dirname for token in conf.get('kw_o', ('袋',))),
        "shadow": any(token in dirname for token in conf.get('kw_s', ('影',))),
    }


def _draw_glyph_to_cell(image, font, char, x, y, cell_width, cell_height, style, conf, glyph_metrics_cache=None):

    bold = style["bold"]
    shadow = style["shadow"]
    outline = style["outline"]

    bold_strength = conf.get('bold_s', 2)
    outline_width = conf.get('out_w', 1) if outline else 0

    shadow_offset_x = conf.get('shd_x', 2)
    shadow_offset_y = conf.get('shd_y', 1)
    fill_color = conf.get('color_f', (255, 255, 255, 255))
    outline_color = conf.get('color_o', (0, 0, 0, 255))
    shadow_color = conf.get('color_s', (0, 0, 0, 255))

    lower_left_chars = conf.get('sym_ll', ())
    left_edge_chars = conf.get('sym_left', ())
    ellipsis_chars = conf.get('sym_ellipsis', ())
    bottom_chars = conf.get('sym_bottom', ())
    optical_center_chars = conf.get('sym_center', ())
    punctuation_x_offset = conf.get('punc_x', 2)
    punctuation_y_offset = conf.get('punc_y', 1)
    ellipsis_y_offset = conf.get('ellipsis_y', 4)
    bottom_padding = conf.get('bottom_pad', 0)
    optical_center_y_offset = conf.get('center_y', 2)
    left_edge_padding = conf.get('left_pad', 0)

    anchor = "ls"

    cache_key = (char, outline_width)
    metrics = glyph_metrics_cache.get(cache_key) if glyph_metrics_cache is not None else None
    if metrics is None:
        left, top, right, bottom = font.getbbox(char, stroke_width=outline_width, anchor=anchor)
        metrics = (left, top, right, bottom)
        if glyph_metrics_cache is not None:
            glyph_metrics_cache[cache_key] = metrics
    else:
        left, top, right, bottom = metrics
    glyph_w = right - left

    draw_x = x + (cell_width - glyph_w) / 2 - left
    draw_y = _baseline_y_for_cell(font, y, cell_height)

    if char in left_edge_chars:
        draw_x = x + left_edge_padding - left
    if char in lower_left_chars:
        draw_x -= punctuation_x_offset
        draw_y += punctuation_y_offset
    if char in ellipsis_chars:
        draw_y += ellipsis_y_offset
    if char in bottom_chars:
        draw_y = y + cell_height - bottom_padding
    elif char in optical_center_chars:
        draw_y += optical_center_y_offset

    pad = max(2, outline_width + max(0, bold_strength), abs(shadow_offset_x), abs(shadow_offset_y)) + 2

    bbox_left = int(draw_x + left) - pad
    bbox_top = int(draw_y + top) - pad
    bbox_right = int(draw_x + left + glyph_w) + pad
    bbox_bottom = int(draw_y + bottom) + pad
    lw = max(1, bbox_right - bbox_left)
    lh = max(1, bbox_bottom - bbox_top)
    ox = draw_x - bbox_left
    oy = draw_y - bbox_top

    fill_mask = Image.new("L", (lw, lh), 0)
    mask_draw = ImageDraw.Draw(fill_mask)
    mask_draw.text((ox, oy), char, font=font, fill=255, anchor=anchor)
    if bold:
        for bx, by in _build_bold_offsets(bold_strength):
            mask_draw.text((ox + bx, oy + by), char, font=font, fill=255, anchor=anchor)

    if outline_width > 0:
        outline_mask = fill_mask.filter(ImageFilter.MaxFilter(size=outline_width * 2 + 1))
        outline_only_mask = ImageChops.subtract(outline_mask, fill_mask)
    else:
        outline_mask = fill_mask
        outline_only_mask = None

    glyph_layer = Image.new("RGBA", (lw, lh), (0, 0, 0, 0))
    if shadow:
        shadow_src = outline_mask if outline_width > 0 else fill_mask
        shadow_mask = _shift_mask(shadow_src, shadow_offset_x, shadow_offset_y)
        shadow_layer = _colored_mask_image(shadow_mask, shadow_color)
        if shadow_layer:
            glyph_layer.alpha_composite(shadow_layer)

    if outline_only_mask is not None:
        outline_layer = _colored_mask_image(outline_only_mask, outline_color)
        if outline_layer:
            glyph_layer.alpha_composite(outline_layer)

    fill_layer = _colored_mask_image(fill_mask, fill_color)
    if fill_layer:
        glyph_layer.alpha_composite(fill_layer)

    image.alpha_composite(glyph_layer, (bbox_left, bbox_top))

def _render_pic_page(task):
    conf = task['conf']
    bg_color = conf.get('color_b', (0, 0, 0, 0))
    img = Image.new('RGBA', (conf['img_w'], conf['img_h']), bg_color)
    context = _get_font_render_context(conf['font_spec'], conf['fsize'])
    font = context['font']
    glyph_metrics_cache = context['glyph_metrics_cache']

    for slot_index, _trail, char in task['entries']:
        col = slot_index % conf['count']
        row = slot_index // conf['count']
        if row >= conf.get('rows', 9999):
            break
        px = conf['ix'] + col * (conf['cw'] + conf['iw'])
        py = conf['iy'] + row * (conf['ch'] + conf['ih'])
        _draw_glyph_to_cell(img, font, char, px, py, conf['cw'], conf['ch'], task['style'], conf, glyph_metrics_cache)

    fname = f"fnt_s{conf['fsize']}_n{task['seq']}.{conf['format']}"
    save_path = os.path.join(task['folder'], fname)
    img.save(save_path, conf['format'])
    return save_path


def gen_pic(conf, log_signal, prog_signal):
    conf = dict(conf)
    conf['font_spec'] = resolve_font_spec(conf['font'])
    conf['font'] = str(conf['font_spec'].get('path') or '')
    conf = _normalize_pic_conf(conf)

    if not os.path.exists(conf['font']):
        log_signal("❌ 字体文件不存在！")
        return None

    log_signal(f"🎌 开始生成图片字库 ({conf['format']})...")
    preset = _get_pic_preset(conf)
    os.makedirs(conf['folder'], exist_ok=True)

    page_map = _build_cp932_page_map(conf['add_char'])
    tasks = []
    for dirname in FONT_STYLE_DIRS:
        style_dir = os.path.join(conf['folder'], dirname)
        os.makedirs(style_dir, exist_ok=True)
        style = _detect_pic_style(dirname, conf)
        for seq, page in enumerate(page_map, start=1):
            tasks.append({
                'conf': conf,
                'folder': style_dir,
                'seq': seq,
                'entries': page['entries'],
                'style': style,
            })

    total_tasks = len(tasks)
    log_signal(f"🖼️ 将生成 {len(FONT_STYLE_DIRS)} 套样式，共 {total_tasks} 张图片")
    if preset:
        log_signal(
            f"   已应用字号预设: {conf.get('preset_size', conf['fsize'])} -> 绘制字号 {conf['fsize']} | 画布 {conf['img_w']}x{conf['img_h']} | 起始 ({conf['ix']},{conf['iy']}) | 格子 {conf['cw']}x{conf['ch']} | {conf['count']} 列 x {conf['rows']} 行"
        )
    log_signal(f"   CP932 页数: {len(page_map)} | 每行 {conf['count']} 字 | 单字 {conf['cw']}x{conf['ch']} | 线程 {conf['workers']}")

    completed = 0
    with ThreadPoolExecutor(max_workers=conf['workers']) as executor:
        futures = [executor.submit(_render_pic_page, task) for task in tasks]
        for future in as_completed(futures):
            completed += 1
            saved_path = future.result()
            prog_signal(int(completed * 100 / total_tasks))
            log_signal(f"[{completed}/{total_tasks}] 已生成: {saved_path}")

    prog_signal(100)
    log_signal("✅ 图片字库生成完成。")
    return None


def gen_tga(conf, log_signal, prog_signal):
    conf = dict(conf)
    conf['font_spec'] = resolve_font_spec(conf['font'])
    conf['font'] = str(conf['font_spec'].get('path') or '')
    if not os.path.exists(conf['font']): 
 
        log_signal("❌ 字体文件不存在！")
        return None
    log_signal("🚀 开始生成 TGA 引擎字库...")

    out_dir = os.path.join(conf['folder'], 'new')
    if not os.path.exists(out_dir): os.makedirs(out_dir)

    text_items = []
    for code in range(0x20, 0x7F): text_items.append((chr(code), code))

    fl = list(range(0x81, 0xA0)) + list(range(0xE0, 0xEB)) + list(range(0xFA, 0xFD))
    sl = list(range(0x40, 0x80)) + list(range(0x80, 0x100))
    for i in fl:
        for j in sl:
            code = i * 0x100 + j
            try:
                text_items.append(((code).to_bytes(2, 'big').decode('cp932'), code))
            except:
                pass

    img = Image.new('RGBA', (conf['img_w'], conf['img_h']))
    font = _create_pil_font(conf['font_spec'], conf['fsize'])
    draw = ImageDraw.Draw(img)

    px, py = 0, 0
    info_map = {}
    total = len(text_items)

    for idx, (char, code) in enumerate(text_items):
        if idx % 500 == 0: prog_signal(int((idx / total) * 100))

        bbox = font.getbbox(char)
        cw = bbox[2]
        ch = bbox[3]

        if px + cw > conf['img_w']:
            px = 0
            py += conf['ch'] + conf['ih']
            if py + conf['ch'] > conf['img_h']:
                log_signal("⚠️ 警告：图片空间不足，截断！")
                break

        draw.text((px, py), char, font=font, fill=(255, 255, 255))
        info_map[code] = {'box': (px, py, px + cw, py + ch), 'code': code}
        px += cw + conf['iw']

    tga_path = os.path.join(out_dir, f"{conf['dat']}.tga")
    img.save(tga_path)

    dat = bytearray()
    fname_b = conf['eng_name'].encode('cp932')
    fpath_b = conf['eng_path'].encode('cp932')
    dat.extend(struct.pack(f'<I{len(fname_b)}s', len(fname_b), fname_b))
    dat.extend(struct.pack('<II', conf['cw'], conf['ch']))
    dat.extend(struct.pack(f'<I{len(fpath_b)}s', len(fpath_b), fpath_b))
    dat.extend(struct.pack('<I', len(info_map)))

    for _, info in info_map.items():
        x0, y0, x1, y1 = info['box']
        dat.extend(struct.pack('<HBBIIIIII', info['code'], x1 - x0, 0x1E, x0, y0, x1, y1, 0xFFFFFFFF, 0))

    with open(os.path.join(out_dir, f"{conf['dat']}.txt"), 'wb') as f: f.write(dat)
    prog_signal(100)
    log_signal(f"✅ TGA 字库完成，索引: {conf['dat']}.txt")
    return None

def gen_bmp(conf, log_signal, prog_signal):
    conf = dict(conf)
    conf['font_spec'] = resolve_font_spec(conf['font'])
    conf['font'] = str(conf['font_spec'].get('path') or '')
    if not os.path.exists(conf['font']): 
 
        log_signal("❌ 字体文件不存在！")
        return None
    log_signal("🚀 开始生成 BMP 长图字库...")
    if not os.path.exists(conf['folder']): os.makedirs(conf['folder'])

    font = _create_pil_font(conf['font_spec'], conf['fsize'])
    fl, sl = _get_jp_chars()

    palette = []
    if conf['depth'] <= 8:
        grad = 256 // (2 ** conf['depth'])
        t = 0
        for i in range(2 ** conf['depth']):
            palette.extend([t, t, t]); t += grad

    text_buf = ""
    count = 0
    seq = 0
    page_limit = 16

    total_fl = len(fl)

    for idx, i in enumerate(fl):
        prog_signal(int((idx / total_fl) * 100))
        for j in sl:
            try:
                text_buf += (i * 0x100 + j).to_bytes(2, 'big').decode('cp932')
            except:
                text_buf += '　'

        count += 1
        if count == page_limit or i == fl[-1]:
            h = count * conf['ch'] * 12
            if conf['depth'] <= 8:
                img = Image.new('P', (conf['img_w'], h))
                img.putpalette(palette)
            else:
                img = Image.new('RGBA', (conf['img_w'], h))

            draw = ImageDraw.Draw(img)
            start = 0
            py = 0
            while start < len(text_buf):
                line = text_buf[start: start + conf['count']]
                px = 0
                for ch in line:
                    draw.text((px, py), ch, font=font, fill=(255, 255, 255))
                    px += conf['cw']
                py += conf['ch']
                start += conf['count']

            if conf['scale'] != 1.0:
                img = img.resize((int(img.width * conf['scale']), int(img.height * conf['scale'])), Image.Resampling.BICUBIC)

            fname = f"ff_0{seq}l.bmp"
            img.save(os.path.join(conf['folder'], fname))
            log_signal(f"   -> 已输出: {fname}")

            seq += 1
            text_buf = ""
            count = 0

    prog_signal(100)
    log_signal("✅ BMP 长图字库生成完成。")
    return None

def gen_bmfont(conf, log_signal, prog_signal):
    font_spec = resolve_font_spec(conf['font_path'])
    font_path = str(font_spec.get('path') or '')

    chars = conf['chars']
    tex_size = conf['tex_size']
    font_size = conf['font_size']
    out_fnt = conf['out_fnt']
    out_png = os.path.splitext(out_fnt)[0] + ".png"
    
    if not os.path.exists(font_path):
            log_signal("❌ 字体文件不存在")
            return None

    log_signal(f"🚀 <b>开始生成 BMFont...</b>")
    log_signal(f"   画布尺寸: {tex_size}x{tex_size} | 字号: {font_size}")
    log_signal(f"   字符总数: {len(chars)}")
    prog_signal(5)
    
    try:
        pil_font = _create_pil_font(font_spec, font_size)
        metrics = [] 
        log_signal("📏 正在测量字形...")
        
        current_x = 0
        current_y = 0
        row_h = 0
        padding = 2 
        
        packed_glyphs = []
        img_map = {} 
        
        ascent, descent = pil_font.getmetrics()
        line_height = ascent + descent
        
        count = 0 
        total_chars = len(chars)
        
        for char in chars:
            adv = pil_font.getlength(char)
            bbox = pil_font.getbbox(char)
            
            if bbox:
                w = bbox[2] - bbox[0]
                h = bbox[3] - bbox[1]
                cw, ch = font_size * 2, font_size * 2
                tmp_img = Image.new('RGBA', (cw, ch), (0,0,0,0))
                draw = ImageDraw.Draw(tmp_img)
                draw.text((0,0), char, font=pil_font, fill=(255,255,255))
                
                crop_box = tmp_img.getbbox()
                if crop_box:
                        glyph_img = tmp_img.crop(crop_box)
                        w, h = glyph_img.size
                        xoff = crop_box[0]
                        yoff = crop_box[1]
                else:
                        glyph_img = None
                        w, h = 0, 0
                        xoff, yoff = 0, 0
            else:
                glyph_img = None
                w, h = 0, 0
                xoff, yoff = 0, 0
                
            img_map[char] = glyph_img

            if current_x + w + padding > tex_size:
                current_x = 0
                current_y += row_h + padding
                row_h = 0
            
            if current_y + h + padding > tex_size:
                log_signal("❌ 画布过小，无法容纳所有字符！请增大画布尺寸。")
                return None

            packed_glyphs.append({
                "id": ord(char),
                "char": char,
                "x": current_x,
                "y": current_y,
                "width": w,
                "height": h,
                "xoffset": xoff,
                "yoffset": yoff,
                "xadvance": int(adv),
                "chnl": 15
            })

            current_x += w + padding
            row_h = max(row_h, h)
            
            count += 1
            if count % 200 == 0:
                prog_signal(int(5 + 80 * count / total_chars))
        
        log_signal("🎨 正在绘制纹理...")
        atlas = Image.new('RGBA', (tex_size, tex_size), (0,0,0,0))
        for g in packed_glyphs:
            char = g['char']
            if img_map[char]:
                atlas.paste(img_map[char], (g['x'], g['y']))
        
        log_signal(f"💾 保存纹理: {out_png}")
        atlas.save(out_png)
        
        log_signal(f"📝 生成描述文件: {out_fnt}")
        
        lines = []
        lines.append(f'info face="{os.path.basename(font_path)}" size={font_size} bold=0 italic=0 charset="" unicode=1 stretchH=100 smooth=1 aa=1 padding=0,0,0,0 spacing=1,1 outline=0')
        lines.append(f'common lineHeight={line_height} base={ascent} scaleW={tex_size} scaleH={tex_size} pages=1 packed=0 alphaChnl=1 redChnl=0 greenChnl=0 blueChnl=0')
        lines.append(f'page id=0 file="{os.path.basename(out_png)}"')
        lines.append(f'chars count={len(packed_glyphs)}')
        
        for g in packed_glyphs:
            line = f'char id={g["id"]} x={g["x"]} y={g["y"]} width={g["width"]} height={g["height"]} xoffset={g["xoffset"]} yoffset={g["yoffset"]} xadvance={g["xadvance"]} page=0 chnl=15'
            lines.append(line)
        
        with open(out_fnt, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        prog_signal(100)
        log_signal(f"✅ <b>BMFont 生成完毕!</b>")
        return out_fnt

    except Exception as e:
        log_signal(f"❌ 生成失败: {e}")
        traceback.print_exc()
        return None