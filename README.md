# Disciplined Process Marketplace

A Claude Code plugin marketplace for rigorous AI-assisted development workflows.

## Prerequisites

- **Claude Code** version 2.0.0 or higher
- **Git** (for the Beads task tracker, if used)
- A project directory where you want to use the disciplined process

Check your Claude Code version:
```bash
claude --version
```

## Installation

### Step 1: Add the Marketplace

In Claude Code, run:
```bash
/plugin marketplace add rand/disciplined-process-marketplace
```

This registers the marketplace so you can install plugins from it.

### Step 2: Install the Plugin

```bash
/plugin install disciplined-process@disciplined-process-marketplace
```

### Step 3: Verify Installation

Confirm the plugin is installed:
```bash
/plugin list
```

You should see `disciplined-process` in the list of installed plugins.

### Step 4: Initialize Your Project

Navigate to your project directory and run:
```bash
/dp:init
```

This launches an interactive wizard that will:
1. Detect your project language
2. Configure task tracking (Beads recommended)
3. Set up test frameworks
4. Choose enforcement level (strict/guided/minimal)
5. Create all necessary files and directories

### Step 5: Validate Setup

After initialization, verify everything is working:

```bash
# Check the plugin help works
/dp:help

# View your configuration
cat .claude/dp-config.yaml

# If using Beads task tracking, verify it's initialized
bd stats
```

You should see the help output and your configuration file.

## Quick Start After Installation

```bash
# See available work
/dp:task ready

# Create your first specification
/dp:spec create 01-core "Core Functionality"

# Start the workflow
/dp:help workflow
```

## Updating the Plugin

When a new version is released:

```bash
# Update the marketplace first
/plugin marketplace update rand/disciplined-process-marketplace

# Then update the plugin
/plugin update disciplined-process@disciplined-process-marketplace
```

To check for available updates:
```bash
/plugin outdated
```

## Uninstalling

To remove the plugin:
```bash
/plugin uninstall disciplined-process@disciplined-process-marketplace
```

To also remove the marketplace:
```bash
/plugin marketplace remove rand/disciplined-process-marketplace
```

Note: Uninstalling the plugin does not remove files created by `/dp:init` in your projects (configs, specs, ADRs, etc.). Remove those manually if needed.

## Troubleshooting

### "Command not found" after installation

1. Verify the plugin is installed: `/plugin list`
2. Try restarting Claude Code
3. Re-run the installation command

### Wizard doesn't detect my language

The wizard checks for `package.json`, `Cargo.toml`, `pyproject.toml`, `go.mod`, and `build.zig`. If your project uses a different setup, select "other" when prompted.

### Hooks not running

1. Check that `.claude/settings.json` was created
2. Verify your enforcement level isn't set to "minimal" (which disables hooks)
3. Review hook configuration: `cat .claude/settings.json`

### Beads task tracker issues

If `bd` commands fail:
1. Ensure `.beads/` directory exists
2. Run `bd init` manually if needed
3. Check git is initialized in your project

### Permission errors on scripts

The plugin scripts need execute permissions:
```bash
chmod +x .claude/scripts/*.sh
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

See [disciplined-process-plugin/README.md](./disciplined-process-plugin/README.md) for full documentation.

## Repository Structure

```
disciplined-process-marketplace/
├── .claude-plugin/
│   └── marketplace.json        # Marketplace manifest
├── disciplined-process-plugin/ # The main plugin
│   ├── .claude-plugin/
│   │   └── plugin.json
│   ├── commands/               # /dp:* commands
│   ├── agents/                 # Code review agent
│   ├── skills/                 # Auto-invoked skills
│   ├── hooks/                  # Process enforcement
│   ├── scripts/                # Hook implementations
│   ├── references/             # Configuration docs
│   └── assets/                 # Templates
└── README.md
```

## License

MIT

## Contributing

Contributions welcome! Please follow the disciplined process (naturally).

## Support

- **Issues**: [GitHub Issues](https://github.com/rand/disciplined-process-marketplace/issues)
- **Discussions**: [GitHub Discussions](https://github.com/rand/disciplined-process-marketplace/discussions)
