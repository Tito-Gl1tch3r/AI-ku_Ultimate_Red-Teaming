# core/apt_loader.py

APT_PROFILES = {
    "APT29 - Cozy Bear": [
        {"attack": "Credential Dump", "technique": "T1003.001"},
        {"attack": "Lateral Movement (PsExec)", "technique": "T1021.002"}
    ],
    "APT41 - Dual Use": [
        {"attack": "Command Injection", "technique": "T1059"},
        {"attack": "SQL Injection", "technique": "T1505.001"},
        {"attack": "XSS (Reflected)", "technique": "T1059.007"}
    ]
}

def get_profiles():
    return list(APT_PROFILES.keys())

def load_profile(profile_name):
    return APT_PROFILES.get(profile_name, [])
