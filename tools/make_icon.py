"""离线绘制 VirtualCom 的二次元风格图标，不依赖任何云端生成。"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
S = 4
BASE = 256


def px(v: float) -> int:
    return int(round(v * S))


def box(values: tuple[float, float, float, float]) -> tuple[int, int, int, int]:
    return tuple(px(v) for v in values)  # type: ignore[return-value]


def pts(values) -> list[tuple[int, int]]:
    return [(px(x), px(y)) for x, y in values]


def poly(draw: ImageDraw.ImageDraw, values, **kwargs):
    draw.polygon(pts(values), **kwargs)


def seg(draw: ImageDraw.ImageDraw, values, **kwargs):
    draw.line(pts(values), **kwargs)


def rounded(draw: ImageDraw.ImageDraw, xy, radius, **kwargs):
    draw.rounded_rectangle(
        [int(v * S) if isinstance(v, (int, float)) else v for v in xy],
        radius=px(radius),
        **kwargs,
    )


def build() -> Image.Image:
    size = BASE * S
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))

    # 圆角底板 + 柔和渐变
    grad = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    gd = ImageDraw.Draw(grad)
    top = (25, 35, 74)
    bottom = (13, 19, 47)
    for y in range(size):
        t = y / max(size - 1, 1)
        c = tuple(int(top[i] * (1 - t) + bottom[i] * t) for i in range(3))
        gd.line([(0, y), (size, y)], fill=c + (255,))
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle(box((6, 6, 250, 250)), radius=42, fill=255)
    img.paste(grad, (0, 0), mask)

    d = ImageDraw.Draw(img)

    # 双描边：薄荷青 + 樱粉，轻小说封面感
    d.rounded_rectangle(box((13, 13, 243, 243)), radius=36, outline=(126, 221, 205, 235), width=px(2))
    d.rounded_rectangle(box((19, 19, 237, 237)), radius=31, outline=(238, 166, 190, 145), width=px(1.4))

    # 角落小装饰
    for x, y, r, col in [
        (41, 48, 3, (246, 214, 153, 210)),
        (215, 62, 2.5, (138, 226, 210, 220)),
        (207, 207, 3, (240, 170, 194, 190)),
        (52, 203, 2, (246, 214, 153, 170)),
    ]:
        d.ellipse(box((x - r, y - r, x + r, y + r)), fill=col)

    # 头发：后层先铺，脸画好后再盖刘海，保证小尺寸也看得出发型
    hair_dark = (57, 44, 70, 255)
    hair = (91, 66, 89, 255)
    hair_light = (117, 87, 109, 255)
    d.ellipse(box((69, 43, 187, 178)), fill=hair_dark)
    poly(d, [(70, 108), (58, 176), (82, 205), (101, 150)], fill=hair_dark)
    poly(d, [(186, 106), (198, 176), (176, 205), (156, 150)], fill=hair_dark)

    # 脸
    skin = (248, 222, 203, 255)
    d.ellipse(box((84, 68, 172, 153)), fill=skin)
    d.ellipse(box((80, 105, 95, 129)), fill=skin)
    d.ellipse(box((161, 105, 176, 129)), fill=skin)

    # 刘海：偏分 + 三段式发梢
    poly(d, [(80, 112), (84, 68), (127, 49), (170, 68), (176, 112),
               (159, 103), (151, 115), (137, 101), (127, 112), (113, 97),
               (101, 113), (90, 101)], fill=hair)
    poly(d, [(84, 74), (112, 54), (133, 52), (113, 98), (97, 104)], fill=hair_light)
    poly(d, [(150, 58), (171, 73), (176, 110), (160, 102)], fill=(74, 55, 76, 255))
    # 两侧长发
    poly(d, [(78, 98), (90, 112), (83, 170), (70, 190)], fill=hair)
    poly(d, [(178, 98), (166, 112), (173, 170), (186, 190)], fill=hair)
    seg(d, [(88, 118), (80, 162)], fill=hair_light, width=px(3))

    # 眼睛：温和的半垂眼
    line = (49, 42, 61, 255)
    seg(d, [(101, 122), (112, 126), (124, 121)], fill=line, width=px(3.4), joint="curve")
    seg(d, [(134, 121), (146, 126), (157, 122)], fill=line, width=px(3.4), joint="curve")
    d.ellipse(box((108, 118, 117, 127)), fill=(61, 82, 118, 255))
    d.ellipse(box((141, 118, 150, 127)), fill=(61, 82, 118, 255))
    d.ellipse(box((111, 120, 114, 123)), fill=(246, 250, 255, 255))
    d.ellipse(box((144, 120, 147, 123)), fill=(246, 250, 255, 255))
    # 鼻与浅笑
    seg(d, [(129, 129), (127, 134)], fill=(184, 128, 122, 190), width=px(1.6))
    d.arc(box((120, 135, 138, 145)), start=12, end=168, fill=(171, 103, 110, 235), width=px(2.2))
    blush = (238, 154, 165, 120)
    d.ellipse(box((93, 133, 108, 139)), fill=blush)
    d.ellipse(box((150, 133, 165, 139)), fill=blush)

    # 衣服：白衬衫 + 深色领子 + 薄荷领结
    poly(d, [(104, 151), (128, 164), (152, 151), (169, 166), (184, 210), (72, 210), (87, 166)], fill=(242, 241, 238, 255))
    poly(d, [(104, 151), (128, 167), (110, 180), (91, 163)], fill=(33, 45, 84, 255))
    poly(d, [(152, 151), (128, 167), (146, 180), (165, 163)], fill=(33, 45, 84, 255))
    poly(d, [(122, 165), (134, 165), (139, 183), (128, 190), (117, 183)], fill=(122, 218, 201, 255))
    d.ellipse(box((124, 178, 132, 186)), fill=(79, 184, 173, 255))

    # 手里的串口水晶：DB9 轮廓简化为小插头
    glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    gg = ImageDraw.Draw(glow)
    rounded(gg, (142, 185, 193, 222), 9, fill=(91, 212, 205, 90))
    glow = glow.filter(ImageFilter.GaussianBlur(px(7)))
    img.alpha_composite(glow)
    d = ImageDraw.Draw(img)
    rounded(d, (145, 187, 190, 220), 8, fill=(36, 61, 91, 255), outline=(142, 230, 216, 255), width=px(2))
    seg(d, [(153, 196), (153, 212)], fill=(167, 238, 226, 255), width=px(3))
    seg(d, [(163, 196), (163, 212)], fill=(167, 238, 226, 255), width=px(3))
    seg(d, [(173, 196), (173, 212)], fill=(167, 238, 226, 255), width=px(3))
    seg(d, [(182, 200), (182, 208)], fill=(238, 171, 194, 230), width=px(2.4))

    # 衣袖边与高光
    seg(d, [(74, 206), (72, 214)], fill=(196, 214, 231, 200), width=px(2))
    seg(d, [(184, 206), (186, 214)], fill=(196, 214, 231, 200), width=px(2))

    return img.resize((BASE, BASE), Image.Resampling.LANCZOS)


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    img = build()
    png_path = ASSETS / "logo.png"
    ico_path = ASSETS / "app.ico"
    img.save(png_path)
    img.save(
        ico_path,
        format="ICO",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    print(f"generated: {png_path}")
    print(f"generated: {ico_path}")


if __name__ == "__main__":
    main()
