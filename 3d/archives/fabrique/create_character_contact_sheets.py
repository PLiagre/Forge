"""Build deterministic character review sheets from Blender previews."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
PREVIEWS = ROOT / "AssetFactory/Workbench/Characters/Production/Previews"


def sheet(entries: list[tuple[str, str]], columns: int, output: str) -> None:
    width, height, label_height = 256, 320, 34
    rows = (len(entries) + columns - 1) // columns
    canvas = Image.new("RGB", (columns * width, rows * (height + label_height)), "#101820")
    draw = ImageDraw.Draw(canvas)
    font_path = Path("C:/Windows/Fonts/arial.ttf")
    font = ImageFont.truetype(font_path, 16) if font_path.is_file() else ImageFont.load_default(size=16)
    for index, (filename, label) in enumerate(entries):
        image = Image.open(PREVIEWS / filename).convert("RGB").resize((width, height), Image.Resampling.LANCZOS)
        x = index % columns * width
        y = index // columns * (height + label_height)
        canvas.paste(image, (x, y))
        bounds = draw.textbbox((0, 0), label, font=font)
        text_width = bounds[2] - bounds[0]
        draw.text((x + (width - text_width) / 2, y + height + 7), label, font=font, fill="#F0E5D1")
    canvas.save(PREVIEWS.parent / output, optimize=True)


def main() -> None:
    sheet([
        ("role_worker_male_adult_sturdy.png", "Ouvrier"),
        ("role_wealthy_female_adult_average.png", "Riche"),
        ("role_peasant_female_child_slender.png", "Paysan"),
        ("role_religious_male_elder_slender.png", "Religieux"),
        ("role_soldier_male_adult_sturdy.png", "Soldat"),
        ("role_noble_male_adult_tall.png", "Noble"),
        ("role_bourgeois_female_adult_average.png", "Bourgeois"),
        ("role_beggar_female_elder_slender.png", "Mendiant"),
    ], 4, "character_roles_review.png")
    sheet([
        ("body_male_child_average.png", "Masculin enfant"),
        ("body_female_child_average.png", "Féminin enfant"),
        ("body_male_adult_average.png", "Masculin adulte"),
        ("body_female_adult_average.png", "Féminin adulte"),
        ("body_male_elder_average.png", "Masculin âgé"),
        ("body_female_elder_average.png", "Féminin âgé"),
    ], 3, "character_bodies_review.png")
    print("CITYLAB_CHARACTER_SHEETS_OK roles=8 bodies=6")


if __name__ == "__main__":
    main()
