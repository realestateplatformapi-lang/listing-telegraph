# Copy this file to WINDOWS_CONFIG.ps1 and replace only the values marked CHANGE_ME.
$InstallRoot = "D:\KyivEstateListingTelegraph"
$LocalPort = 8794

# Mac connection. Use the Mac IP shown in System Settings > Network.
$MacHost = "CHANGE_ME_MAC_IP"
$MacUser = "admin"
$MacProjectPath = "/Users/admin/Documents/Codex/2026-07-11/new-chat"
$MacDataPath = "/Users/admin/Documents/Codex/2026-07-11/new-chat/data"
$SshKeyPath = "$env:USERPROFILE\.ssh\id_ed25519"

# Optional public KYIV ESTATE data. Leave blank until real values are available.
$KyivEstateLogoUrl = ""
$KyivEstateLogoPath = "D:\KyivEstateTelegraph\assets\kyiv-estate-logo.jpg"
$KyivEstatePhone = ""
$KyivEstateUrl = ""
$KyivEstateInstagram = ""
$KyivEstateTelegram = ""
$KyivEstateWhatsApp = ""
$KyivEstateFacebook = ""
$KyivEstateEmail = ""
$TelegraphAccessToken = ""
$MediaGitHubRepo = "realestateplatformapi-lang/listing-telegraph"
$MediaGitHubBranch = "media"

# Existing Windows AI photo lane (Block 3 / Block 2). It remains isolated on 8793.
$AiEndpoint = "http://127.0.0.1:8793"
$AiPackagesRoot = "D:\KyivEstateInstantTelegraph\data\packages"
$SourceListingsRoot = "D:\KyivEstateTelegraph\data\listings"
$AiRequired = $true
$AiTimeoutSeconds = 1800
