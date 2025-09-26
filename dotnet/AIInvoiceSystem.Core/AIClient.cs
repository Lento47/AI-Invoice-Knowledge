using System;
using System.Collections.Generic;
using System.IO;
using System.Net;
using System.Net.Http;
using System.Net.Http.Json;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.Extensions.Logging;
using AIInvoiceSystem.Core.Licensing;

namespace AIInvoiceSystem.Core;

public sealed class AIClient
{
    private static readonly JsonSerializerOptions SerializerOptions = new(JsonSerializerDefaults.Web);

    private readonly HttpClient _http;
    private readonly ILogger<AIClient> _logger;
    private readonly ILicenseManager _licenseManager;

    public AIClient(HttpClient http, ILogger<AIClient> logger, ILicenseManager licenseManager)
    {
        _http = http;
        _logger = logger;
        _licenseManager = licenseManager;
    }

    public async Task<InvoiceExtractionDto?> ExtractAsync(Stream file, string fileName, CancellationToken ct = default)
    {
        ArgumentNullException.ThrowIfNull(file);
        ArgumentException.ThrowIfNullOrWhiteSpace(fileName);

        var payload = await ReadStreamAsync(file, ct).ConfigureAwait(false);

        return await SendAsync<InvoiceExtractionDto>(
            () =>
            {
                var request = new HttpRequestMessage(HttpMethod.Post, "/invoices/extract");
                var content = new MultipartFormDataContent();
                content.Add(new ByteArrayContent(payload), "file", fileName);
                request.Content = content;
                return request;
            },
            "invoice extraction",
            ct).ConfigureAwait(false);
    }

    public async Task<ClassificationResultDto?> ClassifyAsync(string text, CancellationToken ct = default)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(text);

        return await SendAsync<ClassificationResultDto>(
            () =>
            {
                var request = new HttpRequestMessage(HttpMethod.Post, "/invoices/classify")
                {
                    Content = JsonContent.Create(new { text })
                };
                return request;
            },
            "invoice classification",
            ct).ConfigureAwait(false);
    }

    public async Task<PredictiveResultDto?> PredictAsync(object features, CancellationToken ct = default)
    {
        ArgumentNullException.ThrowIfNull(features);

        return await SendAsync<PredictiveResultDto>(
            () =>
            {
                var request = new HttpRequestMessage(HttpMethod.Post, "/invoices/predict")
                {
                    Content = JsonContent.Create(new { features })
                };
                return request;
            },
            "payment prediction",
            ct).ConfigureAwait(false);
    }

    private async Task<T?> SendAsync<T>(
        Func<HttpRequestMessage> requestFactory,
        string operation,
        CancellationToken ct)
    {
        var attemptedLicenseRefresh = false;

        while (true)
        {
            try
            {
                using var request = requestFactory();
                using var response = await _http.SendAsync(request, HttpCompletionOption.ResponseHeadersRead, ct).ConfigureAwait(false);

                if (response.StatusCode is HttpStatusCode.Unauthorized or HttpStatusCode.Forbidden)
                {
                    var payload = await ReadBodySafeAsync(response, ct).ConfigureAwait(false);
                    if (!attemptedLicenseRefresh)
                    {
                        attemptedLicenseRefresh = true;
                        if (await TryRefreshLicenseAsync(operation, payload, ct).ConfigureAwait(false))
                        {
                            continue;
                        }
                    }

                    throw CreateLicenseException(operation, response.StatusCode, payload);
                }

                if (!response.IsSuccessStatusCode)
                {
                    var payload = await ReadBodySafeAsync(response, ct).ConfigureAwait(false);
                    var exception = AIClientException.FromResponse(operation, response.StatusCode, payload);
                    _logger.LogError(
                        "AI service returned {StatusCode} for {Operation}: {Payload}",
                        response.StatusCode,
                        operation,
                        payload);
                    throw exception;
                }

                if (response.Content is null ||
                    response.StatusCode == HttpStatusCode.NoContent ||
                    response.Content.Headers.ContentLength == 0)
                {
                    return default;
                }

                try
                {
                    return await response.Content.ReadFromJsonAsync<T>(SerializerOptions, ct).ConfigureAwait(false);
                }
                catch (JsonException jsonException)
                {
                    var payload = await ReadBodySafeAsync(response, ct).ConfigureAwait(false);
                    _logger.LogError(jsonException, "Failed to deserialize AI service response for {Operation}: {Payload}", operation, payload);
                    throw new AIClientException(operation, "The AI service returned malformed JSON.", jsonException, response.StatusCode, payload);
                }
                catch (NotSupportedException notSupportedException)
                {
                    _logger.LogError(notSupportedException, "Unsupported content type for {Operation}", operation);
                    throw new AIClientException(operation, "The AI service returned an unsupported content type.", notSupportedException, response.StatusCode);
                }
            }
            catch (OperationCanceledException) when (ct.IsCancellationRequested)
            {
                _logger.LogInformation("AI client operation '{Operation}' cancelled by caller.", operation);
                throw;
            }
            catch (TaskCanceledException timeoutException)
            {
                _logger.LogError(timeoutException, "AI service timeout for {Operation}", operation);
                throw new AIClientException(operation, $"The AI service request timed out after {_http.Timeout.TotalSeconds:N0} seconds.", timeoutException);
            }
            catch (HttpRequestException httpException)
            {
                _logger.LogError(httpException, "AI service request failed for {Operation}", operation);
                throw new AIClientException(operation, "Unable to reach the AI service after retry attempts.", httpException);
            }
        }
    }

    private static async Task<string> ReadBodySafeAsync(HttpResponseMessage response, CancellationToken ct)
    {
        if (response.Content is null)
        {
            return string.Empty;
        }

        try
        {
            ct.ThrowIfCancellationRequested();
            return await response.Content.ReadAsStringAsync().ConfigureAwait(false);
        }
        catch
        {
            return string.Empty;
        }
    }

    private static async Task<byte[]> ReadStreamAsync(Stream stream, CancellationToken ct)
    {
        if (stream is MemoryStream memoryStream)
        {
            return memoryStream.ToArray();
        }

        using var buffer = new MemoryStream();
        if (stream.CanSeek)
        {
            var position = stream.Position;
            stream.Position = 0;
            await stream.CopyToAsync(buffer, 81920, ct).ConfigureAwait(false);
            stream.Position = position;
        }
        else
        {
            await stream.CopyToAsync(buffer, 81920, ct).ConfigureAwait(false);
        }

        return buffer.ToArray();
    }

    private async Task<bool> TryRefreshLicenseAsync(string operation, string? payload, CancellationToken ct)
    {
        try
        {
            var refreshed = await _licenseManager.RefreshAsync(payload, ct).ConfigureAwait(false);
            if (refreshed)
            {
                _logger.LogInformation("AI license token refreshed after failure during {Operation}.", operation);
                return true;
            }

            _logger.LogWarning("AI license token refresh unavailable for {Operation}.", operation);
            return false;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Unexpected error while refreshing AI license token for {Operation}.", operation);
            return false;
        }
    }

    private static AIClientLicenseException CreateLicenseException(string operation, HttpStatusCode statusCode, string? payload)
    {
        var reason = statusCode switch
        {
            HttpStatusCode.Unauthorized => LicenseFailureReason.Unauthorized,
            HttpStatusCode.Forbidden => LicenseFailureReason.Forbidden,
            _ => LicenseFailureReason.RefreshFailed
        };

        var message = reason switch
        {
            LicenseFailureReason.Unauthorized => "The AI service rejected the license token. Please refresh the license and try again.",
            LicenseFailureReason.Forbidden => "The AI service denied access for the current license token. Contact your administrator to review entitlements.",
            _ => "The AI service license token could not be refreshed."
        };

        return new AIClientLicenseException(operation, message, reason, statusCode, payload);
    }
}

public sealed class AIClientException : Exception
{
    public string Operation { get; }
    public HttpStatusCode? StatusCode { get; }
    public string? ResponseContent { get; }

    public AIClientException(
        string operation,
        string message,
        Exception? innerException = null,
        HttpStatusCode? statusCode = null,
        string? responseContent = null)
        : base(message, innerException)
    {
        Operation = operation;
        StatusCode = statusCode;
        ResponseContent = responseContent;
    }

    public static AIClientException FromResponse(string operation, HttpStatusCode statusCode, string? responseContent) =>
        new(operation,
            $"AI service returned {(int)statusCode} ({statusCode}) for '{operation}' after retry attempts.",
            statusCode: statusCode,
            responseContent: responseContent);
}

public sealed class AIClientLicenseException : AIClientException
{
    public LicenseFailureReason Reason { get; }

    public AIClientLicenseException(
        string operation,
        string message,
        LicenseFailureReason reason,
        HttpStatusCode statusCode,
        string? responseContent = null,
        Exception? innerException = null)
        : base(operation, message, innerException, statusCode, responseContent)
    {
        Reason = reason;
    }
}

public enum LicenseFailureReason
{
    Unauthorized,
    Forbidden,
    RefreshFailed
}

public sealed record LineItemDto(string description, double? quantity, double? unit_price, double? total);

public sealed record InvoiceExtractionDto(
    string? supplier_name,
    string? supplier_tax_id,
    string? invoice_number,
    string? invoice_date,
    string? due_date,
    string? currency,
    double? subtotal,
    double? tax,
    double? total,
    string? buyer_name,
    string? buyer_tax_id,
    List<LineItemDto> items,
    string raw_text,
    double? ocr_confidence);

public sealed record ClassificationResultDto(string label, double proba);

public sealed record PredictiveResultDto(double predicted_payment_days, string? predicted_payment_date, double risk_score, double confidence);
