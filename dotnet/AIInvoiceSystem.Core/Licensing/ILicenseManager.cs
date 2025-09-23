namespace AIInvoiceSystem.Core.Licensing;

public interface ILicenseManager
{
    LicenseArtifact? Current { get; }

    Task InitializeAsync(CancellationToken ct = default);
    Task<string?> GetTokenAsync(CancellationToken ct = default);
    Task UpdateAsync(LicenseArtifact artifact, CancellationToken ct = default);
    Task<bool> RefreshAsync(string? failurePayload = null, CancellationToken ct = default);
}
