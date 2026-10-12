import os
import argparse

def rename_with_hidden_spaces(original_file, fake_base="hello_word.mp4", num_invisible=20, visible_spaces=12):
    # Unicode invisible character (Zero Width Space)
    invisible_char = '\u200B'

    # Build the new fake filename
    new_filename = f"{fake_base}{invisible_char * num_invisible}{' ' * visible_spaces}.exe"

    # Check if original file exists
    if not os.path.isfile(original_file):
        print(f"❌ Error: File '{original_file}' not found.")
        return

    # Perform renaming
    os.rename(original_file, new_filename)
    print(f"✅ File renamed to: {new_filename}")
    print(f"ℹ️ Looks like: {fake_base}{' ' * visible_spaces}.exe (but contains {num_invisible} invisible chars hidden inside)")

def main():
    parser = argparse.ArgumentParser(description="Disguise an .exe file to look like a long .mp4,png etc filename with hidden Unicode characters.",
                                    epilog="Example: python3 filename_obfuscate.py shell.exe --fake-name hello_word.mp4 --invisible 20 --visible-spaces 10")
    parser.add_argument("original_file", help="The original .exe file to rename")
    parser.add_argument("--fakename", default="hello_word.mp4", help="Visible part of the filename (default: hello_word.mp4)")
    parser.add_argument("--invisible", type=int, default=20, help="Number of invisible Unicode characters (default: 20)")
    parser.add_argument("--visible-spaces", type=int, default=12, help="Number of visible spaces before .exe (default: 12)")

    args = parser.parse_args()
    rename_with_hidden_spaces(args.original_file, args.fake_name, args.invisible, args.visible_spaces)

if __name__ == "__main__":
    main()

