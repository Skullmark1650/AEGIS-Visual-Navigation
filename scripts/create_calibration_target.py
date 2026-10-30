"""Author a vector checkerboard using the bundled authoring runtime's ReportLab."""
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.units import mm


def main():
    output = Path("output/pdf/aegis-checkerboard-letter.pdf")
    output.parent.mkdir(parents=True, exist_ok=True)
    width, height = landscape(letter)
    document = canvas.Canvas(str(output), pagesize=(width, height))
    document.setTitle("AEGIS calibration target - 9 x 6 internal corners")
    document.setAuthor("AEGIS project")
    document.setFont("Helvetica-Bold", 15)
    document.drawCentredString(width/2, height-14*mm, "AEGIS CAMERA CALIBRATION TARGET")
    document.setFont("Helvetica", 10)
    document.drawCentredString(width/2, height-21*mm, "9 x 6 internal corners | 10 x 7 squares | nominal square side: 20 mm")
    side = 20*mm
    left, bottom = (width-10*side)/2, (height-7*side)/2
    for row in range(7):
        for column in range(10):
            if (row+column) % 2 == 0:
                document.rect(left+column*side, bottom+row*side, side, side, fill=1, stroke=0)
    document.setLineWidth(.2)
    document.rect(left, bottom, 10*side, 7*side, fill=0, stroke=1)
    document.setLineWidth(.7)
    ruler_left, ruler_y = (width-100*mm)/2, 22*mm
    document.line(ruler_left, ruler_y, ruler_left+100*mm, ruler_y)
    for index in range(6):
        x = ruler_left+index*20*mm
        document.line(x, ruler_y-2*mm, x, ruler_y+2*mm)
    document.setFont("Helvetica", 9)
    document.drawCentredString(width/2, 15*mm, "Print 100% / Actual size (no Fit). Verify ruler = 100 mm and five square widths = 100 mm.")
    document.drawCentredString(width/2, 10*mm, "Mount flat on rigid backing. Keep the full white margin visible. Do not fold or laminate with a glossy cover.")
    document.save()
    print(output.resolve())


if __name__ == "__main__":
    main()
