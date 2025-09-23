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

namespace AIInvoiceSystem.Core;

public sealed class AIClient
{
    private static readonly JsonSerializerOptions SerializerOptions = new(JsonSerializerDefaults.Web);

    private readonly HttpClient _http;
    private readonly ILogger<AIClient> _logger;

    public AIClient(HttpClient http, ILogger<AIClient> logger)
    {
        _http = http;
        _logger = logger;
    }

    public async Task<InvoiceExtractionDto?> ExtractAsync(Stream file, string fileName, CancellationToken ct = default)
    {
        ArgumentNullException.ThrowIfNull(file);
        ArgumentException.ThrowIfNullOrWhiteSpace(fileName);

        using var content = new MultipartFormDataContent();
        var streamContent = new StreamContent(file);
        content.Add(streamContent, "file", fileName);

        return await SendAsync<InvoiceExtractionDto>(
            cancellationToken => _http.PostAsync("/invoices/extract", content, cancellationToken),
            "invoice extraction",
            ct).ConfigureAwait(false);
    }

    public async Task<ClassificationResultDto?> ClassifyAsync(string text, CancellationToken ct = default)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(text);

        return await SendAsync<ClassificationResultDto>(
            cancellationToken => _http.PostAsJsonAsync("/invoices/classify", new { text }, cancellationToken),
            "invoice classification",
            ct).ConfigureAwait(false);
    }

    public async Task<PredictiveResultDto?> PredictAsync(object features, CancellationToken ct = default)
    {
        ArgumentNullException.ThrowIfNull(features);

        return await SendAsync<PredictiveResultDto>(
            cancellationToken => _http.PostAsJsonAsync("/invoices/predict", new { features }, cancellationToken),
            "payment prediction",
            ct).ConfigureAwait(false);
    }

    private async Task<T?> SendAsync<T>(
        Func<CancellationToken, Task<HttpResponseMessage>> send,
        string operation,
        CancellationToken ct)
    {
        try
        {
            using var response = await send(ct).ConfigureAwait(false);

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
    string raw_text);

public sealed record ClassificationResultDto(string label, double proba);

public sealed record PredictiveResultDto(double predicted_payment_days, string? predicted_payment_date, double risk_score, double confidence);
