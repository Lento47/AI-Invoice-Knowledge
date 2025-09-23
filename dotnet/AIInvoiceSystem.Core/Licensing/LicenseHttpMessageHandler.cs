using Microsoft.Extensions.Logging;

namespace AIInvoiceSystem.Core.Licensing;

public sealed class LicenseHttpMessageHandler : DelegatingHandler
{
    private readonly ILicenseManager _licenseManager;
    private readonly ILogger<LicenseHttpMessageHandler> _logger;

    public const string LicenseHeaderName = "X-License-Token";

    public LicenseHttpMessageHandler(ILicenseManager licenseManager, ILogger<LicenseHttpMessageHandler> logger)
    {
        _licenseManager = licenseManager;
        _logger = logger;
    }

    protected override async Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken)
    {
        var token = await _licenseManager.GetTokenAsync(cancellationToken).ConfigureAwait(false);
        if (!string.IsNullOrWhiteSpace(token))
        {
            request.Headers.Remove(LicenseHeaderName);
            request.Headers.TryAddWithoutValidation(LicenseHeaderName, token);
        }
        else
        {
            _logger.LogDebug("No license token available when preparing request {Method} {Uri}.", request.Method, request.RequestUri);
        }

        return await base.SendAsync(request, cancellationToken).ConfigureAwait(false);
    }
}
