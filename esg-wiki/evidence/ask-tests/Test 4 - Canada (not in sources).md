# Test 4 - Canada (not in sources)

**Test type:** plausible question the wiki cannot answer  
**Expected behavior:** An explicit insufficient-evidence response. None of the three sources mention Canada, so any specific Canadian rule in the answer is a failure.  
**Expected answer (written before running):** INSUFFICIENT EVIDENCE  
**Automatic answer check:** pass (citation status and expected-passage citation only; the human assessment below decides)

| Field | Value |
|---|---|
| Question | What are Canada's mandatory sustainability disclosure requirements for listed companies? |
| Mode | ask (standalone; no chat history, no persona) |
| Execution | local via Ollama 0.35.0 |
| Network at run time | **offline** |
| Model | `gemma4:e2b-it-qat` (digest `07ea59a47401`, 4.6B, Q4_0) |
| Embedding model | `embeddinggemma` (digest `85462619ee72`) |
| Retrieval | hybrid, top 5 source passages |
| Time | 2026-09-29 22:49:18 PDT |

## Retrieved passages

**[1] Global Sustainability Reporting Briefing, p.2, "4. Corporate Sustainability Reporting Directive (CSRD) and ESRS"**  
`vault/raw/Global_Sustainability_Reporting_Standards_Executive_Briefing.pdf` · id `reporting-briefing:s06c1` · BM25 rank 1 · vector rank 2 (cosine 0.4757)

> 4. Corporate Sustainability Reporting Directive (CSRD) and ESRS. The EU's mandatory sustainability
> reporting law and its technical standards. Components: Double materiality (impacts on people and
> planet, plus financial risk); 2 cross-cutting and 10 topical ESRS; mandatory limited assurance;
> digital tagging, now postponed. Revised ESRS adopted on 3 July 2026 cut mandatory datapoints by over
> 60% and total datapoints by over 70% (European Commission). In scope: EU companies with more than
> 1,000 employees and more than EUR 450m net turnover. Non-EU groups are in scope with over EUR 450m
> EU turnover and an EU subsidiary or branch above EUR 200m (Latham & Watkins). Suppliers under 1,000
> employees can decline data requests beyond a voluntary SME standard. Enforcement: Penalties set by
> each Member State; statutory auditors or accredited assurers sign off; national market regulators
> supervise listed issuers.

**[2] Global Sustainability Reporting Briefing, p.3, "7. Corporate Sustainability Due Diligence Directive (CSDDD)"**  
`vault/raw/Global_Sustainability_Reporting_Standards_Executive_Briefing.pdf` · id `reporting-briefing:s09c1` · BM25 rank 6 · vector rank 4 (cosine 0.4722)

> 7. Corporate Sustainability Due Diligence Directive (CSDDD). A conduct obligation, not only a
> disclosure one. Components: Identify, prevent and remediate adverse human rights and environmental
> impacts in the company's own operations and chain of activities, with a risk-based focus. In scope:
> EU companies with more than 5,000 employees and EUR 1.5bn net worldwide turnover, and non-EU
> companies with EUR 1.5bn EU turnover. Compliance is required from 26 July 2029 (Morrison Foerster).
> Enforcement: National supervisory authorities with administrative fines; the Omnibus narrowed the
> liability and penalty provisions (Accountancy Europe).

**[3] Global Sustainability Reporting Briefing, pp.4-5, "10. Business Responsibility and Sustainability Report (BRSR) and BRSR Core"**  
`vault/raw/Global_Sustainability_Reporting_Standards_Executive_Briefing.pdf` · id `reporting-briefing:s13c1` · BM25 rank 2 · vector rank 10 (cosine 0.4291)

> 10. Business Responsibility and Sustainability Report (BRSR) and BRSR Core. India's mandatory ESG
> report, set by the Securities and Exchange Board of India (SEBI). Components: Full BRSR covers the
> nine principles of India's National Guidelines on Responsible Business Conduct, from environment to
> employee welfare to consumer fairness. BRSR Core is a subset of nine attributes (including GHG
> emissions, water, energy, waste, gender diversity and workforce safety) that must be independently
> assessed or assured. In scope: The top 1,000 listed companies by market capitalization file the full
> BRSR. BRSR Core assessment or assurance extends to all 1,000 from FY 2026-27. Value chain
> disclosures for the top 250 are voluntary from FY 2025-26 after SEBI's March 2025 deferral
> (Sustainability 101). Enforcement: A listing obligation under SEBI's LODR Regulation 34(2)(f), filed
> with the annual report; SEBI and the stock exchanges can impose fines and other actions for non-
> compliance or misstatement.

**[4] ESG Frameworks Comparison, "Table row: CSRD"**  
`vault/raw/ESG_Frameworks.docx` · id `esg-frameworks-table:row03` · BM25 rank 10 · vector rank 3 (cosine 0.474)

> Framework/Standard: CSRD. Full Name: Corporate Sustainability Reporting Directive. Focus:
> Comprehensive sustainability reporting. Scope: EU companies and non-EU companies operating in the
> EU. Reporting Requirement: Mandatory for large EU companies, phased approach starting in 2024.
> Alignment with Other Standards: Aligned with European Green Deal, GRI. Industry-Specific Guidance:
> No, but includes sector-specific indicators. Key Features: Expands on NFRD, integrates double
> materiality (financial + sustainability impact)

**[5] Novata ESG Standards and Frameworks Guide, p.2, "IFRS"**  
`vault/raw/Novata_news.pdf` · id `novata-esg-guide:s03c1` · BM25 rank 17 · vector rank 1 (cosine 0.4864)

> The International Financial Reporting Standards (IFRS) Sustainability Disclosure Standards,
> developed by the International Sustainability Standards Board (ISSB), are designed to help investors
> and capital markets assess and disclose sustainability-related risks and opportunities. Its first
> two standards—IFRS S1 (general sustainability-related financial disclosures) and IFRS S2 (climate-
> related disclosures)—were published in 2023 and are now seeing rapid regulatory uptake, with over 36
> jurisdictions committed to aligning with them.

## Gemma's answer (verbatim)

INSUFFICIENT EVIDENCE: The provided passages do not contain information about Canada's mandatory sustainability disclosure requirements for listed companies.

## Citations

- none

## Automatic checks

- Status: **insufficient-evidence** (model reported that the sources do not contain the answer)
- Citations that point to no passage: none
- Sentences without a citation: 0

## Timing and memory

- Retrieval: 0.1 s
- Model: 4.94 s total, first token after 4.19 s, model load 0.01 s
- Tokens: 1248 prompt, 26 output (33.6 tokens/s)
- Prompt size: 779 words
- Loaded in Ollama: `gemma4:e2b-it-qat` 1.66 GB (1.66 GB in GPU memory, context 4096)
- Loaded in Ollama: `embeddinggemma:latest` 0.68 GB (0.68 GB in GPU memory, context 2048)
- Harness process peak memory: 29.5 MB

## Assessment (written by hand after opening the cited pages)

- Retrieval: returned CSRD, CSDDD, BRSR and IFRS passages; none mention Canada, which is the expected result.
- Answer: "INSUFFICIENT EVIDENCE" with no invented Canadian rules and no answer from general knowledge.
- Citations: none, which is correct for this test.
- Verdict: **pass**.
