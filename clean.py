def clean_html():
    input_file = 'battery-report.html'
    output_file = 'cleaned_battery-report.html'
    try:
        with open(input_file, 'r') as infile:
            lines = infile.readlines()

        # Remove empty lines
        cleaned_lines = [line.strip() for line in lines if line.strip()]

        with open(output_file, 'w') as outfile:
            outfile.write('\n'.join(cleaned_lines))

        print(f"Cleaned HTML saved to {output_file}")
    except FileNotFoundError:
        print(f"File '{input_file}' not found.")


if __name__ == "__main__":
    clean_html()
