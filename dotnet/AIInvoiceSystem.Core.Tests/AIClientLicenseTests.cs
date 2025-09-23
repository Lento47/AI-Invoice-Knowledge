using System.Net;
using System.Net.Http;
using System.Net.Http.Json;
using AIInvoiceSystem.Core;
using AIInvoiceSystem.Core.Licensing;
using Microsoft.Extensions.Logging.Abstractions;
using Xunit;

namespace AIInvoiceSystem.Core.Tests;

public sealed class AIClientLicenseTests
{
    [Fact]
    public async Task SendsLicenseTokenForSuccessfulRequests()
    {
        var store = new InMemoryLicenseStore(new LicenseArtifact("stored-token"));
        var refresher = new TestLicenseRefresher();
        using var manager = new LicenseManager(store, refresher, NullLogger<LicenseManager>.Instance);
        await manager.InitializeAsync();

        var handler = new TestHttpMessageHandler((request, _) =>
        {
            Assert.True(request.Headers.TryGetValues(LicenseHttpMessageHandler.LicenseHeaderName, out var values));
            Assert.Equal("stored-token", Assert.Single(values));

            var response = new HttpResponseMessage(HttpStatusCode.OK)
            {
                Content = JsonContent.Create(new ClassificationResultDto("invoice", 0.95))
            };
            return Task.FromResult(response);
        });

        var licenseHandler = new LicenseHttpMessageHandler(manager, NullLogger<LicenseHttpMessageHandler>.Instance)
        {
            InnerHandler = handler
        };

        var httpClient = new HttpClient(licenseHandler)
        {
            BaseAddress = new Uri("http://localhost")
        };

        var client = new AIClient(httpClient, NullLogger<AIClient>.Instance, manager);

        var result = await client.ClassifyAsync("content");

        Assert.NotNull(result);
        Assert.Equal("invoice", result!.label);
        Assert.Equal(0.95, result.proba);
        Assert.Equal(1, handler.CallCount);
    }

    [Fact]
    public async Task RefreshesLicenseAfterUnauthorizedResponse()
    {
        var store = new InMemoryLicenseStore(new LicenseArtifact("expired-token"));
        var refresher = new TestLicenseRefresher(new[] { new LicenseArtifact("renewed-token") });
        using var manager = new LicenseManager(store, refresher, NullLogger<LicenseManager>.Instance);
        await manager.InitializeAsync();

        var call = 0;
        var handler = new TestHttpMessageHandler((request, _) =>
        {
            call++;
            Assert.True(request.Headers.TryGetValues(LicenseHttpMessageHandler.LicenseHeaderName, out var values));
            var header = Assert.Single(values);

            if (call == 1)
            {
                Assert.Equal("expired-token", header);
                return Task.FromResult(new HttpResponseMessage(HttpStatusCode.Unauthorized)
                {
                    Content = new StringContent("expired")
                });
            }

            Assert.Equal("renewed-token", header);
            return Task.FromResult(new HttpResponseMessage(HttpStatusCode.OK)
            {
                Content = JsonContent.Create(new ClassificationResultDto("invoice", 0.85))
            });
        });

        var licenseHandler = new LicenseHttpMessageHandler(manager, NullLogger<LicenseHttpMessageHandler>.Instance)
        {
            InnerHandler = handler
        };

        var httpClient = new HttpClient(licenseHandler)
        {
            BaseAddress = new Uri("http://localhost")
        };

        var client = new AIClient(httpClient, NullLogger<AIClient>.Instance, manager);

        var result = await client.ClassifyAsync("content");

        Assert.NotNull(result);
        Assert.Equal("invoice", result!.label);
        Assert.Equal(0.85, result.proba);
        Assert.Equal(2, handler.CallCount);
        Assert.Equal("renewed-token", (await manager.GetTokenAsync())!);
        Assert.Single(refresher.Calls);
    }

    [Fact]
    public async Task ThrowsLicenseExceptionWhenRefreshUnavailable()
    {
        var store = new InMemoryLicenseStore(new LicenseArtifact("revoked-token"));
        var refresher = new TestLicenseRefresher();
        using var manager = new LicenseManager(store, refresher, NullLogger<LicenseManager>.Instance);
        await manager.InitializeAsync();

        var handler = new TestHttpMessageHandler((request, _) =>
        {
            Assert.True(request.Headers.TryGetValues(LicenseHttpMessageHandler.LicenseHeaderName, out var values));
            var header = Assert.Single(values);
            Assert.Equal("revoked-token", header);

            return Task.FromResult(new HttpResponseMessage(HttpStatusCode.Forbidden)
            {
                Content = new StringContent("revoked")
            });
        });

        var licenseHandler = new LicenseHttpMessageHandler(manager, NullLogger<LicenseHttpMessageHandler>.Instance)
        {
            InnerHandler = handler
        };

        var httpClient = new HttpClient(licenseHandler)
        {
            BaseAddress = new Uri("http://localhost")
        };

        var client = new AIClient(httpClient, NullLogger<AIClient>.Instance, manager);

        var exception = await Assert.ThrowsAsync<AIClientLicenseException>(() => client.PredictAsync(new { foo = "bar" }));

        Assert.Equal(LicenseFailureReason.Forbidden, exception.Reason);
        Assert.Equal(HttpStatusCode.Forbidden, exception.StatusCode);
        Assert.Equal(1, handler.CallCount);
        Assert.Single(refresher.Calls);
    }

    private sealed class TestHttpMessageHandler : HttpMessageHandler
    {
        private readonly Func<HttpRequestMessage, CancellationToken, Task<HttpResponseMessage>> _handler;

        public int CallCount { get; private set; }

        public TestHttpMessageHandler(Func<HttpRequestMessage, CancellationToken, Task<HttpResponseMessage>> handler)
        {
            _handler = handler;
        }

        protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken)
        {
            CallCount++;
            return _handler(request, cancellationToken);
        }
    }

    private sealed class InMemoryLicenseStore : ILicenseStore
    {
        private LicenseArtifact? _artifact;

        public InMemoryLicenseStore(LicenseArtifact? artifact = null)
        {
            _artifact = artifact;
        }

        public Task<LicenseArtifact?> LoadAsync(CancellationToken ct = default) => Task.FromResult(_artifact);

        public Task SaveAsync(LicenseArtifact artifact, CancellationToken ct = default)
        {
            _artifact = artifact;
            return Task.CompletedTask;
        }

        public Task ClearAsync(CancellationToken ct = default)
        {
            _artifact = null;
            return Task.CompletedTask;
        }
    }

    private sealed class TestLicenseRefresher : ILicenseRefresher
    {
        private readonly Queue<LicenseArtifact?> _responses;

        public List<(LicenseArtifact? current, string? payload)> Calls { get; } = new();

        public TestLicenseRefresher(IEnumerable<LicenseArtifact?>? responses = null)
        {
            _responses = new Queue<LicenseArtifact?>(responses ?? Array.Empty<LicenseArtifact?>());
        }

        public Task<LicenseArtifact?> RefreshAsync(LicenseArtifact? current, string? failurePayload, CancellationToken ct = default)
        {
            Calls.Add((current, failurePayload));
            return Task.FromResult(_responses.Count > 0 ? _responses.Dequeue() : null);
        }
    }
}
