# Disciplined Process Marketplace

A Claude Code plugin marketplace for rigorous AI-assisted development workflows.

## Installation

```bash
# Add this marketplace to Claude Code
/plugin marketplace add rand/disciplined-process-marketplace

# Install the plugin
/plugin install disciplined-process@disciplined-process-marketplace
```

## Available Plugins

### disciplined-process

A rigorous, traceable AI-assisted development workflow inspired by the [Rue language](https://github.com/rue-language/rue) project.

**Features:**
- Specification-first development with traceable paragraph IDs
- Test-driven development with four test types (unit, integration, property, e2e)
- Architecture Decision Records (ADRs)
- Pluggable task tracking (Beads, GitHub Issues, Linear, Markdown)
- Configurable enforcement (strict, guided, minimal)
- Hooks for process enforcement

**Quick Start:**
```bash
/dp:init
```

See [disciplined-process-plugin/README.md](./disciplined-process-plugin/README.md) for full documentation.

## Structure

```
disciplined-process-marketplace/
├── .claude-plugin/
│   └── marketplace.json        # Marketplace manifest
├── disciplined-process-plugin/ # The main plugin
│   ├── .claude-plugin/
│   │   └── plugin.json
│   ├── commands/
│   ├── agents/
│   ├── skills/
│   ├── hooks/
│   ├── scripts/
│   ├── references/
│   └── assets/
└── README.md
```

## License

MIT

## Contributing

Contributions welcome! Please follow the disciplined process (naturally).
