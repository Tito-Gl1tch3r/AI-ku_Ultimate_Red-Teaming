use std::env;
use std::fs;
use std::path::PathBuf;

fn main() {
    //main arrenge
    let src = "./config/config.json";
    let bat = "src/installer/quebrix_install.bat";
    let nssm = "src/nssm/nssm.exe";
    let out_dir = env::var("OUT_DIR").unwrap();

    //windows
    #[cfg(target_os = "windows")]
    {
        let mut config_dest = PathBuf::from(out_dir.clone());
        config_dest.pop();
        config_dest.pop();
        config_dest.pop();
        config_dest.push("config");

        fs::create_dir_all(&config_dest).unwrap();

        let mut bat_dest = PathBuf::from(out_dir.clone());
        bat_dest.pop();
        bat_dest.pop();
        bat_dest.pop();

        let mut nssm_dest = PathBuf::from(out_dir.clone());
        nssm_dest.pop();
        nssm_dest.pop();
        nssm_dest.pop();
        nssm_dest.push("nssm");

        fs::create_dir_all(&nssm_dest).unwrap();

        nssm_dest.push("nssm.exe");
        bat_dest.push("quebrix_install.bat");
        config_dest.push("config.json");

        fs::copy(bat, &bat_dest).unwrap();
        fs::copy(nssm, &nssm_dest).unwrap();
        fs::copy(src, &config_dest).unwrap();

        println!("cargo:rerun-if-changed={}", src);
        println!("cargo:rerun-if-changed={}", bat);
        println!("cargo:rerun-if-changed={}", nssm);
    }

    //not windows
    #[cfg(not(target_os = "windows"))]
    {
        let mut config_dest = PathBuf::from(out_dir.clone());
        config_dest.pop();
        config_dest.pop();
        config_dest.pop();
        config_dest.push("config");
        fs::create_dir_all(&config_dest).unwrap();
        config_dest.push("config.json");
        fs::copy(src, &config_dest).unwrap();
        println!("cargo:rerun-if-changed={}", src);
    }
}
