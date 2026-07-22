# Windows quick start

The GitHub application and the existing AI photo lane must use different ports. The example configuration installs this application into `D:\KyivEstateListingTelegraph` on port `8794`; the existing AI service remains on `127.0.0.1:8793` and stores certified packages in `D:\KyivEstateInstantTelegraph\data\packages`.

Copy `WINDOWS_CONFIG.example.ps1` to `WINDOWS_CONFIG.ps1`, keep the provided D-drive logo and Block 2 listing paths, and fill in only the official KYIV ESTATE contact links. With `$AiRequired = $true`, a package cannot be published when the AI lane fails or returns no certified photos. The Block 2 archive is used as a fallback for the `original` comparison set when a source CDN URL has expired.

1. Copy `WINDOWS_CONFIG.example.ps1` to `WINDOWS_CONFIG.ps1` and fill in the Mac IP.
2. Run `INSTALL_WINDOWS.ps1`.
3. Run `SYNC_FROM_MAC.ps1` if Mac data must be copied.
4. Run `START_BLOCK3_HIDDEN.ps1`.
5. Open `http://127.0.0.1:8794/`.

The complete Ukrainian setup guide is delivered as `KYIV_ESTATE_WINDOWS_SETUP.md` with the project documentation.
