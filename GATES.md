# Gates: Anchor Developer A

OWNS: GATES.md, option-a/**, contracts/**, docs/integrations/opencode-*.md, docs/status/dev-a.md

Scope: Verify the OpenCode boundary, prepare the shared C0 contract, and verify A1 observation.

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

- [x] A1B: The locked TypeScript workspace compiles and its redacted events validate against C0
  CHECK: npm ci --no-audit --no-fund && npm test
  EXPECT: interleaved sessions keep independent run IDs and sequence, with redacted output
  CWD: option-a
  EVIDENCE: automatic-evidence=v1; definition-sha256=416ac5282016e30ff81625e91147f10b27907966b3bc14e95ffccd0643b97fb0; exit=0; EXPECT=matched; output-sha256=006e446721723810916974e294287853befb4ed3ba902914b9a5cea3c7c74e0e; output-bytes=871; shell=C:\WINDOWS\system32\cmd.exe; cwd=C:\Users\harag\Documents\coding\anchor\option-a; path=f29d444f29d9/43 entries

- [x] A1R: OpenCode loads the built plugin and emits schema-valid prompt and tool events with matching session and call IDs
  CHECK: npm run test:opencode
  EXPECT: A1 live observation verified
  CWD: option-a
  EVIDENCE: automatic-evidence=v1; definition-sha256=277dfc2c5f07f3c68cd550c87e5b8a9eba54084d8beb1d17223ff1fdd5987c14; exit=0; EXPECT=matched; output-sha256=9fcbfe885ac853a5fbbfd2f13f3b2169303d1d6cc347c3f03db9119d0c51d3aa; output-bytes=331; shell=C:\WINDOWS\system32\cmd.exe; cwd=C:\Users\harag\Documents\coding\anchor\option-a; path=f29d444f29d9/43 entries

- [ ] A2: Protected effects remain uncalled on denial, detector failure and exposure races
  CHECK: npm test
  EXPECT: authorization rejects missing, stale, and failed detector evidence
  CWD: option-a
  EVIDENCE: pending

- [ ] A3: Real OpenCode attempts the same controlled sink in OFF and enforce and only OFF produces a receipt
  CHECK: npm run test:policy-demo
  EXPECT: A3 policy-only sink verified
  CWD: option-a
  EVIDENCE: pending

- [ ] A4: The authenticated loopback API streams real runtime events and detector transport failures cannot authorize effects
  CHECK: npm test
  EXPECT: loopback API streams runtime events and resumes after disconnect
  CWD: option-a
  EVIDENCE: pending

- [ ] C1: The real managed service and A runtime verify generation correlation and fail-closed behavior together
  EVIDENCE: pending
