# Durable Telegraph media

Telegraph pages embed public image URLs. The native `telegra.ph/upload` endpoint is not part of the official Telegraph API and currently returns `400 Unknown error`, so production publishing stores final listing photos in the public `media` branch of this repository.

Runtime configuration:

- `KYIV_ESTATE_MEDIA_GITHUB_REPO=realestateplatformapi-lang/listing-telegraph`
- `KYIV_ESTATE_MEDIA_GITHUB_BRANCH=media`
- `GITHUB_TOKEN` is read from the authenticated GitHub CLI session at process start and is never saved in the repository, package manifest, or public URL.

Each listing is written in one Git commit under `media/<internal-id>/`. Files use SHA-256-derived names and uploaded URLs are cached in SQLite. The public order is always:

1. primary property photo;
2. KYIV ESTATE logo;
3. remaining property photos.

The same ordering rule is applied to generated PDFs. The original and processed files remain stored separately on drive D.
