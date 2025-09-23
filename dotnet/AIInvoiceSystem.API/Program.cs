using AIInvoiceSystem.Core;
using Microsoft.Extensions.Logging;
using Polly;
using Polly.Extensions.Http;
using System.Net;
using System.Net.Http;

const string aiClientSectionName = "AIClient";

var builder = WebApplication.CreateBuilder(args);

var aiClientSection = builder.Configuration.GetSection(aiClientSectionName);
var baseAddressConfig = aiClientSection.GetValue<string?>("BaseAddress");
var retryCount = Math.Max(1, aiClientSection.GetValue<int?>("RetryCount") ?? 3);
var retryBaseDelaySeconds = Math.Max(0.5, aiClientSection.GetValue<double?>("RetryBaseDelaySeconds") ?? 1.0);
var timeoutSeconds = Math.Max(5, aiClientSection.GetValue<int?>("TimeoutSeconds") ?? 30);

var baseAddress = Uri.TryCreate(baseAddressConfig, UriKind.Absolute, out var parsedUri)
    ? parsedUri
    : new Uri("http://localhost:8088");

builder.Services.AddControllers();
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();
builder.Services
    .AddHttpClient<AIClient>(client =>
    {
        client.BaseAddress = baseAddress;
        client.Timeout = TimeSpan.FromSeconds(timeoutSeconds);
    })
    .SetHandlerLifetime(TimeSpan.FromMinutes(5))
    .ConfigurePrimaryHttpMessageHandler(() => new HttpClientHandler
    {
        AutomaticDecompression = DecompressionMethods.All
    })
    .AddPolicyHandler((services, request) =>
    {
        var logger = services.GetRequiredService<ILogger<AIClient>>();

        return HttpPolicyExtensions
            .HandleTransientHttpError()
            .OrResult(response => response.StatusCode == HttpStatusCode.RequestTimeout)
            .WaitAndRetryAsync(
                retryCount,
                retryAttempt =>
                {
                    var exponent = Math.Pow(2, retryAttempt - 1);
                    var jitterSeconds = Random.Shared.NextDouble();
                    return TimeSpan.FromSeconds((retryBaseDelaySeconds * exponent) + jitterSeconds);
                },
                (outcome, delay, attempt, context) =>
                {
                    var requestUri = outcome.Result?.RequestMessage?.RequestUri?.ToString()
                        ?? request.RequestUri?.ToString()
                        ?? "unknown";

                    var reason = outcome.Exception?.Message
                        ?? outcome.Result?.ReasonPhrase
                        ?? outcome.Result?.StatusCode.ToString();

                    logger.LogWarning(
                        outcome.Exception,
                        "Retry {Attempt}/{MaxAttempts} for {RequestUri} after {Delay}. Reason: {Reason}",
                        attempt,
                        retryCount,
                        requestUri,
                        delay,
                        reason);
                });
    });

var app = builder.Build();

if (app.Environment.IsDevelopment())
{
    app.UseSwagger();
    app.UseSwaggerUI();
}

app.UseHttpsRedirection();
app.UseAuthorization();
app.MapControllers();

app.Run();
