# Code Review Checklist

This checklist guides code reviews for the disciplined process workflow.

## Review Categories

### Correctness (Blocking)

These issues MUST be fixed before merge:

- [ ] **Logic**: Does the code do what it's supposed to do?
- [ ] **Bugs**: Any obvious bugs or logic errors?
- [ ] **Edge cases**: Are boundary conditions handled?
- [ ] **Error handling**: Are errors caught and handled appropriately?
- [ ] **Tests passing**: Do all tests pass?

### Specification Compliance (Blocking in strict mode)

- [ ] **Trace markers**: Does implementation have `@trace SPEC-XX.YY` comments?
- [ ] **Test traces**: Do tests reference spec paragraph IDs?
- [ ] **Behavior match**: Does implementation match spec requirements?
- [ ] **Coverage**: Are all touched specs covered by tests?

### Performance

Flag for non-blocking issues unless on critical path:

- [ ] **Obvious issues**: No O(n²) where O(n) is trivial?
- [ ] **Data structures**: Appropriate for the use case?
- [ ] **Allocations**: No unnecessary allocations in hot paths?
- [ ] **Async**: Async/await used appropriately?

### Security

- [ ] **Secrets**: No hardcoded secrets, tokens, or credentials?
- [ ] **Input validation**: User input validated before use?
- [ ] **Injection**: No SQL, command, or other injection risks?
- [ ] **Access control**: Appropriate authorization checks?

### Code Quality

- [ ] **Readable**: Can another developer understand this easily?
- [ ] **Naming**: Are names clear and descriptive?
- [ ] **Functions**: Are functions focused and appropriately sized?
- [ ] **Duplication**: Is there obvious code that should be shared?
- [ ] **Comments**: Do comments explain "why", not "what"?

### Testing

- [ ] **Coverage**: Does new code have tests?
- [ ] **Meaningful**: Are tests validating real behavior, not just coverage?
- [ ] **Naming**: Do test names describe the behavior being tested?
- [ ] **Isolation**: Are tests properly isolated?

### Documentation

- [ ] **Public APIs**: Are public interfaces documented?
- [ ] **Complex logic**: Is non-obvious code explained?
- [ ] **ADR**: If architectural decision made, is there an ADR?

## Issue Classification

### Blocking Issues

Must be fixed before the change can be merged:

- Bugs or incorrect behavior
- Security vulnerabilities
- Missing tests for new functionality
- Spec compliance violations (in strict mode)
- Failed tests

### Non-Blocking Issues

File as tasks for later:

- Style improvements
- Refactoring opportunities
- Performance optimizations (unless critical)
- Documentation improvements
- Nice-to-have tests

## Review Output Format

Structure your review feedback as:

```
## Summary
{1-2 sentence overview}

## Blocking Issues
{File:line references with specific fixes needed}

## Non-Blocking Issues
{Suggestions for future improvement}

## Positive Observations
{What was done well - reinforce good practices}

## Recommendation
- [ ] Ready to merge
- [ ] Needs changes (address blocking issues)
```

## Best Practices

1. **Be specific**: Reference file and line numbers
2. **Explain why**: Don't just say something is wrong, explain the issue
3. **Offer solutions**: Suggest specific fixes when possible
4. **Be constructive**: Focus on the code, not the person
5. **Acknowledge good work**: Positive feedback reinforces good practices
