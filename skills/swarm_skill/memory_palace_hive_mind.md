---
title: Hive Memory Palace
purpose: Shared reflective log for all swarm workers
---

# Hive Memory Palace

This palace is the collective journal for your multi-worker swarm. Every worker writes to this single thread so you can trace context without chasing multiple files.

## How To Append
1. **One entry per shift** – start with \`## [Worker-ID] Planet\`.
2. **Follow the six-slot lattice** inside the entry:
   \`\`\`
   Agent: [Worker Name]
   Location: [Working Directory]
   Subject: [Core Task]
   Action: [Operation performed]
   Outcome: [Result/Artifact]
   Timing: [Timestamp/Duration]
   \`\`\`
3. **Reflection block** – bullets capturing wins, blockers, and status.
4. **Handoff note** – who should pick it up next.

## Why This Exists
The swarm's purpose is alignment: every worker understands where the Cluster → Galaxy → Sun → Planet stack stands before executing tasks. This palace acts as the daily anchor.

---
