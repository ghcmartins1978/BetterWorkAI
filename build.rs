use std::process::Command;
use std::env;
use std::path::Path;

fn main() {
    println!("cargo:rerun-if-changed=resources/tagui/src/tagui");
    println!("cargo:rerun-if-changed=resources/tagui/tagui.exe.cmd");
    
    // Make the tagui script executable on Unix platforms
    if env::consts::FAMILY == "unix" {
        let tagui_path = Path::new("resources/tagui/src/tagui");
        if tagui_path.exists() {
            let status = Command::new("chmod")
                .arg("+x")
                .arg(tagui_path)
                .status();
                
            match status {
                Ok(exit_status) => {
                    if !exit_status.success() {
                        println!("cargo:warning=Failed to make tagui executable: {}", exit_status);
                    }
                },
                Err(e) => {
                    println!("cargo:warning=Failed to run chmod: {}", e);
                }
            }
        } else {
            println!("cargo:warning=TagUI script not found at: {:?}", tagui_path);
        }
    }
    
    // On Windows, rename the .cmd file to .exe for testing
    if env::consts::FAMILY == "windows" {
        let cmd_path = Path::new("resources/tagui/tagui.exe.cmd");
        let exe_path = Path::new("resources/tagui/tagui.exe");
        
        if cmd_path.exists() && !exe_path.exists() {
            use std::fs;
            match fs::copy(cmd_path, exe_path) {
                Ok(_) => {},
                Err(e) => println!("cargo:warning=Failed to copy tagui.exe.cmd to tagui.exe: {}", e)
            }
        }
    }
}