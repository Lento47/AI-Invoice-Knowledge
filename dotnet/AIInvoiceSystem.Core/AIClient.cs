using System.Collections.Generic;
using System.Net.Http.Json;

namespace AIInvoiceSystem.Core;

public sealed class AIClient(HttpClient http)
{
    public async Task<InvoiceExtractionDto?> ExtractAsync(Stream file, string fileName, CancellationToken ct = default)
    {
        using var content = new MultipartFormDataContent();
        content.Add(new StreamContent(file), "file", fileName);
        var response = await http.PostAsync("/extract", content, ct);
        response.EnsureSuccessStatusCode();
        return await response.Content.ReadFromJsonAsync<InvoiceExtractionDto>(cancellationToken: ct);
    }

    public async Task<ClassificationResultDto?> ClassifyAsync(string text, CancellationToken ct = default)
    {
        var response = await http.PostAsJsonAsync("/classify", new { text }, ct);
        response.EnsureSuccessStatusCode();
        return await response.Content.ReadFromJsonAsync<ClassificationResultDto>(cancellationToken: ct);
    }

    public async Task<PredictiveResultDto?> PredictAsync(object features, CancellationToken ct = default)
    {
        var response = await http.PostAsJsonAsync("/predict", features, ct);
        response.EnsureSuccessStatusCode();
        return await response.Content.ReadFromJsonAsync<PredictiveResultDto>(cancellationToken: ct);
    }
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
