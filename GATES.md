# Gates: Anchor Developer A

OWNS: GATES.md, option-a/**, contracts/**, docs/integrations/opencode-*.md, docs/status/dev-a.md

Scope: Verify the OpenCode boundary and prepare the shared C0 contract before starting A1.

- [x] A0: OpenCode runs the same harmless sentinel tool when allowed and stops it before execution when denied
  CHECK: node option-a/audit/verify.mjs
  EXPECT: A0 sentinel verified
  EVIDENCE: automatic-evidence=v1; definition-sha256=05545a6d131f25abdfedcdd494678908b2a929c05468908bb21304323b3cc70d; exit=0; EXPECT=matched; output-sha256=3dccf4aff8c4043ff00d01d2b455dd659349cc661a13e7b8654a7690ae433faa; output-bytes=312; shell=C:\WINDOWS\system32\cmd.exe; cwd=C:\Users\harag\Documents\coding\anchor; path=f29d444f29d9/43 entries

- [x] C0A: Developer A validates the proposed shared schemas against positive and negative fixtures
  CHECK: node option-a/audit/verify-contracts.mts
  EXPECT: C0 A fixtures verified
  EVIDENCE: automatic-evidence=v1; definition-sha256=6d1c2960732cdea687ebad163a3f390125f2c2485e49a64885082736d99059a6; exit=0; EXPECT=matched; output-sha256=cf1b50eb8af381d51122f92a9bfe0d975c410d7c46f752e3091706c0b09db53c; output-bytes=26; shell=C:\WINDOWS\system32\cmd.exe; cwd=C:\Users\harag\Documents\coding\anchor; path=f29d444f29d9/43 entries

- [ ] C0: Garv's B0 and independent Python validation and both owners' approval are recorded for the same contract revision
  EVIDENCE: pending
