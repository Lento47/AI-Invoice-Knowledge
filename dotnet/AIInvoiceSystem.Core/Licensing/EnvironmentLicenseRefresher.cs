using Microsoft.Extensions.Logging;

namespace AIInvoiceSystem.Core.Licensing;

public sealed class EnvironmentLicenseRefresher : ILicenseRefresher
{
    private readonly ILogger<EnvironmentLicenseRefresher> _logger;
    private readonly string _tokenVariable;
    private readonly string? _expiryVariable;

    public EnvironmentLicenseRefresher(ILogger<EnvironmentLicenseRefresher> logger, string tokenVariable = "AI_LICENSE_TOKEN", string? expiryVariable = "AI_LICENSE_TOKEN_EXPIRES_AT")
    {
        _logger = logger;
        _tokenVariable = tokenVariable;
        _expiryVariable = expiryVariable;
    }

    public Task<LicenseArtifact?> RefreshAsync(LicenseArtifact? current, string? failurePayload, CancellationToken ct = default)
    {
        var token = Environment.GetEnvironmentVariable(_tokenVariable);
        if (string.IsNullOrWhiteSpace(token))
        {
            _logger.LogWarning("Environment variable {Variable} did not contain a license token.", _tokenVariable);
            return Task.FromResult<LicenseArtifact?>(null);
        }

        if (current is not null && string.Equals(current.Token, token, StringComparison.Ordinal))
        {
            _logger.LogDebug("Environment provided the same license token; skipping update.");
            return Task.FromResult<LicenseArtifact?>(null);
        }

        DateTimeOffset? expiresAt = null;
        if (!string.IsNullOrWhiteSpace(_expiryVariable))
        {
            var expiryValue = Environment.GetEnvironmentVariable(_expiryVariable);
            if (!string.IsNullOrWhiteSpace(expiryValue) && DateTimeOffset.TryParse(expiryValue, out var parsed))
            {
                expiresAt = parsed;
            }
        }

        _logger.LogInformation("Loaded updated license token from environment variables.");
        return Task.FromResult<LicenseArtifact?>(new LicenseArtifact(token.Trim(), expiresAt));
    }
}
