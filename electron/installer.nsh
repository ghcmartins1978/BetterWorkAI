!macro customInit
  ; Add any custom initialization steps for the Windows installer here
  
  ; Check if we need to install Microsoft Visual C++ Redistributable
  !define MSVC_VERSION "14.0"
  !define MSVC_REDIST "vc_redist.x64.exe"
  !define MSVC_REDIST_URL "https://aka.ms/vs/17/release/vc_redist.x64.exe"
  
  ; Add function to download and install VC++ Redistributable if needed
  Function InstallVCRedist
    ; Check if VC++ Redistributable is already installed
    ReadRegStr $0 HKLM "SOFTWARE\Microsoft\VisualStudio\${MSVC_VERSION}\VC\Runtimes\x64" "Installed"
    ${If} $0 == "1"
      DetailPrint "Microsoft Visual C++ Redistributable ${MSVC_VERSION} is already installed."
    ${Else}
      DetailPrint "Microsoft Visual C++ Redistributable ${MSVC_VERSION} is not installed. Installing now..."
      
      ; Download VC++ Redistributable
      DetailPrint "Downloading ${MSVC_REDIST}..."
      NSISdl::download "${MSVC_REDIST_URL}" "$TEMP\${MSVC_REDIST}"
      
      ; Install VC++ Redistributable
      DetailPrint "Installing ${MSVC_REDIST}..."
      ExecWait '"$TEMP\${MSVC_REDIST}" /install /quiet /norestart' $0
      
      ; Check installation result
      ${If} $0 == 0
        DetailPrint "Microsoft Visual C++ Redistributable ${MSVC_VERSION} installed successfully."
      ${Else}
        DetailPrint "Microsoft Visual C++ Redistributable ${MSVC_VERSION} installation failed with error code: $0"
        MessageBox MB_OK|MB_ICONEXCLAMATION "Failed to install Microsoft Visual C++ Redistributable. The application may not work correctly."
      ${EndIf}
      
      ; Delete temporary file
      Delete "$TEMP\${MSVC_REDIST}"
    ${EndIf}
  FunctionEnd
  
  ; Call the function to install VC++ Redistributable
  Call InstallVCRedist
!macroend

!macro customUnInit
  ; Add any custom uninstallation steps for the Windows installer here
!macroend