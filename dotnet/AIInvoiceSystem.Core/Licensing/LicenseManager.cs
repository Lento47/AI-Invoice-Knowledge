using Microsoft.Extensions.Logging;

namespace AIInvoiceSystem.Core.Licensing;

public sealed class LicenseManager : ILicenseManager, IDisposable
{
    private readonly ILicenseStore _store;
    private readonly ILicenseRefresher _refresher;
    private readonly ILogger<LicenseManager> _logger;
    private readonly SemaphoreSlim _sync = new(1, 1);

    private volatile bool _initialized;
    private LicenseArtifact? _current;

    public LicenseManager(ILicenseStore store, ILicenseRefresher refresher, ILogger<LicenseManager> logger)
    {
        _store = store;
        _refresher = refresher;
        _logger = logger;
    }

    public LicenseArtifact? Current => _current;

    public async Task InitializeAsync(CancellationToken ct = default)
    {
        if (_initialized)
        {
            return;
        }

        await _sync.WaitAsync(ct).ConfigureAwait(false);
        try
        {
            if (_initialized)
            {
                return;
            }

            _current = await _store.LoadAsync(ct).ConfigureAwait(false);
            if (_current is not null)
            {
                _logger.LogInformation("Loaded persisted license artifact with expiry {Expiry}.", _current.ExpiresAt);
            }
            else
            {
                _logger.LogWarning("No persisted license artifact was found.");
            }

            _initialized = true;
        }
        finally
        {
            _sync.Release();
        }
    }

    public async Task<string?> GetTokenAsync(CancellationToken ct = default)
    {
        await EnsureInitializedAsync(ct).ConfigureAwait(false);
        return _current?.Token;
    }

    public async Task UpdateAsync(LicenseArtifact artifact, CancellationToken ct = default)
    {
        ArgumentNullException.ThrowIfNull(artifact);

        await EnsureInitializedAsync(ct).ConfigureAwait(false);

        await _sync.WaitAsync(ct).ConfigureAwait(false);
        try
        {
            _current = artifact;
            await _store.SaveAsync(artifact, ct).ConfigureAwait(false);
            _logger.LogInformation("Persisted new license artifact with expiry {Expiry}.", artifact.ExpiresAt);
        }
        finally
        {
            _sync.Release();
        }
    }

    public async Task<bool> RefreshAsync(string? failurePayload = null, CancellationToken ct = default)
    {
        await EnsureInitializedAsync(ct).ConfigureAwait(false);

        await _sync.WaitAsync(ct).ConfigureAwait(false);
        try
        {
            var refreshed = await _refresher.RefreshAsync(_current, failurePayload, ct).ConfigureAwait(false);
            if (refreshed is null)
            {
                _logger.LogWarning("License refresh did not produce a new artifact.");
                return false;
            }

            if (string.IsNullOrWhiteSpace(refreshed.Token))
            {
                _logger.LogWarning("License refresh returned an empty token; ignoring result.");
                return false;
            }

            if (_current is not null && string.Equals(_current.Token, refreshed.Token, StringComparison.Ordinal))
            {
                _logger.LogDebug("License refresh returned an unchanged token.");
                return false;
            }

            _current = refreshed;
            await _store.SaveAsync(refreshed, ct).ConfigureAwait(false);
            _logger.LogInformation("License token refreshed successfully with expiry {Expiry}.", refreshed.ExpiresAt);
            return true;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "License refresh failed to complete.");
            return false;
        }
        finally
        {
            _sync.Release();
        }
    }

    private async Task EnsureInitializedAsync(CancellationToken ct)
    {
        if (_initialized)
        {
            return;
        }

        await InitializeAsync(ct).ConfigureAwait(false);
    }

    public void Dispose()
    {
        _sync.Dispose();
    }
}
