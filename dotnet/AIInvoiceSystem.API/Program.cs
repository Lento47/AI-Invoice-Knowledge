using AIInvoiceSystem.Core;
using Polly;
using Polly.Extensions.Http;
using System.Net.Http;

static IAsyncPolicy<HttpResponseMessage> RetryPolicy() =>
    HttpPolicyExtensions
        .HandleTransientHttpError()
        .OrResult(msg => (int)msg.StatusCode == 429)
        .WaitAndRetryAsync(3, retry => TimeSpan.FromMilliseconds(200 * Math.Pow(2, retry)));

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddControllers();
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();

builder.Services
    .AddHttpClient<AIClient>(client =>
    {
        client.BaseAddress = new Uri("http://127.0.0.1:8088");
        client.Timeout = TimeSpan.FromSeconds(20);

        // Propagate API key to FastAPI if configured
        var apiKey = Environment.GetEnvironmentVariable("AI_API_KEY") ?? string.Empty;
        if (!string.IsNullOrWhiteSpace(apiKey))
        {
            client.DefaultRequestHeaders.Add("X-API-Key", apiKey);
        }
    })
    .AddPolicyHandler(RetryPolicy());

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
