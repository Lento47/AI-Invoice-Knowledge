namespace AIInvoiceSystem.Core.Licensing;

public interface ILicenseStore
{
    Task<LicenseArtifact?> LoadAsync(CancellationToken ct = default);
    Task SaveAsync(LicenseArtifact artifact, CancellationToken ct = default);
    Task ClearAsync(CancellationToken ct = default);
}
