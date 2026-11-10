"""DOM 取证：通过 CDP 提取外部可见的设计 token、元素坐标与调色板。

只读取访客可见的计算样式与几何信息，不读取脚本逻辑或源码，符合洁净室原则。
"""
import json

INSPECT_JS = r"""
(() => {
  const out = {
    url: location.href,
    viewport: { width: window.innerWidth, height: window.innerHeight },
    tokens: {}, elements: [], palette: []
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
      box: {
        x: Math.round(rect.x), y: Math.round(rect.y),
        width: Math.round(rect.width), height: Math.round(rect.height)
      },
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
  return out;
})()
"""


def inspect_page(cdp, url=None, wait=1.5):
    """在已连接的 CDP 会话上执行取证；可先导航到 url。"""
    if url:
        cdp.navigate(url, wait=wait)
    data = cdp.evaluate(INSPECT_JS)
    if not isinstance(data, dict) or "tokens" not in data:
        raise RuntimeError("取证返回结构异常")
    return data


def write_report(data, out_path):
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return out_path
