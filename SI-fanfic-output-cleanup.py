
import argparse
import os
import re


def init_argparse() -> argparse.ArgumentParser:
    """
    Create an argument parser for this script.
    Params:
        input_file: The file to read from
        output_file (-o): The file to write to (optional: default=output-clean.csv)
        force (-f): Force overwrite of output_file (optional: default=False)

    """
    parser = argparse.ArgumentParser(
        description="Cleanup SI perl script output")
    parser.add_argument("input_file", help="The file to read from")
    parser.add_argument("-o", "--output_file", help="The file to write to",
                        required=False, default="output-clean.csv")
    parser.add_argument("-f", "--force", help="Force overwrite of output_file",
                        required=False, action="store_true")

    return parser


def verify_input_args(args: argparse.Namespace) -> bool:
    """
    Verify that the input arguments are valid:
        - input_file exists
        - output_file does not exist
    """
    if not os.path.isfile(args.input_file):
        print("input_file does not exist")
        return False

    if os.path.isfile(args.output_file) and not args.force:
        print("output_file exists and force not set")
        return False

    return True


def cleanup_output(input_file: str, output_file: str) -> None:
    """
    Cleanup the output from the SI perl script.

    Lines to keep look like this:
        "The Gardener's Tale (Star Wars SI)|https://forums.spacebattles.com/threads/the-gardeners-tale-star-wars-si.854323/| 1,000,000+"
        "Blind as a Beetle (Naruto SI)|https://forums.sufficientvelocity.com/threads/blind-as-a-beetle-naruto-si.52565/|8 threadmarks, 24k"

    Lines to remove include blank lines, lines with "| |", and lines with "into some problems",
    or any other lines that look like they're not useful.
    """
    with open(input_file, "r") as f:
        lines = f.readlines()

    # Define a regular expression to match the lines we want to keep
    pattern = re.compile(r'^.+?\|https?://.+?')

    # Filter out lines that don't match the pattern
    lines = filter(pattern.match, lines)

    with open(output_file, "w") as f:
        for line in lines:
            f.write(line.strip() + "\n")

    print(f"Output cleaned up and written to {output_file}")


def main():
    print("Cleanup SI perl script output")

    parser = init_argparse()
    args = parser.parse_args()

    if not verify_input_args(args):
        print("Invalid input arguments")
        return

    cleanup_output(args.input_file, args.output_file)


if __name__ == "__main__":
    main()
