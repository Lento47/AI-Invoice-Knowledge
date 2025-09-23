using System.Diagnostics;
using System.Security.Cryptography;
using System.Text.Json;
using Microsoft.Extensions.Logging;

namespace AIInvoiceSystem.Core.Licensing;

public static class LicenseStoreFactory
{
    public static ILicenseStore CreateDefault(string applicationName, ILoggerFactory loggerFactory)
    {
        if (OperatingSystem.IsMacOS())
        {
            return new MacKeychainLicenseStore(applicationName, loggerFactory.CreateLogger<MacKeychainLicenseStore>());
        }

        return new FileProtectedLicenseStore(applicationName, loggerFactory.CreateLogger<FileProtectedLicenseStore>());
    }
}

internal sealed class FileProtectedLicenseStore : ILicenseStore
{
    private static readonly JsonSerializerOptions SerializerOptions = new(JsonSerializerDefaults.Web);

    private readonly string _filePath;
    private readonly ISecretProtector _protector;
    private readonly ILogger<FileProtectedLicenseStore> _logger;

    public FileProtectedLicenseStore(string applicationName, ILogger<FileProtectedLicenseStore> logger)
    {
        _logger = logger;

        var directory = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), applicationName);
        Directory.CreateDirectory(directory);
        _filePath = Path.Combine(directory, "license.bin");

        if (OperatingSystem.IsWindows())
        {
            _protector = new DpapiSecretProtector();
        }
        else
        {
            var keyDirectory = Path.Combine(directory, "keys");
            Directory.CreateDirectory(keyDirectory);
            _protector = new AesSecretProtector(Path.Combine(keyDirectory, "license.key"), logger);
        }
    }

    public async Task<LicenseArtifact?> LoadAsync(CancellationToken ct = default)
    {
        if (!File.Exists(_filePath))
        {
            return null;
        }

        byte[]? payload = null;
        try
        {
            payload = await File.ReadAllBytesAsync(_filePath, ct).ConfigureAwait(false);
            if (payload.Length == 0)
            {
                return null;
            }

            var unprotected = _protector.Unprotect(payload);
            try
            {
                return JsonSerializer.Deserialize<LicenseArtifact>(unprotected, SerializerOptions);
            }
            finally
            {
                CryptographicOperations.ZeroMemory(unprotected);
            }
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to load the license artifact from {Path}.", _filePath);
            return null;
        }
        finally
        {
            if (payload is not null)
            {
                CryptographicOperations.ZeroMemory(payload);
            }
        }
    }

    public async Task SaveAsync(LicenseArtifact artifact, CancellationToken ct = default)
    {
        ArgumentNullException.ThrowIfNull(artifact);

        var json = JsonSerializer.SerializeToUtf8Bytes(artifact, SerializerOptions);
        var protectedBytes = Array.Empty<byte>();
        try
        {
            protectedBytes = _protector.Protect(json);
            await File.WriteAllBytesAsync(_filePath, protectedBytes, ct).ConfigureAwait(false);
        }
        finally
        {
            if (protectedBytes.Length > 0)
            {
                CryptographicOperations.ZeroMemory(protectedBytes);
            }
            CryptographicOperations.ZeroMemory(json);
        }
    }

    public Task ClearAsync(CancellationToken ct = default)
    {
        if (File.Exists(_filePath))
        {
            File.Delete(_filePath);
        }

        return Task.CompletedTask;
    }
}

internal sealed class MacKeychainLicenseStore : ILicenseStore
{
    private static readonly JsonSerializerOptions SerializerOptions = new(JsonSerializerDefaults.Web);

    private readonly string _serviceName;
    private readonly string _accountName;
    private readonly ILogger<MacKeychainLicenseStore> _logger;

    public MacKeychainLicenseStore(string applicationName, ILogger<MacKeychainLicenseStore> logger)
    {
        _serviceName = applicationName;
        _accountName = "AIInvoiceSystem-License";
        _logger = logger;
    }

    public async Task<LicenseArtifact?> LoadAsync(CancellationToken ct = default)
    {
        try
        {
            var result = await RunSecurityCommandAsync("find-generic-password", "-s", _serviceName, "-a", _accountName, "-w").ConfigureAwait(false);
            if (string.IsNullOrWhiteSpace(result))
            {
                return null;
            }

            var data = Convert.FromBase64String(result.Trim());
            var artifact = JsonSerializer.Deserialize<LicenseArtifact>(data, SerializerOptions);
            CryptographicOperations.ZeroMemory(data);
            return artifact;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to load license artifact from macOS Keychain.");
            return null;
        }
    }

    public async Task SaveAsync(LicenseArtifact artifact, CancellationToken ct = default)
    {
        ArgumentNullException.ThrowIfNull(artifact);

        var json = JsonSerializer.SerializeToUtf8Bytes(artifact, SerializerOptions);
        var encoded = Convert.ToBase64String(json);
        CryptographicOperations.ZeroMemory(json);

        try
        {
            await RunSecurityCommandAsync("delete-generic-password", "-s", _serviceName, "-a", _accountName).ConfigureAwait(false);
        }
        catch
        {
            // Ignore missing items
        }

        await RunSecurityCommandAsync("add-generic-password", "-s", _serviceName, "-a", _accountName, "-w", encoded, "-U").ConfigureAwait(false);
    }

    public async Task ClearAsync(CancellationToken ct = default)
    {
        try
        {
            await RunSecurityCommandAsync("delete-generic-password", "-s", _serviceName, "-a", _accountName).ConfigureAwait(false);
        }
        catch (Exception ex)
        {
            _logger.LogDebug(ex, "Failed to remove license artifact from macOS Keychain.");
        }
    }

    private static async Task<string> RunSecurityCommandAsync(params string[] arguments)
    {
        using var process = new Process
        {
            StartInfo = new ProcessStartInfo
            {
                FileName = "security",
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                UseShellExecute = false,
                CreateNoWindow = true,
                ArgumentList = { }
            }
        };

        foreach (var argument in arguments)
        {
            process.StartInfo.ArgumentList.Add(argument);
        }

        process.Start();
        var output = await process.StandardOutput.ReadToEndAsync().ConfigureAwait(false);
        var error = await process.StandardError.ReadToEndAsync().ConfigureAwait(false);
        await process.WaitForExitAsync().ConfigureAwait(false);

        if (process.ExitCode != 0 && !string.IsNullOrWhiteSpace(error))
        {
            throw new InvalidOperationException($"security tool returned {process.ExitCode}: {error}");
        }

        return output;
    }
}

internal interface ISecretProtector
{
    byte[] Protect(ReadOnlySpan<byte> data);
    byte[] Unprotect(ReadOnlySpan<byte> data);
}

internal sealed class DpapiSecretProtector : ISecretProtector
{
    public byte[] Protect(ReadOnlySpan<byte> data) => ProtectedData.Protect(data.ToArray(), null, DataProtectionScope.CurrentUser);

    public byte[] Unprotect(ReadOnlySpan<byte> data) => ProtectedData.Unprotect(data.ToArray(), null, DataProtectionScope.CurrentUser);
}

internal sealed class AesSecretProtector : ISecretProtector
{
    private readonly string _keyPath;
    private readonly ILogger _logger;
    private byte[]? _cachedKey;

    public AesSecretProtector(string keyPath, ILogger logger)
    {
        _keyPath = keyPath;
        _logger = logger;
    }

    public byte[] Protect(ReadOnlySpan<byte> data)
    {
        var key = GetOrCreateKey();
        using var aes = Aes.Create();
        aes.Key = key;
        aes.Mode = CipherMode.CBC;
        aes.Padding = PaddingMode.PKCS7;
        aes.GenerateIV();

        using var encryptor = aes.CreateEncryptor(aes.Key, aes.IV);
        var buffer = data.ToArray();
        try
        {
            var cipher = encryptor.TransformFinalBlock(buffer, 0, buffer.Length);
            var result = new byte[aes.IV.Length + cipher.Length];
            Buffer.BlockCopy(aes.IV, 0, result, 0, aes.IV.Length);
            Buffer.BlockCopy(cipher, 0, result, aes.IV.Length, cipher.Length);
            return result;
        }
        finally
        {
            CryptographicOperations.ZeroMemory(buffer);
        }
    }

    public byte[] Unprotect(ReadOnlySpan<byte> data)
    {
        var key = GetOrCreateKey();
        using var aes = Aes.Create();
        aes.Key = key;
        aes.Mode = CipherMode.CBC;
        aes.Padding = PaddingMode.PKCS7;

        var ivLength = aes.BlockSize / 8;
        var iv = data.Slice(0, ivLength).ToArray();
        var cipher = data.Slice(ivLength).ToArray();

        using var decryptor = aes.CreateDecryptor(aes.Key, iv);
        try
        {
            return decryptor.TransformFinalBlock(cipher, 0, cipher.Length);
        }
        finally
        {
            CryptographicOperations.ZeroMemory(iv);
            CryptographicOperations.ZeroMemory(cipher);
        }
    }

    private byte[] GetOrCreateKey()
    {
        if (_cachedKey is not null)
        {
            return _cachedKey;
        }

        if (File.Exists(_keyPath))
        {
            var existing = Convert.FromBase64String(File.ReadAllText(_keyPath));
            _cachedKey = existing;
            return existing;
        }

        Directory.CreateDirectory(Path.GetDirectoryName(_keyPath)!);
        var key = RandomNumberGenerator.GetBytes(32);
        File.WriteAllText(_keyPath, Convert.ToBase64String(key));

        try
        {
            if (OperatingSystem.IsLinux() || OperatingSystem.IsMacOS())
            {
                File.SetUnixFileMode(_keyPath, UnixFileMode.UserRead | UnixFileMode.UserWrite);
            }
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "Failed to set restrictive permissions on license key file.");
        }

        _cachedKey = key;
        return key;
    }
}
