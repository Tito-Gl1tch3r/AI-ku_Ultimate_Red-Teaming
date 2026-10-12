use std::fs::File;
use std::io::Error;
use std::path::Path;
use std::fs::OpenOptions;

fn GetFileDirectory(file_path: &Path) -> &Path
{
    let output_path: &Path;
    let directory_path: Option<&Path> = file_path.parent();
    if let Some(path) = directory_path
    {
        output_path = path;
    } else {
        let file: &str = file_path.file_name().unwrap().to_str().unwrap();
        let path: &str = file_path.as_os_str().to_str().unwrap();
        let file_index: usize = path.find(file).unwrap();
        let directory: &str = &path[..file_index];
        output_path = Path::new(directory);
    }
    return output_path;
}

pub fn CanEditDirectory(target_directory: &str) -> bool
{
    let mut directory_path: &Path = Path::new(target_directory);
    if !directory_path.exists()
    {
        return false;
    }
    if directory_path.is_file()
    {
        directory_path = GetFileDirectory(directory_path);
    }
    let temp_file_path: String = format!("{:?}\\temp.temp232", directory_path);
    let file_handle: Result<File, Error> = OpenOptions::new().append(false).read(false).write(true).open(temp_file_path);
    if file_handle.is_ok()
    {
        return true;
    }
    return false;
}