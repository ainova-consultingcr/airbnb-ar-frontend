import argparse

from reporting import demo_records, load_records, write_html_report


def main():
    parser = argparse.ArgumentParser(
        description="Generate a professional AVI HTML report from Google Sheets CSV/JSON data."
    )
    parser.add_argument(
        "input",
        nargs="?",
        help="CSV or JSON export. If omitted, a demo report is generated.",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="../reports/avi_report_demo.html",
        help="Output HTML path.",
    )
    parser.add_argument(
        "--property-id",
        help="Optional property/entity id filter, for example hotel_demo.",
    )
    args = parser.parse_args()

    records = load_records(args.input) if args.input else demo_records()
    output = write_html_report(records, args.output, property_id=args.property_id)
    print(f"Report generated: {output}")


if __name__ == "__main__":
    main()
