import subprocess


def generate_battery_report():
    try:
        # Run the command 'powercfg /batteryreport'
        result = subprocess.run(['powercfg', '/batteryreport'], capture_output=True, text=True, shell=True)

        # Check if the command was successful
        if result.returncode == 0:
            print("Battery report generated successfully.")
            print(result.stdout)  # This will print the standard output of the command
            print(result.stderr)  # This will print any standard errors (if any)
        else:
            print(f"Failed to generate battery report. Return code: {result.returncode}")
            print(result.stderr)  # This will print any standard errors
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    generate_battery_report()
