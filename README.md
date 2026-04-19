# oh-my-ccstatusline
claude code colorful statusline

A colorful Claude Code status line inspired by island_breeze aesthetics and the Catppuccin Mocha palette.

It is designed to keep the most useful session information visible without turning the status line into a wall of text.

## Features

- Colorful two-line Claude Code status line
- Compact context usage badge with progress dots
- Cost, duration, and clock badges
- Token, cache, and API wait stats
- Git branch and working tree status
- Catppuccin-inspired colors with an island_breeze feel
- Simple single-file Python script

## Preview

<img width="1453" height="148" alt="image" src="https://github.com/user-attachments/assets/baa93122-aabb-43cc-92b7-b47c187e47b1" />


## Requirements

- Claude Code
- Python 3
- A terminal with true color support
- A Nerd Font-compatible terminal font for icons such as `` and ``
- `git` available in `PATH` if you want git status information

## Installation

1. Copy `island_breeze_statusline.py` to your Claude directory:

```bash
cp island_breeze_statusline.py ~/.claude/island_breeze_statusline.py
```

2. Add this to `~/.claude/settings.json`:

```json
{
  "statusLine": {
    "type": "command",
    "command": "python3 ~/.claude/island_breeze_statusline.py",
    "padding": 1,
    "refreshInterval": 2
  }
}
```

If your `settings.json` already contains other keys, merge the `statusLine` block into the existing file instead of replacing it.

Example:

```json
{
  "enabledPlugins": {
    "superpowers@claude-plugins-official": true
  },
  "extraKnownMarketplaces": {
    "superpowers-marketplace": {
      "source": {
        "source": "github",
        "repo": "obra/superpowers-marketplace"
      }
    }
  },
  "model": "opus[1m]",
  "statusLine": {
    "type": "command",
    "command": "python3 ~/.claude/island_breeze_statusline.py",
    "padding": 1,
    "refreshInterval": 2
  }
}
```

## What it shows

### First line

- Claude model
- Context window size label
- Claude Code version
- Current working directory
- Context usage badge
- Total session cost
- Total session duration
- Git branch and working tree summary when available
- Clock

### Second line

- Cache hit rate
- Total input and output tokens
- Total API wait time
- Current input, cache read, and cache write token stats

## Git indicators

When the current directory is inside a git repository, the status line can show:

- ` branch-name`
- `+N` staged changes
- `!N` modified files
- `>N` renamed files
- `xN` deleted files
- `?N` untracked files
- `=N` conflicted files
- `⇡N` commits ahead of upstream
- `⇣N` commits behind upstream

## Customization

The color palette is defined near the top of the script in the `PALETTE` dictionary.

You can tweak:

- badge colors
- text colors
- progress dot colors
- git colors
- timing and token colors

You can also adjust refresh frequency here:

```json
"refreshInterval": 2
```

## Notes

- Git info is cached briefly to keep the status line responsive.
- If icons do not render correctly, switch to a Nerd Font-enabled terminal font.
- If the status line does not appear, verify that `python3 ~/.claude/island_breeze_statusline.py` runs successfully.

## License

MIT
