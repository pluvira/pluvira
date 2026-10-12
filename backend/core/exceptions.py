"""Custom domain exception hierarchy for Pluvira backend."""


class PluviraError(Exception):
    """Base exception class for all domain errors in Pluvira."""

    pass




class EntityNotFoundError(PluviraError):
    """Raised when a requested domain entity (channel, source, merge) is not found."""

    pass


class DuplicateEntityError(PluviraError):
    """Raised when attempting to create an entity that already exists."""

    pass


class InvalidConfigurationError(PluviraError):
    """Raised when configuration validation fails or file is corrupted."""

    pass


class ProcessLockedError(PluviraError):
    """Raised when a background process (runner or scanner) is already active."""

    pass


class SystemJobImmutableError(PluviraError):
    """Raised when attempting to delete or illegally mutate a protected system job."""

    pass


class AuthenticationError(PluviraError):
    """Raised when user authentication or access credentials fail validation."""

    pass


class BadGatewayError(PluviraError):
    """Raised when connection to an upstream stream server fails."""

    pass


class ValidationDomainError(PluviraError):
    """Raised when business logic parameter or domain validation fails."""

    pass


class LicenseThresholdExceededError(PluviraError):
    """Raised when a Free Tier resource threshold (BSL 1.1) is exceeded without a Pro license."""

    pass


class MaxSourcesExceededError(LicenseThresholdExceededError):
    """Raised when active M3U playlist sources exceed Free Tier limit."""

    pass


class MaxChannelsExceededError(LicenseThresholdExceededError):
    """Raised when total channel count exceeds Free Tier limit."""

    pass


class MaxConcurrentStreamsExceededError(LicenseThresholdExceededError):
    """Raised when concurrent stream views exceed Free Tier limit."""

    pass


class PersonalChannelLimitExceeded(LicenseThresholdExceededError):
    """Raised when curated channels in personal playlist exceed Free Tier limit (max 25)."""

    pass


class MaxSlotsExceededError(LicenseThresholdExceededError):
    """Raised when stream slots per channel exceed Free Tier limit."""

    pass


class MetadataLookupError(PluviraError):
    """Raised when external metadata enrichment lookup fails or times out."""

    pass


class MaxPlaylistsExceededError(LicenseThresholdExceededError):
    """Raised when total personal playlists exceed Free Tier limit."""

    pass


class SnapshotPinLimitExceededError(LicenseThresholdExceededError):
    """Raised when snapshot pinning quota (N-1) is exceeded or attempted on free tier."""

    pass
