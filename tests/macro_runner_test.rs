#[cfg(test)]
mod tests {
    use std::path::Path;
    use std::fs;
    use std::io::Write;
    use tempfile::tempdir;
    
    #[test]
    fn test_mock_tagui_execution() {
        // Create a test script
        let temp_dir = tempdir().expect("Failed to create temp directory");
        let test_script_path = temp_dir.path().join("test_script.tag");
        
        let mut test_script = fs::File::create(&test_script_path)
            .expect("Failed to create test script");
            
        writeln!(test_script, "// Test script")
            .expect("Failed to write to test script");
        writeln!(test_script, "echo \"Hello from test script\"")
            .expect("Failed to write to test script");
        writeln!(test_script, "echo \"DONE\"")
            .expect("Failed to write to test script");
            
        // Determine the TagUI binary based on OS
        let tagui_binary = if cfg!(target_os = "windows") {
            "resources/tagui/tagui.exe"
        } else {
            "resources/tagui/src/tagui"
        };
        
        // Check if the TagUI binary exists
        assert!(Path::new(tagui_binary).exists(), 
                "TagUI binary not found at: {}", tagui_binary);
        
        // Test executing the script
        let output = std::process::Command::new(tagui_binary)
            .arg(test_script_path)
            .output()
            .expect("Failed to execute TagUI");
            
        let stdout = String::from_utf8_lossy(&output.stdout);
        
        // Check that the command completed successfully
        assert!(output.status.success(), 
                "TagUI execution failed: {}", stdout);
        
        // Check that the script output contains expected text
        assert!(stdout.contains("test_script.tag"), 
                "Script output does not contain script name: {}", stdout);
        
        // Check that the script output contains "DONE" at the end
        assert!(stdout.contains("DONE"), 
                "Script output does not contain DONE: {}", stdout);
    }
}