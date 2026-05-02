import os
import json
import glob
import traceback
from fontTools.ttLib import TTFont
from fontTools import subset
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib.tables._g_l_y_f import GlyphCoordinates
from core.utils import ensure_ttf
from core.history_manager import get_history_manager
from core.system_fonts import resolve_font_path, resolve_font_spec
from core.opencc_overrides import OPENCC_T2S_OVERRIDE, OPENCC_S2T_OVERRIDE



SUPPORTED_BUILD_EXTENSIONS = ('.ttf', '.woff', '.woff2')
SUPPORTED_WEB_EXTENSIONS = ('.ttf', '.otf', '.woff', '.woff2')
TEXT_READ_ENCODINGS = ['utf-8', 'utf-8-sig', 'cp932', 'gbk', 'utf-16']



def _normalize_output_name(file_name, default_ext, allowed_exts):
    lower_name = file_name.lower()
    for ext in allowed_exts:
        if lower_name.endswith(ext):
            return file_name, ext
    return f"{file_name}{default_ext}", default_ext


def _save_font_with_extension(font, out_path, ext):
    font.flavor = None if ext in ('.ttf', '.otf') else ext.lstrip('.')
    font.save(out_path)


def _collect_unicode_cmap(font):
    preferred = font.getBestCmap()
    if preferred:
        return dict(preferred)
    merged = {}
    if 'cmap' not in font:
        return merged
    for table in font['cmap'].tables:
        if getattr(table, 'isUnicode', lambda: False)() and getattr(table, 'cmap', None):
            merged.update(table.cmap)
    return merged


def _read_text_file_auto(path):
    for enc in TEXT_READ_ENCODINGS:
        try:
            with open(path, 'r', encoding=enc) as f:
                return f.read(), enc
        except UnicodeDecodeError:
            continue
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        return f.read(), 'utf-8-replace'


def _open_ttfont_from_spec(font_spec: dict[str, object]) -> TTFont:
    font_path = str(font_spec.get('path') or '')
    font_number = int(font_spec.get('font_number', 0) or 0)
    if os.path.splitext(font_path)[1].lower() == '.ttc':
        return TTFont(font_path, fontNumber=font_number)
    return TTFont(font_path)


def build_font(conf, log_signal, prog_signal):

    src_spec = resolve_font_spec(conf['src'])
    fallback_spec = resolve_font_spec(conf.get('fallback', ''))
    src = str(src_spec.get('path') or '')
    fallback = str(fallback_spec.get('path') or '')


    json_path = conf['json']
    file_name = conf['file_name']
    internal_name = conf['internal_name']
    mode = conf['mode']
    output_dir = conf.get('output_dir', '')
    history = get_history_manager()

    if not os.path.exists(src):
        log_signal("❌ <font color='red'>错误：未找到源字体文件</font>")
        return None

    if mode not in [3, 4, 5] and not os.path.exists(json_path):
        log_signal("❌ <font color='red'>错误：未找到映射 JSON 文件</font>")
        return None

    out_name, out_ext = _normalize_output_name(file_name, '.ttf', SUPPORTED_BUILD_EXTENSIONS)


    mode_desc = {
        1: "日繁映射 (CN -> JP)", 2: "逆向映射 (JP -> CN)",
        3: "仅修改代码页标识", 4: "繁转简", 5: "简转繁"
        }.get(mode, "未知")

    src_label = str(src_spec.get('family') or os.path.basename(src))
    fallback_label = str(fallback_spec.get('family') or os.path.basename(fallback)) if fallback else ''

    log_signal(f"<b>🔨 开始字体处理...</b><br>模式: {mode_desc}<br>输入: {src_label}<br>输出: {out_name}")
    prog_signal(10)

    try:
        font = _open_ttfont_from_spec(src_spec)
        ensure_ttf(font, log_signal, "主字体")
    except Exception as e:
        log_signal(f"❌ 字体读取失败: {str(e)}")
        return None

    if mode in [1, 2] and fallback and os.path.exists(fallback):
        log_signal(f"🔧 检测到补全字体: {fallback_label or os.path.basename(fallback)}")
        try:
            fb_font = _open_ttfont_from_spec(fallback_spec)
            ensure_ttf(fb_font, log_signal, "补全字体")


            upm_main = font['head'].unitsPerEm
            upm_fb = fb_font['head'].unitsPerEm
            scale_factor = upm_main / upm_fb

            need_scale = abs(scale_factor - 1.0) > 0.01
            if need_scale:
                log_signal(f"⚖️ 检测到UPM差异 (主:{upm_main} vs 补:{upm_fb})，缩放倍率: {scale_factor:.2f}")

            target_chars_needed = set()
            with open(json_path, 'r', encoding='utf-8') as f:
                raw_json = json.load(f)
                if mode == 1:
                    target_chars_needed = set(raw_json.keys())
                elif mode == 2:
                    target_chars_needed = set(raw_json.values())

            main_cmap = _collect_unicode_cmap(font)
            fb_cmap = _collect_unicode_cmap(fb_font)
            injected_count = 0

            if 'glyf' not in font or 'glyf' not in fb_font:
                log_signal("⚠️ 补全警告：非 TrueType 格式，跳过。")
            else:
                fb_glyph_set = fb_font.getGlyphSet()
                fb_glyf_table = fb_font['glyf']
                glyph_order = list(font.getGlyphOrder())
                bmp_cmap_tables = []
                full_unicode_cmap_tables = []
                for table in font['cmap'].tables:
                    if not getattr(table, 'isUnicode', lambda: False)():
                        continue
                    if table.format == 12:
                        full_unicode_cmap_tables.append(table)
                    elif table.format in (4, 6):
                        bmp_cmap_tables.append(table)

                for char in target_chars_needed:
                    code = ord(char)
                    if code in main_cmap or code not in fb_cmap:
                        continue

                    try:
                        fb_glyph_name = fb_cmap[code]
                        recording_pen = DecomposingRecordingPen(fb_glyph_set)
                        fb_glyph_set[fb_glyph_name].draw(recording_pen)
                        pen = TTGlyphPen(fb_glyph_set)
                        recording_pen.replay(pen)
                        new_glyph = pen.glyph()

                        if need_scale:
                            if hasattr(new_glyph, 'coordinates') and new_glyph.coordinates is not None and len(new_glyph.coordinates) > 0:
                                coords = new_glyph.coordinates
                                new_glyph.coordinates = GlyphCoordinates([(int(x * scale_factor), int(y * scale_factor)) for x, y in coords])
                            new_glyph.recalcBounds(fb_glyf_table)
                            width, lsb = fb_font['hmtx'][fb_glyph_name]
                            width = int(width * scale_factor)
                            lsb = int(lsb * scale_factor)
                        else:
                            new_glyph.recalcBounds(fb_glyf_table)
                            width, lsb = fb_font['hmtx'][fb_glyph_name]

                        new_glyph_name = f"uni{code:04X}_fb" if code <= 0xFFFF else f"u{code:X}_fb"
                        if new_glyph_name not in glyph_order:
                            glyph_order.append(new_glyph_name)
                        font['glyf'][new_glyph_name] = new_glyph
                        if hasattr(font['hmtx'], 'metrics'):
                            font['hmtx'].metrics[new_glyph_name] = (width, lsb)
                        else:
                            font['hmtx'][new_glyph_name] = (width, lsb)

                        if 'vmtx' in font:
                            v_height = font['head'].unitsPerEm
                            v_tsb = 0
                            if 'vmtx' in fb_font and fb_glyph_name in fb_font['vmtx'].metrics:
                                vh, tsb = fb_font['vmtx'].metrics[fb_glyph_name]
                                v_height = int(vh * scale_factor)
                                v_tsb = int(tsb * scale_factor)
                            if hasattr(font['vmtx'], 'metrics'):
                                font['vmtx'].metrics[new_glyph_name] = (v_height, v_tsb)
                            else:
                                font['vmtx'][new_glyph_name] = (v_height, v_tsb)

                        if code <= 0xFFFF:
                            for t in bmp_cmap_tables:
                                t.cmap[code] = new_glyph_name
                            for t in full_unicode_cmap_tables:
                                t.cmap[code] = new_glyph_name
                        else:
                            for t in full_unicode_cmap_tables:
                                t.cmap[code] = new_glyph_name

                        main_cmap[code] = new_glyph_name
                        injected_count += 1
                    except Exception as glyph_error:
                        log_signal(f"⚠️ 自动补全跳过 U+{code:04X} / {repr(char)}: {glyph_error}")

                font.setGlyphOrder(glyph_order)
                if 'maxp' in font:
                    font['maxp'].numGlyphs = len(glyph_order)

                log_signal(f"💉 <b>自动补全:</b> 注入 {injected_count} 个汉字 (已修正大小)")

        except Exception as e:
            log_signal(f"⚠️ 补全出错: {str(e)}")
            traceback.print_exc()

    ok_count = 0
    missing_list = []

    if mode == 3:
        log_signal("⏩ 伪装模式：跳过字符修改...")
        prog_signal(30)

    elif mode in [4, 5]:
        try:
            import opencc
        except ImportError:
            log_signal("❌ 未安装 OpenCC，请运行: pip install opencc-python-reimplemented")
            return None
        
        config_file = 't2s' if mode == 4 else 's2t'
        override_map = OPENCC_T2S_OVERRIDE if mode == 4 else OPENCC_S2T_OVERRIDE
        log_signal(f"🔄 字形转换 ({config_file})...")
        log_signal(f"   模式 4 = 繁体字显示为简体字形")
        log_signal(f"   模式 5 = 简体字显示为繁体字形")
        log_signal(f"   内置补充表: {len(override_map)} 条")
        try:
            cc = opencc.OpenCC(config_file)
            mapped_count = 0
            override_hit_count = 0
            cmap_tables = [t for t in font['cmap'].tables if getattr(t, 'isUnicode', lambda: False)()]
            merged_cmap = _collect_unicode_cmap(font)

            for table in cmap_tables:
                existing = list(table.cmap.keys())
                new_mappings = {}
                for code in existing:
                    try:
                        orig_char = chr(code)

                        if orig_char in override_map:
                            converted_char = override_map[orig_char]
                            override_hit_count += 1
                        else:
                            converted_char = cc.convert(orig_char)

                        if converted_char != orig_char and len(converted_char) == 1:
                            converted_code = ord(converted_char)
                            glyph_name = merged_cmap.get(converted_code)
                            if glyph_name is not None:
                                if table.format in (4, 6) and code > 0xFFFF:
                                    continue
                                new_mappings[code] = glyph_name
                                mapped_count += 1
                    except Exception:
                        pass
                table.cmap.update(new_mappings)
            ok_count = mapped_count
            if cmap_tables:
                ok_count //= len(cmap_tables)
            log_signal(f"   ✓ 已转换 {ok_count} 个字符映射")
            log_signal(f"   ✓ 命中补充表 {override_hit_count} 次")
        except Exception as e:
            log_signal(f"❌ OpenCC 失败: {e}")
            return None

    else:
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                raw = json.load(f)
                mapping = {v: k for k, v in raw.items()} if mode == 1 else raw
        except Exception as e:
            log_signal(f"❌ JSON 读取失败: {e}")
            return None

        prog_signal(30)
        log_signal("🔍 执行映射...")

        missing_set = set()
        mapping_applied = 0
        unicode_tables = [t for t in font['cmap'].tables if getattr(t, 'isUnicode', lambda: False)()]
        best_cmap = _collect_unicode_cmap(font)

        for target_char, source_char in mapping.items():
            if target_char == source_char:
                continue
            target_code, source_code = ord(target_char), ord(source_char)

            if source_code not in best_cmap:
                missing_set.add(source_char)
                continue

            glyph_name = best_cmap[source_code]
            applied = False
            for table in unicode_tables:
                if table.format in (4, 6) and target_code > 0xFFFF:
                    continue
                table.cmap[target_code] = glyph_name
                applied = True

            if applied:
                best_cmap[target_code] = glyph_name
                mapping_applied += 1
            else:
                missing_set.add(target_char)

        ok_count = mapping_applied
        missing_list = list(missing_set)

    prog_signal(60)
    log_signal("✏️ 修改元数据...")

    font['name'].names = [r for r in font['name'].names if r.nameID not in [1, 4, 6, 16, 17]]
    style = "Regular"
    full_name = f"{internal_name} {style}"
    ps_name = f"{internal_name}-{style}".replace(" ", "")

    for nameID, string in [(1, internal_name), (4, full_name), (6, ps_name)]:
        try:
            font['name'].setName(string, nameID, 3, 1, 1033)
        except:
            pass

        log_signal("💉 注入代码页伪装...")
    try:
        charset_val = conf.get('charset', '128')
        charset_map = {'128': 17, '134': 18, '136': 20, '1': 0, '129': 19}
        bit = charset_map.get(charset_val, 17)

        font['OS/2'].ulCodePageRange1 |= (1 << bit)
        font['OS/2'].ulCodePageRange1 |= (1 << 0)
        log_signal(f"   ✓ 已注入 Charset {charset_val} (Bit {bit})")
    except Exception as e:
        log_signal(f"   ⚠️ 注入失败: {e}")
        if hasattr(font, 'tables') and 'OS/2' in font.tables:
            del font.tables['OS/2']



    if output_dir and os.path.isdir(output_dir):
        out_path = os.path.join(output_dir, out_name)
    else:
        out_path = os.path.join(os.path.dirname(src), out_name)

    file_existed = os.path.exists(out_path)
    if file_existed:
        history.record_before_overwrite("生成字体", out_path, f"模式{mode}")


    try:
        _save_font_with_extension(font, out_path, out_ext)
        prog_signal(100)

        msg = f"<br><b style='color:#4CAF50'>✅ 成功: {out_path}</b><br>"
        if mode in [1, 2]:
            msg += f"&nbsp;&nbsp;-> 成功映射: {ok_count} 个<br>"
            msg += f"&nbsp;&nbsp;-> 缺失汉字: {len(missing_list)} 个<br>"

        if missing_list:
            msg += f"<br><b style='color:#FF9800'>⚠️ 严重警告：以下字符在补全字体中也未找到：</b><br>"
            msg += "".join(missing_list[:100])
            if len(missing_list) > 100:
                msg += f"... (共 {len(missing_list)} 个)"
            msg += "<br><span style='color:gray'>建议更换一个字符集更大的补全字体。</span><br>"

        log_signal(msg)
        
        if not file_existed and os.path.exists(out_path):
            history.record_new_file("生成字体", out_path, f"模式{mode}")
        
        return out_path
        
    except Exception as e:
        log_signal(f"❌ 保存失败: {e}")
        traceback.print_exc()
        return None


def subset_font(conf, log_signal, prog_signal):
    font_path = conf['font_path']
    txt_dir = conf.get('txt_dir', '')
    json_path = conf.get('json_path', '')
    out_path = conf['out_path']
    exts = conf.get('exts', '.txt;.json').split(';')
    history = get_history_manager()
    file_existed = os.path.exists(out_path)

    if not os.path.exists(font_path):
        log_signal("❌ 字体文件不存在！")
        return None

    log_signal(f"✂️ <b>开始精简字体...</b>")
    log_signal(f"   源字体: {os.path.basename(font_path)}")
    prog_signal(5)

    all_chars = set()

    if txt_dir and os.path.exists(txt_dir):
        all_files = []
        for ext in exts:
            ext = ext.strip()
            if not ext: continue
            if not ext.startswith('.'): ext = '.' + ext
            all_files.extend(glob.glob(os.path.join(txt_dir, '**', f'*{ext}'), recursive=True))
        
        log_signal(f"   扫描文本: {len(all_files)} 个文件")
        
        for fpath in all_files:
            try:
                content, used_enc = _read_text_file_auto(fpath)
                all_chars.update(content)
            except Exception as e:
                log_signal(f"⚠️ 读取文本失败 {os.path.basename(fpath)}: {e}")

    if json_path and os.path.exists(json_path):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                mapping = json.load(f)
                all_chars.update(mapping.keys())
                all_chars.update(mapping.values())
            log_signal(f"   映射表: {len(mapping)} 条")
        except Exception as e:
            log_signal(f"⚠️ 读取映射表失败: {e}")

    all_chars = {c for c in all_chars if c.isprintable() or c in ['\n', '\r', '\t']}
    log_signal(f"   需要保留: {len(all_chars)} 个字符")
    
    prog_signal(30)

    if not all_chars:
        log_signal("⚠️ 未找到任何字符，无法精简！")
        return None

    try:
        font = TTFont(font_path)
        ensure_ttf(font, log_signal, "源字体")
        
        options = subset.Options()
        options.name_IDs = ['*']
        options.name_legacy = True
        options.name_languages = ['*']
        options.glyph_names = True
        options.notdef_glyph = True
        options.notdef_outline = True
        options.recalc_bounds = True
        options.drop_tables = ['EBDT', 'EBLC', 'EBSC', 'CBDT', 'CBLC']
        
        prog_signal(50)
        
        subsetter = subset.Subsetter(options=options)
        subsetter.populate(text=''.join(all_chars))
        subsetter.subset(font)
        
        prog_signal(80)
        
        if file_existed:
            history.record_before_overwrite("精简字体", out_path, f"保留{len(all_chars)}字符")

        font.save(out_path)
        font.close()
        
        original_size = os.path.getsize(font_path) / 1024
        new_size = os.path.getsize(out_path) / 1024
        reduction = (1 - new_size / original_size) * 100
        
        if not file_existed and os.path.exists(out_path):
            history.record_new_file("精简字体", out_path, f"保留{len(all_chars)}字符")
        elif os.path.exists(out_path):
            history.record("精简字体", out_path, f"保留{len(all_chars)}字符")
        
        prog_signal(100)
        log_signal(f"✅ <b>精简完成！</b>")
        log_signal(f"   原始大小: {original_size:.1f} KB")
        log_signal(f"   精简后: {new_size:.1f} KB")
        log_signal(f"   体积减少: {reduction:.1f}%")
        log_signal(f"   输出: {out_path}")
        return out_path

    except Exception as e:
        log_signal(f"❌ 精简失败: {e}")
        traceback.print_exc()
        return None


def gen_woff2(conf, log_signal, prog_signal):
    src = conf['src']
    out_path = conf['out_path']
    history = get_history_manager()

    if not os.path.exists(src):
        log_signal("❌ 源字体不存在！")
        return None

    out_path, out_ext = _normalize_output_name(out_path, '.woff2', SUPPORTED_WEB_EXTENSIONS)
    file_existed = os.path.exists(out_path)
    target_label = out_ext.upper().lstrip('.')
    history_label = f"Web字体转换({target_label})"

    log_signal(f"🌐 <b>开始 Web 字体转换...</b>")
    log_signal(f"   源文件: {os.path.basename(src)}")
    log_signal(f"   目标格式: {target_label}")
    prog_signal(10)

    try:
        font = TTFont(src)
        ensure_ttf(font, log_signal, "源字体")
        
        prog_signal(50)
        
        if file_existed:
            history.record_before_overwrite(history_label, out_path, os.path.basename(src))
        
        _save_font_with_extension(font, out_path, out_ext)
        font.close()
        
        original_size = os.path.getsize(src) / 1024
        new_size = os.path.getsize(out_path) / 1024
        reduction = (1 - new_size / original_size) * 100 if original_size else 0
        
        if not file_existed and os.path.exists(out_path):
            history.record_new_file(history_label, out_path, os.path.basename(src))
        elif os.path.exists(out_path):
            history.record(history_label, out_path, os.path.basename(src))
        
        prog_signal(100)
        log_signal(f"✅ <b>{target_label} 转换完成！</b>")
        log_signal(f"   原始大小: {original_size:.1f} KB")
        log_signal(f"   {target_label}: {new_size:.1f} KB")
        log_signal(f"   体积变化: {reduction:.1f}%")
        log_signal(f"   输出: {out_path}")
        return out_path

    except Exception as e:
        log_signal(f"❌ 转换失败: {e}")
        traceback.print_exc()
        return None