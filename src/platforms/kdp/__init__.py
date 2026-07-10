# File Purpose: Package marker for the Kindle/KDP upload-bundle pipeline.
# Primary Functions/Classes: re-exports build_upload_bundle.
# Inputs/Outputs: Import surface for adapters and CLI consumers.

from platforms.kdp.bundle import build_upload_bundle, package_upload_bundle

__all__ = ["build_upload_bundle", "package_upload_bundle"]
