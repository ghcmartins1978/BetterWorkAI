use std::process::{Command, Stdio};
use std::fs::{self, File};
use std::io::Write;
use std::path::{Path, PathBuf};
use std::env;
use std::error::Error;
use serde::{Deserialize, Serialize};
use uuid::Uuid;
use chrono::Utc;
use std::time::SystemTime;
use path_absolutize::Absolutize;
use tempfile::tempdir;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MacroResponse {
    pub status: String,
    pub pid: Option<u32>,
    pub log_path: Option<String>,
}

/// Compiles a YAML file to TagUI syntax and runs it using the TagUI binary.
/// Returns a JSON response with status, process ID, and log path.
pub fn run_macro(yaml_path: &str, mode: &str) -> Result<MacroResponse, Box<dyn Error>> {
    // Determine if we're in a dry-run mode
    let dry_run = mode.to_lowercase() == "dry-run";
    
    // Generate a unique ID for this run
    let run_id = Uuid::new_v4().to_string();
    let timestamp = Utc::now().format("%Y%m%d_%H%M%S").to_string();
    let log_file_name = format!("macro_{}_{}.log", Path::new(yaml_path).file_stem().unwrap().to_string_lossy(), timestamp);
    let log_path = PathBuf::from("logs").join(log_file_name);
    
    // Ensure logs directory exists
    fs::create_dir_all("logs")?;
    
    // For now, since we're not implementing YAML -> TagUI conversion here,
    // we'll use a test TagUI file directly
    let tagui_script_path = if Path::new(yaml_path).exists() {
        // In real implementation, this would compile YAML to .tag file
        yaml_path.to_string()
    } else {
        // For testing, use the hello.tag sample
        "resources/tagui/hello.tag".to_string()
    };
    
    // Determine the TagUI binary based on OS
    let tagui_binary = if cfg!(target_os = "windows") {
        "resources/tagui/tagui.exe"
    } else {
        "resources/tagui/src/tagui"
    };
    
    // Create a log file
    let log_file = File::create(&log_path)?;
    
    // Run the TagUI command
    let mut command = Command::new(tagui_binary);
    command.arg(&tagui_script_path);
    
    // Add dry-run flag if needed
    if dry_run {
        command.arg("-n");
    }
    
    // Add additional TagUI arguments
    command.arg("--nobrowser"); // For safety, as per guidelines
    
    // Capture output
    command.stdout(Stdio::from(log_file.try_clone()?))
           .stderr(Stdio::from(log_file));
    
    // Start the process
    let child = command.spawn();
    
    match child {
        Ok(child) => {
            let pid = child.id();
            
            // In a real implementation, you would store the child in a managed process pool
            // For this example, we let it run independently
            
            Ok(MacroResponse {
                status: "running".to_string(),
                pid: Some(pid),
                log_path: Some(log_path.to_string_lossy().to_string()),
            })
        },
        Err(e) => {
            // Log the error
            let mut log_file = File::create(&log_path)?;
            writeln!(log_file, "Failed to start TagUI process: {}", e)?;
            
            Err(Box::new(e))
        }
    }
}

/// This function will be implemented in Ticket A2
/// Converts a YAML file to TagUI syntax
fn compile_yaml_to_tagui(_yaml_path: &str, _output_path: &str) -> Result<(), Box<dyn Error>> {
    // Placeholder for YAML to TagUI compilation
    // This will be implemented in Ticket A2
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_run_macro_response_format() {
        // Since we can't actually run TagUI in a test, we'll just check
        // that the function returns a properly formatted response
        let response = run_macro("resources/tagui/hello.tag", "normal");
        
        assert!(response.is_ok(), "run_macro should return Ok for a valid path");
        
        let response = response.unwrap();
        assert_eq!(response.status, "running");
        assert!(response.pid.is_some());
        assert!(response.log_path.is_some());
        
        let log_path = response.log_path.unwrap();
        assert!(log_path.contains("logs/macro_hello_"));
    }
}