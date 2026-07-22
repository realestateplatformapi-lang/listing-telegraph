# Copy this file to WINDOWS_CONFIG.ps1 and replace only the values marked CHANGE_ME.
$InstallRoot = "D:\KyivEstateInstantTelegraph"
$LocalPort = 8793

# Mac connection. Use the Mac IP shown in System Settings > Network.
$MacHost = "CHANGE_ME_MAC_IP"
$MacUser = "admin"
$MacProjectPath = "/Users/admin/Documents/Codex/2026-07-11/new-chat"
$MacDataPath = "/Users/admin/Documents/Codex/2026-07-11/new-chat/data"
$SshKeyPath = "$env:USERPROFILE\.ssh\id_ed25519"

# Optional public KYIV ESTATE data. Leave blank until real values are available.
$KyivEstateLogoUrl = ""
$KyivEstatePhone = ""
$KyivEstateUrl = ""
$TelegraphAccessToken = ""
