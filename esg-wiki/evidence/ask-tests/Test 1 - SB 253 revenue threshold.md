# Test 1 - SB 253 revenue threshold

**Test type:** direct question answered by one source  
**Expected behavior:** Answer with the SB 253 threshold and cite the briefing.  
**Expected answer (written before running):** US-organized entities doing business in California with total annual revenue above $1bn, measured globally (SB 261 uses $500m).  
**Expected source:** `vault/raw/Global_Sustainability_Reporting_Standards_Executive_Briefing.pdf`, pp.3-4, section 8 "California SB 253 and SB 261", In scope paragraph  
**Expected passage(s) in retrieval:** `reporting-briefing:s11c1` → rank 1  
**Expected passage cited in answer:** reporting-briefing:s11c1  
**Automatic answer check:** pass (citation status and expected-passage citation only; the human assessment below decides)

| Field | Value |
|---|---|
| Question | What revenue threshold puts a company in scope of California SB 253? |
| Mode | ask (standalone; no chat history, no persona) |
| Execution | local via Ollama 0.35.0 |
| Network at run time | **offline** |
| Model | `gemma4:e2b-it-qat` (digest `07ea59a47401`, 4.6B, Q4_0) |
| Embedding model | `embeddinggemma` (digest `85462619ee72`) |
| Retrieval | hybrid, top 5 source passages |
| Time | 2026-09-29 22:48:57 PDT |

## Retrieved passages

**[1] Global Sustainability Reporting Briefing, pp.3-4, "8. California SB 253 and SB 261"**  
`vault/raw/Global_Sustainability_Reporting_Standards_Executive_Briefing.pdf` · id `reporting-briefing:s11c1` · BM25 rank 1 · vector rank 1 (cosine 0.5978)

> 8. California SB 253 and SB 261. Two companion laws administered by the California Air Resources
> Board (CARB). Components: SB 253 (Climate Corporate Data Accountability Act) requires annual Scope 1
> and 2 emissions reporting from 2026 and Scope 3 from 2027, measured under the GHG Protocol, with
> third-party assurance phasing from limited to reasonable. SB 261 (Climate-Related Financial Risk
> Act) requires a biennial public report on climate-related financial risk and mitigation, which may
> follow TCFD or ISSB. In scope: US-organized entities doing business in California with total annual
> revenue above $1bn (SB 253) or above $500m (SB 261), public or private, measured globally
> (Persefoni). Status: CARB moved the first SB 253 deadline from 10 August to 10 November 2026 and
> will not require assurance on that first report (Baker Tilly). A Ninth Circuit injunction has paused
> SB 261 enforcement since November 2025; a ruling on the First Amendment challenge was still pending
> as of August 2026. Enforcement: CARB administrative penalties of up to $500,000 per reporting year
> under SB 253 and up to $50,000 under SB 261. Scope 3 misstatements are protected by a safe harbor if
> made in good faith, and penalties for Scope 3 are limited to non-filing until 2030.

**[2] Global Sustainability Reporting Briefing, pp.1-2, "3. GHG Protocol"**  
`vault/raw/Global_Sustainability_Reporting_Standards_Executive_Briefing.pdf` · id `reporting-briefing:s04c1` · BM25 rank 2 · vector rank 3 (cosine 0.3348)

> 3. GHG Protocol. The accounting rulebook for emissions that every regime in this briefing relies on.
> Components: Corporate Standard, Scope 2 Guidance (location- and market-based methods) and Scope 3
> Standard (15 value chain categories). A revision under consultation would require hourly and
> regional matching of renewable energy certificates for market-based Scope 2 claims, with a final
> standard expected in 2027 and implementation likely from 2028 (Greenplaces). In scope: Voluntary;
> referenced directly by California SB 253, ISSB, AASB S2 and ESRS. Enforcement: None of its own;
> errors are penalized through the laws that reference it.

**[3] Global Sustainability Reporting Briefing, p.3, "7. Corporate Sustainability Due Diligence Directive (CSDDD)"**  
`vault/raw/Global_Sustainability_Reporting_Standards_Executive_Briefing.pdf` · id `reporting-briefing:s09c1` · BM25 rank 5 · vector rank 6 (cosine 0.3027)

> 7. Corporate Sustainability Due Diligence Directive (CSDDD). A conduct obligation, not only a
> disclosure one. Components: Identify, prevent and remediate adverse human rights and environmental
> impacts in the company's own operations and chain of activities, with a risk-based focus. In scope:
> EU companies with more than 5,000 employees and EUR 1.5bn net worldwide turnover, and non-EU
> companies with EUR 1.5bn EU turnover. Compliance is required from 26 July 2029 (Morrison Foerster).
> Enforcement: National supervisory authorities with administrative fines; the Omnibus narrowed the
> liability and penalty provisions (Accountancy Europe).

**[4] Global Sustainability Reporting Briefing, p.4, "9. Australian Sustainability Reporting Standards (AASB S2)"**  
`vault/raw/Global_Sustainability_Reporting_Standards_Executive_Briefing.pdf` · id `reporting-briefing:s12c1` · BM25 rank 6 · vector rank 5 (cosine 0.3084)

> 9. Australian Sustainability Reporting Standards (AASB S2). Mandatory climate reporting under
> Chapter 2M of the Corporations Act 2001, based on IFRS S2. Components: A sustainability report
> lodged with the annual report, covering governance, strategy, risk management and metrics; Scope 1
> and 2 emissions from year one and Scope 3 from year two; scenario analysis at 1.5°C and at 2.5°C or
> higher; a directors' declaration; assurance phasing from limited to reasonable. AASB S1 (general
> sustainability) is voluntary. In scope: Entities that lodge annual reports and meet two of three
> size tests, phased by group. Group 1 began with years starting 1 January 2025 (revenue A$500m,
> assets A$1bn, 500 employees). Group 2 began with years starting 1 July 2026 (A$200m, A$500m, 250
> employees). Group 3 follows from 1 July 2027 (A$50m, A$25m, 100 employees) (Carbon Impact). Large
> emitters under the National Greenhouse and Energy Reporting Act and large asset owners are also
> caught. Enforcement: ASIC, under the same civil penalty and director liability provisions as
> financial reports. A three-year "modified liability" period limits claims over Scope 3, scenario
> analysis and transition plans to ASIC-only actions (Naturaliste).

**[5] Global Sustainability Reporting Briefing, p.2, "4. Corporate Sustainability Reporting Directive (CSRD) and ESRS"**  
`vault/raw/Global_Sustainability_Reporting_Standards_Executive_Briefing.pdf` · id `reporting-briefing:s06c1` · BM25 rank 12 · vector rank 2 (cosine 0.3461)

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

## Gemma's answer (verbatim)

US-organized entities doing business in California with total annual revenue above $1bn are in scope for SB 253 [1].

## Citations

- [1] Global Sustainability Reporting Briefing, pp.3-4, "8. California SB 253 and SB 261" → `vault/raw/Global_Sustainability_Reporting_Standards_Executive_Briefing.pdf`

## Automatic checks

- Status: **cited** (every factual sentence cites a retrieved passage)
- Citations that point to no passage: none
- Sentences without a citation: 0
- Numbers in the answer:
  - $1bn: in a cited passage
  - 253: in a cited passage

## Timing and memory

- Retrieval: 1.37 s
- Model: 16.14 s total, first token after 15.24 s, model load 8.95 s
- Tokens: 1612 prompt, 29 output (32.0 tokens/s)
- Prompt size: 989 words
- Loaded in Ollama: `gemma4:e2b-it-qat` 1.66 GB (1.66 GB in GPU memory, context 4096)
- Harness process peak memory: 29.5 MB

## Assessment (written by hand after opening the cited pages)

- Retrieval: yes. The SB 253/261 section of the briefing (pp.3-4) ranked 1st.
- Answer: supported. The briefing says SB 253 covers US-organized entities doing business in California with total annual revenue above $1bn.
- Citations: correct. [1] points to the briefing, pp.3-4, section 8.
- Verdict: **pass**. The answer is short and leaves out that revenue is measured globally, but the question did not ask for that.
