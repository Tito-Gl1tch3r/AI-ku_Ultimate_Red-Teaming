#!/bin/bash

current_dir=$(pwd)

echo "[i] Checking for virtual environment"
if [ ! -d "../../venv" ]; then
    echo "[i] Virtual environment not found, creating one"
    python3 -m venv ../../venv
fi

echo "[i] Activating virtual environment"
source ../../venv/bin/activate

echo "[i] Installing conan"
pip install conan
conan profile detect

echo "[i] Cleaning build directory"
mkdir -p build
rm -rf build/*
cd build

echo "[i] Installing conan dependencies"
cp ../conanfile.txt .
conan install . --build=missing -s build_type=Release -g CMakeToolchain

echo "[i] Checking for MySQL Connector/C++"
if ! ldconfig -p | grep -q libmariadbcpp; then
    if ! find /usr/local/lib/mariadb -name 'libmariadbcpp.so*' | grep -q .; then
        echo "[i] MySQL Connector/C++ not found, installing"
        rm -rf /tmp/mariadb-connector-cpp
        git clone --recurse-submodules -b 1.1.6 https://github.com/mariadb-corporation/mariadb-connector-cpp.git /tmp/mariadb-connector-cpp
        cd /tmp/mariadb-connector-cpp
        git submodule update --init --recursive
        mkdir build
        cd build
        cmake .. -DCMAKE_INSTALL_PREFIX=/usr/local || { echo "[e] CMake configuration failed"; exit 1; }
        make || { echo "[e] Make build failed"; exit 1; }
        sudo make install || { echo "[e] Installation failed"; exit 1; }
        echo "[i] MySQL Connector/C++ installed"
        cd -
        echo "/usr/local/lib/mariadb" | sudo tee /etc/ld.so.conf.d/mariadb.conf
        sudo ldconfig
        sudo ln -sf /usr/local/lib/mariadb/libmariadbcpp.so.* /usr/local/lib/mariadb/libmariadbcpp.so
    else
        echo "[i] Found library file, forcing ldconfig registration"
        echo "/usr/local/lib/mariadb" | sudo tee /etc/ld.so.conf.d/mariadb.conf
        sudo ldconfig
    fi
else
    echo "[i] MySQL Connector/C++ already in linker cache"
fi

echo "[i] Setting library paths"
if ! grep -q "/usr/local/lib/mariadb" ~/.bashrc; then
    echo "export LD_LIBRARY_PATH=/usr/local/lib/mariadb:\$LD_LIBRARY_PATH" >> ~/.bashrc
fi
export LD_LIBRARY_PATH="/usr/local/lib/mariadb:$LD_LIBRARY_PATH"
export CMAKE_PREFIX_PATH="/usr/local/lib/mariadb"

cd $current_dir/build

echo "[i] Generating SBOM"
conan config install https://github.com/conan-io/conan-extensions.git
pip install 'cyclonedx-python-lib>=5.0.0,<6'
conan sbom:cyclonedx --format 1.4_json . > sbom.cyclonedx.json

echo "[i] CMake compiling"
cmake .. -DCMAKE_TOOLCHAIN_FILE=build/conan_toolchain.cmake -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_COMPILER=clang++ || { echo "[E] CMake configuration failed"; exit 1; }

echo "[i] CMake building"
cmake --build . || { echo "[E] Build failed"; exit 1; }




