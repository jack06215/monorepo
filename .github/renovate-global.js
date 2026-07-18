// Self-hosted (global) Renovate config, consumed by .github/workflows/renovate.yml.
//
// This is distinct from .github/renovate.json5: that one holds the *repository*
// rules (what to update, how to group, when). This one holds settings that only
// make sense for the runner itself and that a repo config is not permitted to set.

module.exports = {
  platform: "github",
  repositories: ["jack06215/monorepo"],

  // Renovate's default author is renovate@whitesourcesoftware.com, an address
  // owned by Mend with Vigilant Mode enabled -- every commit from it lands
  // marked "Unverified". Using an identity tied to this account lets GitHub
  // attribute and sign the commits instead.
  //
  // Trade-off: dependency bumps will read as authored by you. To keep them
  // visibly bot-authored (at the cost of staying unverified), swap in:
  //   "renovate[bot] <29139614+renovate[bot]@users.noreply.github.com>"
  gitAuthor: "Jack Cho <jack06215@gmail.com>",

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
