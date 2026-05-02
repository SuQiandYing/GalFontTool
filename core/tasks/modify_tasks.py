import os
import traceback
from fontTools.ttLib import TTFont
from core.utils import ensure_ttf
from core.history_manager import get_history_manager
from core.system_fonts import resolve_font_spec


def _open_ttfont(font_value):
    font_spec = resolve_font_spec(font_value)
    font_path = str(font_spec.get('path') or '')
    font_number = int(font_spec.get('font_number', 0) or 0)
    if os.path.splitext(font_path)[1].lower() == '.ttc':
        return TTFont(font_path, fontNumber=font_number)
    return TTFont(font_path)


def tweak_font_width(conf, log_signal, prog_signal):
    from fontTools.ttLib.tables._g_l_y_f import GlyphCoordinates
    
    src = conf['src']
    scale = conf['scale']
    dx = conf['dx']
    out_name = conf['out_name']

    if not os.path.exists(src):
        log_signal("❌ 源字体不存在")
        return None

    if scale == 1.0 and abs(dx) < 10:
        log_signal(f"⚠️ <b>提醒：您的间距调整值 ({dx}) 太小了！</b>")
        log_signal(f"   字体单位通常为 1000~2048。")
        log_signal(f"   想要肉眼可见的变化，建议尝试 <b>50, 100, -50</b> 这种数值。")

    log_signal(f"📏 <b>开始调整字宽...</b>")
    log_signal(f"   几何缩放: {scale:.2f} | 间距修正: {dx}")
    prog_signal(5)

    try:
        font = _open_ttfont(src)
        ensure_ttf(font, log_signal, "目标字体")
        
        if 'glyf' not in font or 'hmtx' not in font:
            log_signal("❌ 字体格式异常，未找到glyf或hmtx表")
            return None

        glyf = font['glyf']
        hmtx = font['hmtx']
        metrics = hmtx.metrics
        glyph_order = font.getGlyphOrder()
        
        total = len(glyph_order)
        processed = 0

        log_signal("🔨 正在重塑字形...")

        scale_t = (scale, 1.0)

        for name in glyph_order:
            if name in glyf:
                g = glyf[name]
                modified = False
                
                if g.isComposite():
                    for comp in g.components:
                        comp.x = int(comp.x * scale)
                    modified = True
                elif g.numberOfContours > 0:
                    if hasattr(g, 'coordinates'):
                        g.coordinates.scale(scale_t)
                        g.coordinates.toInt()
                        modified = True
                
                if modified:
                    if hasattr(g, 'xMin'): g.xMin = int(g.xMin * scale)
                    if hasattr(g, 'xMax'): g.xMax = int(g.xMax * scale)

            if name in metrics:
                old_w, old_lsb = metrics[name]
                new_w = int(old_w * scale) + dx
                new_lsb = int(old_lsb * scale)
                metrics[name] = (max(0, new_w), new_lsb)

            processed += 1
            if processed % 2000 == 0:
                prog_signal(5 + int(90 * processed / total))

        log_signal("🔄 修正全局 Head 表...")
        head = font['head']
        head.xMin = int(head.xMin * scale)
        head.xMax = int(head.xMax * scale)

        prog_signal(95)
        log_signal("💾 正在保存...")
        
        for record in font['name'].names:
            if record.nameID in [1, 4]:
                try:
                    s = record.toUnicode()
                    record.string = (s + " Condensed").encode('utf-16-be')
                except: pass

        save_path = os.path.join(os.path.dirname(src), out_name)
        
        history = get_history_manager()
        file_existed = os.path.exists(save_path)
        if file_existed:
            history.record_before_overwrite("调整字宽", save_path, f"缩放{scale:.2f} 间距{dx:+}")
        
        font.save(save_path)
        if not file_existed and os.path.exists(save_path):
            history.record_new_file("调整字宽", save_path, f"缩放{scale:.2f} 间距{dx:+}")
        elif os.path.exists(save_path):
            history.record("调整字宽", save_path, f"缩放{scale:.2f} 间距{dx:+}")
        
        prog_signal(100)
        log_signal(f"✅ <b>调整完成！</b>")
        log_signal(f"   已输出: {out_name}")
        return save_path

    except Exception as e:
        log_signal(f"❌ 调整失败: {e}")
        traceback.print_exc()
        return None


def clean_font_tables(conf, log_signal, prog_signal):
    src = conf['src']
    out_path = conf['out_path']
    tables_to_remove = conf['tables'] 

    if not os.path.exists(src):
        log_signal("❌ 源字体不存在")
        return None

    log_signal(f"🧹 <b>开始清理字体表...</b>")
    log_signal(f"   目标: {os.path.basename(src)}")
    log_signal(f"   移除表: {', '.join(tables_to_remove)}")
    prog_signal(10)

    try:
        font = _open_ttfont(src)
        ensure_ttf(font, log_signal, "源字体") 
        
        removed_count = 0
        for tag in tables_to_remove:
            if tag in font:
                del font[tag]
                removed_count += 1
                log_signal(f"   - 已移除: {tag}")
        
        if removed_count == 0:
            log_signal("⚠️ 未发现选定的表，无需清理。")
        
        if 'NAME_DETAILED' in tables_to_remove:
            if 'name' in font:
                names = font['name'].names
                keep_ids = [1, 2, 3, 4, 5, 6]
                new_names = [r for r in names if r.nameID in keep_ids]
                font['name'].names = new_names
                log_signal("   - 已精简 Name 表 (仅保留基本信息)")

        if 'HINTING' in tables_to_remove:
            for hint_tag in ['fpgm', 'prep', 'cvt ', 'hdmx', 'VDMX', 'LTSH']:
                if hint_tag.strip() in font:
                    del font[hint_tag.strip()]
                    log_signal(f"   - 已移除提示表: {hint_tag}")
        
        prog_signal(80)
        log_signal("💾 正在保存...")
        
        history = get_history_manager()
        file_existed = os.path.exists(out_path)
        if file_existed:
            history.record_before_overwrite("清理字体表", out_path, f"移除{removed_count}个表")
        
        font.save(out_path)
        if not file_existed and os.path.exists(out_path):
            history.record_new_file("清理字体表", out_path, f"移除{removed_count}个表")
        elif os.path.exists(out_path):
            history.record("清理字体表", out_path, f"移除{removed_count}个表")
        
        prog_signal(100)
        log_signal(f"✅ <b>清理完成!</b>")
        log_signal(f"   输出: {out_path}")
        return out_path

    except Exception as e:
        log_signal(f"❌ 清理失败: {e}")
        traceback.print_exc()
        return None


def gen_unified_fix(conf, log_signal, prog_signal):
    from fontTools.ttLib.tables._g_l_y_f import GlyphCoordinates
    
    src = conf['src']
    out_path = conf['out_path']
    sx = conf['scale_x']
    sy = conf['scale_y']
    spacing = conf['spacing']
    asc = conf['asc']
    desc = conf['desc']
    gap = conf['gap']

    if not os.path.exists(src):
        log_signal("❌ 源字体不存在")
        return None

    log_signal(f"🔧 <b>开始高级修复...</b>")
    log_signal(f"   变形: 宽 {sx:.2f}x | 高 {sy:.2f}x | 间距 {spacing:+}")
    log_signal(f"   度量: Asc {asc} | Desc {desc}")
    prog_signal(5)

    try:
        font = _open_ttfont(src)
        ensure_ttf(font, log_signal, "目标字体")
        
        glyf = font['glyf']
        hmtx = font['hmtx']
        metrics = hmtx.metrics
        scale_t = (sx, sy) 
        
        log_signal("🔨 正在重塑字形结构...")
        
        glyph_order = font.getGlyphOrder()
        total_g = len(glyph_order)
        
        for idx, name in enumerate(glyph_order):
            if name in glyf:
                g = glyf[name]
                if g.isComposite():
                    for comp in g.components:
                        comp.x = int(comp.x * sx)
                        comp.y = int(comp.y * sy)
                elif g.numberOfContours > 0:
                    if hasattr(g, 'coordinates'):
                        g.coordinates.scale(scale_t)
                        g.coordinates.toInt()
                
                if hasattr(g, 'xMin'): g.xMin = int(g.xMin * sx)
                if hasattr(g, 'yMin'): g.yMin = int(g.yMin * sy)
                if hasattr(g, 'xMax'): g.xMax = int(g.xMax * sx)
                if hasattr(g, 'yMax'): g.yMax = int(g.yMax * sy)

            if name in metrics:
                old_w, old_lsb = metrics[name]
                new_w = int(old_w * sx) + spacing
                new_lsb = int(old_lsb * sx)
                metrics[name] = (max(0, new_w), new_lsb)
            
            if idx % 1000 == 0:
                prog_signal(5 + int(50 * idx / total_g))

        head = font['head']
        head.xMin = int(head.xMin * sx)
        head.yMin = int(head.yMin * sy)
        head.xMax = int(head.xMax * sx)
        head.yMax = int(head.yMax * sy)

        prog_signal(60)

        log_signal("📏 写入垂直度量 (行高)...")
        if 'hhea' in font:
            font['hhea'].ascent = asc
            font['hhea'].descent = desc
            font['hhea'].lineGap = gap
        
        if 'OS/2' in font:
            font['OS/2'].sTypoAscender = asc
            font['OS/2'].sTypoDescender = desc
            font['OS/2'].sTypoLineGap = gap
            font['OS/2'].usWinAscent = asc
            font['OS/2'].usWinDescent = abs(desc)

        for tag in ['EBDT', 'EBLC', 'EBSC', 'CBDT', 'CBLC', 'VDMX', 'hdmx']:
            if tag in font: del font[tag]

        history = get_history_manager()
        file_existed = os.path.exists(out_path)
        if file_existed:
            history.record_before_overwrite("度量修复", out_path, f"Asc{asc} Desc{desc}")
        
        font.save(out_path)
        if not file_existed and os.path.exists(out_path):
            history.record_new_file("度量修复", out_path, f"Asc{asc} Desc{desc}")
        elif os.path.exists(out_path):
            history.record("度量修复", out_path, f"Asc{asc} Desc{desc}")
        
        prog_signal(100)
        log_signal(f"✅ <b>处理完成!</b> 已输出: {os.path.basename(out_path)}")
        return out_path

    except Exception as e:
        log_signal(f"❌ 修复失败: {e}")
        traceback.print_exc()
        return None