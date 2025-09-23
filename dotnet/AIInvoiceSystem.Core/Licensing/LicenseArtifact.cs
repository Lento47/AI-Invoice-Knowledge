namespace AIInvoiceSystem.Core.Licensing;

public sealed record LicenseArtifact(string Token, DateTimeOffset? ExpiresAt = null)
{
    public bool IsExpired(DateTimeOffset now) => ExpiresAt is not null && ExpiresAt <= now;
}
