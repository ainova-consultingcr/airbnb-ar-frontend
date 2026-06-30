import argparse

from provider_reporting import load_records, write_provider_report

parser = argparse.ArgumentParser(description="Genera el reporte comercial de proveedores de AVI")
parser.add_argument("input", help="Archivo CSV o JSON exportado desde la hoja EVENTS")
parser.add_argument("--property-id", help="Filtrar un hotel o Airbnb especifico")
parser.add_argument("--output", default="../reports/avi_provider_report.html")
args = parser.parse_args()

print(write_provider_report(load_records(args.input), args.output, args.property_id))