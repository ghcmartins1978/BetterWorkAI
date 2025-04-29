# BettermanAI - Installation Guide

Thank you for choosing BettermanAI, your personal workflow optimizer!

## System Requirements

- **Windows**: Windows 10 or newer
- **macOS**: macOS 10.15 (Catalina) or newer
- **Linux**: Ubuntu 20.04+, Debian 10+, or compatible distribution
- **Disk Space**: At least 500MB free
- **Memory**: 4GB RAM minimum, 8GB recommended

## Installation Instructions

### Windows

1. Download the `BettermanAI-Setup-1.0.0.exe` installer from the releases page
2. Double-click the installer to launch it
3. Follow the on-screen instructions
4. The installer will add BettermanAI to your Start menu and desktop (if selected)

### macOS

1. Download the `BettermanAI-1.0.0.dmg` file from the releases page
2. Double-click the DMG file to open it
3. Drag the BettermanAI app to your Applications folder
4. Eject the DMG
5. Start the application from your Applications folder
6. On first launch, macOS may ask for security permissions - follow the prompts

### Linux

#### Debian/Ubuntu (DEB package)

1. Download the `bettermanai_1.0.0_amd64.deb` file from the releases page
2. Install with:
   ```
   sudo dpkg -i bettermanai_1.0.0_amd64.deb
   sudo apt-get install -f  # To resolve any dependencies
   ```
3. Launch BettermanAI from your applications menu

#### AppImage (Universal Linux)

1. Download the `BettermanAI-1.0.0.AppImage` file from the releases page
2. Make it executable:
   ```
   chmod +x BettermanAI-1.0.0.AppImage
   ```
3. Run the AppImage:
   ```
   ./BettermanAI-1.0.0.AppImage
   ```

## Permissions Required

BettermanAI requires certain permissions to function properly:

- **Screen Recording**: To detect and analyze your workflow
- **Accessibility**: To automate interactions with applications
- **Camera** (optional): For optional features like computer vision
- **Microphone** (optional): For voice command features

Your operating system will prompt you to grant these permissions during first use.

## Troubleshooting

### Windows

- If installation fails, ensure you have administrator rights
- If the application doesn't start, check if Microsoft Visual C++ Runtime is installed

### macOS

- If macOS blocks the app from opening, go to System Preferences > Security & Privacy and click "Open Anyway"
- For automation features, grant Accessibility permissions in System Preferences > Security & Privacy > Privacy > Accessibility

### Linux

- If AppImage fails, ensure you have FUSE installed: `sudo apt-get install fuse libfuse2`
- For desktop automation, you may need to install `xdotool`

## Support

If you encounter any issues, please:

1. Check our [FAQ](https://bettermanai.com/faq) for common problems
2. Visit our [support forum](https://bettermanai.com/support)
3. Contact us at support@bettermanai.com

## Updates

BettermanAI includes automatic updates. When a new version is available, you'll be prompted to install it.