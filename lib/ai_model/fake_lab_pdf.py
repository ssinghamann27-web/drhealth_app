from fpdf import FPDF

pdf = FPDF()
pdf.add_page()
pdf.set_font("Arial", size=12)
pdf.multi_cell(0, 10, "Patient Name: John Doe\nHemoglobin: 11.2 g/dL\nWBC: 13.5 x10^9/L\nPlatelets: 410 x10^9/L\nGlucose: 108 mg/dL\nCreatinine: 1.1 mg/dL\nSodium: 140 mmol/L\nPotassium: 3.2 mmol/L")
pdf.output("lab_report.pdf")
print("Real lab_report.pdf created.")
