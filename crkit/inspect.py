"""DOM 取证：通过 CDP 提取外部可见的设计 token、元素坐标与调色板。

只读取访客可见的计算样式与几何信息，不读取脚本逻辑或源码，符合洁净室原则。
许可证：PolyForm Noncommercial License 1.0.0。
Copyright (c) 2026 洋洋。
"""
import json

from . import colors

INSPECT_JS = r"""
(() => {
  const sy = window.scrollY || 0;
  const boxOf = (rect) => ({
    x: Math.round(rect.x), y: Math.round(rect.y + sy),
    width: Math.round(rect.width), height: Math.round(rect.height)
  });
  const out = {
    url: location.href,
    viewport: { width: window.innerWidth, height: window.innerHeight },
    tokens: {}, elements: [], palette: [],
    links: [], images: [], headings: [], a11y: {}, design: {}, text: ""
  };
  const body = getComputedStyle(document.body);
  out.tokens.body = {
    backgroundColor: body.backgroundColor,
    color: body.color,
    fontFamily: body.fontFamily,
    fontSize: body.fontSize,
    fontWeight: body.fontWeight,
    lineHeight: body.lineHeight
  };
  const selectors = ['h1','h2','h3','h4','p','a','button','input','img','ul','ol','section','header','footer','nav','main'];
  const seen = new Set();
  for (const el of document.querySelectorAll(selectors.join(','))) {
    if (seen.has(el)) continue;
    seen.add(el);
    const rect = el.getBoundingClientRect();
    if (rect.width === 0 && rect.height === 0) continue;
    const cs = getComputedStyle(el);
    out.elements.push({
      tag: el.tagName.toLowerCase(),
      id: el.id || null,
      className: (typeof el.className === 'string' && el.className) ? el.className : null,
      text: (el.textContent || '').trim().slice(0, 80),
      box: boxOf(rect),
      style: {
        color: cs.color,
        backgroundColor: cs.backgroundColor,
        fontSize: cs.fontSize,
        fontWeight: cs.fontWeight,
        fontFamily: cs.fontFamily
      }
    });
  }
  const colors = new Set();
  for (const el of document.querySelectorAll('*')) {
    const cs = getComputedStyle(el);
    colors.add(cs.color);
    colors.add(cs.backgroundColor);
  }
  out.palette = [...colors].filter(c => c && c !== 'rgba(0, 0, 0, 0)' && c !== 'transparent').slice(0, 24);

  out.links = [...document.querySelectorAll('a')].map(a => ({
    text: (a.textContent || '').trim().slice(0, 80),
    href: a.getAttribute('href'),
    target: a.target || null
  }));

  out.images = [...document.querySelectorAll('img')].map(img => ({
    alt: img.alt || null,
    naturalWidth: img.naturalWidth,
    naturalHeight: img.naturalHeight,
    box: boxOf(img.getBoundingClientRect())
  })).filter(i => i.naturalWidth || i.box.width || i.box.height);

  out.headings = [...document.querySelectorAll('h1,h2,h3,h4,h5,h6')].map(h => ({
    level: parseInt(h.tagName[1], 10),
    text: (h.textContent || '').trim().slice(0, 80),
    box: boxOf(h.getBoundingClientRect())
  }));

  const landmarkTags = [...document.querySelectorAll('header,nav,main,footer,aside,section')]
    .map(el => el.tagName.toLowerCase());
  const unnamed = [...document.querySelectorAll('button,a')]
    .filter(el => !(el.textContent || '').trim() && !el.getAttribute('aria-label') && !el.title)
    .map(el => el.tagName.toLowerCase());
  out.a11y = {
    lang: document.documentElement.lang || null,
    images_without_alt: out.images.filter(i => !i.alt).length,
    landmarks: [...new Set(landmarkTags)],
    unnamed_controls: unnamed
  };

  const sets = {
    font_sizes: new Set(), font_weights: new Set(), fonts: new Set(),
    max_widths: new Set(), radii: new Set(), shadows: new Set(), spacing: new Set()
  };
  for (const el of document.querySelectorAll('*')) {
    const cs = getComputedStyle(el);
    if (cs.fontSize) sets.font_sizes.add(cs.fontSize);
    if (cs.fontWeight) sets.font_weights.add(cs.fontWeight);
    if (cs.fontFamily) sets.fonts.add(cs.fontFamily.split(',')[0].replace(/['"]/g, ''));
    if (cs.maxWidth && cs.maxWidth !== 'none') sets.max_widths.add(cs.maxWidth);
    if (cs.borderRadius && cs.borderRadius !== '0px') sets.radii.add(cs.borderRadius);
    if (cs.boxShadow && cs.boxShadow !== 'none') sets.shadows.add(cs.boxShadow);
    for (const prop of ['margin', 'marginTop', 'marginBottom', 'padding', 'paddingTop', 'paddingBottom']) {
      const v = cs[prop];
      if (v && v !== '0px' && v !== '0px 0px') sets.spacing.add(v);
    }
  }
  out.design = Object.fromEntries(
    Object.entries(sets).map(([k, v]) => [k, [...v].slice(0, 20)])
  );

  out.text = (document.body.innerText || '').replace(/\s+/g, ' ').trim();
  return out;
})()
"""


def _normalize_style(style):
    if not isinstance(style, dict):
        return style
    for key in ("color", "backgroundColor"):
        if style.get(key):
            style[key] = colors.parse_color(style[key])
    return style


def inspect_page(cdp, url=None, wait=1.5, timeout=15, full_page=False, max_text=4000):
    """在已连接的 CDP 会话上执行取证；可先导航到 url。"""
    if url:
        cdp.navigate(url, wait=wait, timeout=timeout)
    data = cdp.evaluate(INSPECT_JS)
    if not isinstance(data, dict) or "tokens" not in data:
        raise RuntimeError("取证返回结构异常")
    data["palette"] = colors.normalize_palette(data.get("palette", []))
    for el in data.get("elements", []):
        _normalize_style(el.get("style"))
    if "text" in data:
        data["text"] = str(data["text"])[:max_text]
    data["full_page"] = full_page
    return data


def write_report(data, out_path):
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return out_path


def write_plaintext(data, out_path):
    """把标题大纲与可见纯文本另存为 .txt，便于人工通读。"""
    lines = []
    for h in data.get("headings", []):
        level = h.get("level", 1)
        lines.append(f"{'#' * min(max(level, 1), 6)} {h.get('text', '')}")
    text = data.get("text", "")
    if text:
        lines.append(text)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return out_path
