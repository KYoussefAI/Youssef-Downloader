"""Generate ISSA logo and multi-resolution Windows icon from vector geometry."""
from pathlib import Path
from PIL import Image, ImageDraw
ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
ASSETS.mkdir(exist_ok=True)
SIZE = 512
im = Image.new("RGBA", (SIZE, SIZE), (0,0,0,0))
d = ImageDraw.Draw(im)
d.rounded_rectangle((16,16,496,496),radius=116,fill=(19,25,45,255))
# Distinctive stylized triangular media symbol in the ISSA violet-to-cyan palette.
d.line([(160,118),(370,256),(160,394),(160,118)],fill=(142,103,255),width=54,joint="curve")
d.line([(203,215),(274,256),(203,298)],fill=(87,204,255),width=40,joint="curve")
d.ellipse((150,105,194,149), fill=(142,103,255))
d.ellipse((150,372,194,416), fill=(142,103,255))
im.save(ASSETS/"issa-logo.png")
im.save(ASSETS/"issa.ico",format="ICO",sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
print("Generated",ASSETS/"issa.ico")
