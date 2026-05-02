import os
import subprocess
import sys


def run_command(command):
    print(f"\nRunning: {' '.join(command)}\n")
    result = subprocess.run(command)

    if result.returncode != 0:
        print(f"\nCommand failed: {' '.join(command)}")
        sys.exit(result.returncode)


def main():
    print("Starting CS410 Final Project...\n")

    if not os.environ.get("OPENROUTER_API_KEY"):
        print("ERROR: OPENROUTER_API_KEY is not set.\n")

        print("To get an OpenRouter API key:")
        print("1. Go to https://openrouter.ai/")
        print("2. Create an account or sign in.")
        print("3. Go to https://openrouter.ai/settings/keys")
        print("4. Create a new API key.")
        print("5. Copy the key.\n")

        print("Then set it in PowerShell like this:")
        print('$env:OPENROUTER_API_KEY="your_api_key_here"\n')

        print("After setting the key, run the project again:")
        print("python run_project.py\n")

        print("Do not paste your API key into the source code or commit it to GitHub.")
        sys.exit(1)

    print("OpenRouter API key detected.")
    print("Training/loading sentiment model...")

    run_command([sys.executable, "train_sentiment_v2.py"])

    print("Starting the application...")

    run_command([sys.executable, "app_v3.py"])


if __name__ == "__main__":
    main()