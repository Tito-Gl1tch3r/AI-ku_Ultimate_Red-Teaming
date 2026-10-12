# =======================
# 🏴‍☠️ CTF Flag Generator
# =======================

import os
import random

# --- SCRIPT FUNCTIONS ---


# Flag's generator function
def generate_flag():
    flag_content = "Why always me?"
    flag_names = [
        ".flag",
        ".galf",
        ".i_am_not_a_flag",
        ".oh_you_found_me",
        ".easy_peasy",
        ".are_you_sure",
        ".definitely_not_this_file",
        ".well_well",
        ".oh_flag_me",
        ".f_l_a_g",
        ".are_you_staring_at_me",
        ".are_you_lost",
        ".of_course_you_had_to",
        ".please_dont",
        ".why_soo_long",
        ".wooooha",
        ".ruuuuun",
        ".hands_off",
        ".its_not_what_you_think",
        ".dont_click_me",
        ".no_no_no",
    ]
    directories = ["/tmp", "/var/tmp", "/var/log", "/run", "/etc"]

    selected_dir = random.choice(directories)  # Pick the random directory
    selected_flag_name = random.choice(flag_names) + ".txt"  # Pick the random name
    full_path = os.path.join(selected_dir, selected_flag_name)  # Create flag path

    # Error's handler
    try:
        with open(full_path, "x") as f:
            f.write(flag_content)
        print("Hidden flag is created!")
        # Uncomment only for testing purposes
        # print(f"Flag name: {selected_flag_name}. Flag directory: {full_path}") # Testing prompt
    except FileExistsError:
        print("ERROR: File is already exists!")
        # Uncomment only for testing purposes
        # print(f"Flag name: {selected_flag_name}. Flag directory: {full_path}") # Testing prompt
        return None
    except PermissionError:
        print("Permission denied. Add SUDO privilege!")
        return None
    except Exception as e:
        print(f"An error occurred: {e}. Try again!")
        return None


# --- MAIN SCRIPT ---

# Invoke flag's generator function
generate_flag()
