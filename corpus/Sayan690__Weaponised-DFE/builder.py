#!/usr/bin/env python3
import os
import subprocess
import sys
import shutil
import xml.etree.ElementTree as ET
import re


# Directory where builder.py is run from (this is where the executable will be copied)
RUN_DIR = os.getcwd()


def parse_csproj(csproj_path, exe_name):
    """Parse the .csproj file to get the target .NET version and set the executable name."""
    try:
        tree = ET.parse(csproj_path)
        root = tree.getroot()
        target_framework = root.find(".//TargetFramework")
        if target_framework is None or not target_framework.text:
            print("Error: Could not find TargetFramework in .csproj")
            sys.exit(1)
        
        # Find or create PropertyGroup
        property_group = root.find(".//PropertyGroup")
        if property_group is None:
            property_group = ET.SubElement(root, "PropertyGroup")
        
        # Set or update AssemblyName
        assembly_name = property_group.find("AssemblyName")
        if assembly_name is None:
            assembly_name = ET.SubElement(property_group, "AssemblyName")
        assembly_name.text = exe_name
        
        # Save the modified .csproj
        tree.write(csproj_path, encoding="utf-8", xml_declaration=True)
        return target_framework.text
    except ET.ParseError:
        print(f"Error: Could not parse {csproj_path}")
        sys.exit(1)


def check_dotnet_installed(required_version):
    """Check if the .NET SDK is installed and provide install instructions if not."""
    dotnet_version = required_version.replace("net", "")
    try:
        result = subprocess.run(["dotnet", "--version"], capture_output=True, text=True, check=True)
        installed_version = result.stdout.strip()
        print(f"dotnet CLI is installed with version {installed_version}")
        if dotnet_version not in installed_version:
            print(f"Warning: Installed version {installed_version} does not match required version {dotnet_version}")
        return True
    except FileNotFoundError:
        print(f"Error: 'dotnet' CLI not found. Install .NET SDK {dotnet_version}:")
        print(f"- Windows: Download from https://dotnet.microsoft.com/en-us/download/dotnet/{dotnet_version}")
        print(f"- Linux: Run 'sudo apt-get update && sudo apt-get install -y dotnet-sdk-{dotnet_version}'")
        print("Install it, then rerun this script.")
        sys.exit(1)


def add_package_and_publish(project_dir):
    """Add the NuGet package and publish the project."""
    os.chdir(project_dir)
    print(f"Changed directory to: {project_dir}")

    print("Adding package 'Microsoft.CodeAnalysis.CSharp.Scripting'...")
    subprocess.run(
        ["dotnet", "add", "package", "Microsoft.CodeAnalysis.CSharp.Scripting"],
        check=True
    )

    print("Publishing project for win-x64...")
    subprocess.run(
        ["dotnet", "publish", "-c", "Release", "-r", "win-x64", "--self-contained", "true", "-o", "out"],
        check=True
    )


def copy_executable(project_dir, exe_name):
    """Copy the executable with the specified name to the run directory."""
    exe_name_with_ext = f"{exe_name}.exe"
    source_path = os.path.join(project_dir, "out", exe_name_with_ext)
    dest_path = os.path.join(RUN_DIR, exe_name_with_ext)
    
    if not os.path.exists(source_path):
        print(f"Error: {source_path} not found after publishing.")
        sys.exit(1)
    
    print(f"Copying {source_path} to {dest_path}")
    shutil.copy2(source_path, dest_path)


def main():
    builder_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.join(builder_dir, "Weaponised-DFE")
    csproj_path = os.path.join(project_dir, "Weaponised-DFE.csproj")
    
    if not os.path.exists(csproj_path):
        print(f"Error: .csproj file not found at {csproj_path}")
        sys.exit(1)
    
    # Read config.ini
    config_path = os.path.join(project_dir, "config.ini")
    if not os.path.exists(config_path):
        print(f"Error: config.ini not found at {config_path}")
        sys.exit(1)
    with open(config_path, "r") as f:
        config_content = f.read()
    exe_name_match = re.search(r"exe_name=\[(.*?)\]", config_content)
    if not exe_name_match:
        print("Error: exe_name not found in config.ini")
        sys.exit(1)
    exe_name = exe_name_match.group(1)
    
    # Parse and update .csproj
    required_version = parse_csproj(csproj_path, exe_name)
    print(f"Required .NET version from .csproj: {required_version}")
    
    check_dotnet_installed(required_version)
    add_package_and_publish(project_dir)
    copy_executable(project_dir, exe_name)
    
    print(f"Success! {exe_name}.exe has been built and copied to {RUN_DIR}")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {e}")
        sys.exit(1)
    except PermissionError as e:
        print(f"Error: Permission denied - {e}. Fix directory permissions and rerun.")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)
    