// Self-hosted (global) Renovate config, consumed by .github/workflows/renovate.yml.
//
// This is distinct from .github/renovate.json5: that one holds the *repository*
// rules (what to update, how to group, when). This one holds settings that only
// make sense for the runner itself and that a repo config is not permitted to set.

module.exports = {
  platform: "github",
  repositories: ["jack06215/monorepo"],

  // Post-upgrade commands are refused unless they match one of these regexes.
  // Renovate deliberately makes this global-only so a repo config can never
  // grant itself arbitrary command execution.
  //
  // Option name confirmed against docs.renovatebot.com/self-hosted-configuration
  // (July 2026). Formerly `allowedPostUpgradeCommands`; if you ever pin an older
  // Renovate that predates the rename, this silently no-ops and requirements.txt
  // stops being regenerated.
  allowedCommands: ["^poetry (self add poetry-plugin-export|export) ?.*$"],

  // A config file is already committed, so skip the onboarding PR entirely.
  onboarding: false,
  requireConfig: "required",
};
