using AIInvoiceSystem.Core.Licensing;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;

namespace AIInvoiceSystem.API.Licensing;

public sealed class LicenseInitializationHostedService : IHostedService
{
    private readonly ILicenseManager _licenseManager;
    private readonly ILogger<LicenseInitializationHostedService> _logger;

    public LicenseInitializationHostedService(ILicenseManager licenseManager, ILogger<LicenseInitializationHostedService> logger)
    {
        _licenseManager = licenseManager;
        _logger = logger;
    }

    public async Task StartAsync(CancellationToken cancellationToken)
    {
        await _licenseManager.InitializeAsync(cancellationToken).ConfigureAwait(false);
        var artifact = _licenseManager.Current;
        if (artifact is null)
        {
            _logger.LogWarning("AI license artifact not found at startup.");
        }
        else
        {
            _logger.LogInformation("AI license artifact loaded with expiry {Expiry}.", artifact.ExpiresAt);
        }
    }

    public Task StopAsync(CancellationToken cancellationToken) => Task.CompletedTask;
}
