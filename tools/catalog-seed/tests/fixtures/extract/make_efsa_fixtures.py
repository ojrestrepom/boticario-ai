"""Genera BOTANIC.xls y ENDPOINTSTUDY.xls de pruebas con unas pocas filas copiadas del compendio real (necesita xlwt).

Uso (fuera del repo): python make_efsa_fixtures.py <ruta de BOTANIC.xls real> <ruta de ENDPOINTSTUDY.xls real> <salida>
El script no se ejecuta en las pruebas; los .xls que produce se versionan.
"""
import sys

import xlrd
import xlwt

BOTANIC_PICK = ("Hypericum perforatum", "Conium maculatum", "Lavandula angustifolia")
ENDPOINT_PICK = ("Conium maculatum", "Calendula officinalis")


def pick(path, names, limit):
    sheet = xlrd.open_workbook(path).sheet_by_index(0)
    header = sheet.row_values(0)
    column = header.index("scientificNames")
    rows, counts = [], {}
    for index in range(1, sheet.nrows):
        values = sheet.row_values(index)
        for name in names:
            if name in str(values[column]) and counts.get(name, 0) < limit:
                counts[name] = counts.get(name, 0) + 1
                rows.append(values)
    return header, rows


def write(path, header, rows):
    book = xlwt.Workbook()
    sheet = book.add_sheet("Hoja1")
    for c, value in enumerate(header):
        sheet.write(0, c, value)
    for r, row in enumerate(rows, 1):
        for c, value in enumerate(row):
            sheet.write(r, c, value)
    book.save(path)


if __name__ == "__main__":
    botanic, endpoint, out = sys.argv[1:4]
    write(out + "/BOTANIC.xls", *pick(botanic, BOTANIC_PICK, 2))
    write(out + "/ENDPOINTSTUDY.xls", *pick(endpoint, ENDPOINT_PICK, 2))
