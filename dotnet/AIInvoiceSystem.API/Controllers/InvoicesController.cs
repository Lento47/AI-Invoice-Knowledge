using AIInvoiceSystem.Core;
using Microsoft.AspNetCore.Mvc;

namespace AIInvoiceSystem.API.Controllers;

[ApiController]
[Route("api/[controller]")]
public class InvoicesController(AIClient aiClient) : ControllerBase
{
    private readonly AIClient _aiClient = aiClient;

    [HttpPost("classify")]
    public async Task<ActionResult<ClassificationResultDto?>> Classify([FromBody] ClassificationRequest request, CancellationToken ct)
    {
        var result = await _aiClient.ClassifyAsync(request.Text, ct);
        return Ok(result);
    }

    [HttpPost("predict")]
    public async Task<ActionResult<PredictiveResultDto?>> Predict([FromBody] object features, CancellationToken ct)
    {
        var result = await _aiClient.PredictAsync(features, ct);
        return Ok(result);
    }
}

public sealed record ClassificationRequest(string Text);
