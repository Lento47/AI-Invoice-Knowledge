namespace AIInvoiceSystem.Core.Licensing;

public interface ILicenseRefresher
{
    Task<LicenseArtifact?> RefreshAsync(LicenseArtifact? current, string? failurePayload, CancellationToken ct = default);
}
