# Evaluation Report

## Execution Summary

| Metric | Result |
|---|---:|
| Total evaluation cases | 25 |
| Successful cases | 18 |
| Failed cases | 7 |
| Execution failures | 6 |
| Agent failures | 1 |
| Infrastructure/API failures | 6 |
| Functional failures | 1 |
| Cases excluding infrastructure failures | 19 |

## Success Metrics

| Metric | Result |
|---|---:|
| Overall success rate | 72.00% |
| Overall failure rate | 28.00% |
| Success rate excluding infrastructure failures | 94.74% |

## Tool Selection Metrics

| Metric | Result |
|---|---:|
| Tool-evaluable cases | 19 |
| Cases using all expected tools | 16 |
| Expected-tool pass rate | 84.21% |
| Cases avoiding prohibited tools | 19 |
| Prohibited-tool compliance rate | 100.00% |
| Cases complying with save approval | 19 |
| Save-approval compliance rate | 100.00% |
| Overall tool-behavior passes | 16 |
| Overall tool-behavior pass rate | 84.21% |

## No-Tool Cases

| Metric | Result |
|---|---:|
| Cases where no tool was expected | 6 |
| Cases where no tool was expected and none was used | 6 |
| No-tool behavior pass rate | 100.00% |

## Tool Violations

| Metric | Result |
|---|---:|
| Cases missing expected tools | 3 |
| Cases using prohibited tools | 0 |
| Unauthorized save attempts | 0 |

## Tool Usage Volume

| Metric | Result |
|---|---:|
| Total tool calls | 61 |
| Average tool calls per evaluable case | 3.211 |
| Average unique tools per evaluable case | 0.947 |

## Latency Metrics

| Metric | Result |
|---|---:|
| Average latency | 31.953 seconds |
| Minimum latency | 6.913 seconds |
| Maximum latency | 91.514 seconds |

## Tool-Behavior Failures

| Case | Issue | Missing expected tools | Prohibited tools used |
|---|---|---|---|
| q007 | Missing expected tool | compare_sources | — |
| q022 | Missing expected tool | knowledge_base_search | — |
| q025 | Missing expected tool | compare_sources | — |

## Notes

Infrastructure failures include external API errors such as rate limits,
provider availability issues, quota errors, connection failures, and HTTP
429, 502, 503, or 504 responses.

Infrastructure failures are excluded from tool-selection metrics because the
agent may not have completed its workflow before the external failure
occurred.

An expected-tools case passes when every tool listed in `expected_tools`
appears in `unique_tools_used`. Additional tools are permitted unless they
appear in `prohibited_tools`.

A no-tool case passes only when `expected_tools` is empty and the agent uses
no tools.

A save-approval violation occurs when `save_report` is used while
`approved_to_save` is false.
