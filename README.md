# Disciplined Process Plugin

A rigorous, traceable AI-assisted development workflow plugin for Claude Code.

Inspired by the [Rue language](https://github.com/rue-language/rue) development process, this plugin enforces specification-first, test-driven development with full traceability.

## Prerequisites

- **Claude Code** version 2.0.0 or higher
- **Git** (for the Beads task tracker, if used)
- A project directory where you want to use the disciplined process

Check your Claude Code version:
```bash
claude --version
```

## Installation

### Step 1: Add the Plugin Repository

In Claude Code, run:
```bash
/plugin marketplace add rand/disciplined-process-plugin
```

This registers the plugin repository so you can install plugins from it.

### Step 2: Install the Plugin

```bash
/plugin install disciplined-process@disciplined-process-plugin
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
# Update the plugin repository metadata
/plugin marketplace update rand/disciplined-process-plugin

# Then update the plugin
/plugin update disciplined-process@disciplined-process-plugin
```

To check for available updates:
```bash
/plugin outdated
```

## Uninstalling

To remove the plugin:
```bash
/plugin uninstall disciplined-process@disciplined-process-plugin
```

To also remove the plugin repository:
```bash
/plugin marketplace remove rand/disciplined-process-plugin
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

## Features

- **Specification-first**: Write specs before code, with traceable paragraph IDs
- **Test-driven**: Tests reference specs, run before implementation
- **ADRs**: Document architectural decisions systematically
- **Task tracking**: Dependency-aware work management (Beads default, pluggable)
- **Traceability**: Every line links to specs via `@trace` markers
- **Enforcement**: Configurable hooks enforce the process (or just guide)

See [disciplined-process-plugin/README.md](./disciplined-process-plugin/README.md) for full documentation.

## Repository Structure

```
disciplined-process-plugin/
├── .claude-plugin/
│   └── marketplace.json        # Plugin registry manifest
├── disciplined-process-plugin/ # Plugin implementation
│   ├── .claude-plugin/
│   │   └── plugin.json         # Plugin metadata
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

- **Issues**: [GitHub Issues](https://github.com/rand/disciplined-process-plugin/issues)
- **Discussions**: [GitHub Discussions](https://github.com/rand/disciplined-process-plugin/discussions)
