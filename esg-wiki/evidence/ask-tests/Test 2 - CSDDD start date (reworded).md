# Test 2 - CSDDD start date (reworded)

**Test type:** answerable question phrased differently from the source  
**Expected behavior:** Retrieval should find the CSDDD passage even though the question never says "CSDDD" or "due diligence". Answer with the 26 July 2029 date and the size thresholds.  
**Expected answer (written before running):** Under the CSDDD, compliance is required from 26 July 2029 for EU companies with more than 5,000 employees and EUR 1.5bn net worldwide turnover, and non-EU companies with EUR 1.5bn EU turnover.  
**Expected source:** `vault/raw/Global_Sustainability_Reporting_Standards_Executive_Briefing.pdf`, p.3, section 7 "Corporate Sustainability Due Diligence Directive (CSDDD)"  
**Expected passage(s) in retrieval:** `reporting-briefing:s09c1` → rank 1  
**Expected passage cited in answer:** reporting-briefing:s09c1  
**Automatic answer check:** pass (citation status and expected-passage citation only; the human assessment below decides)

| Field | Value |
|---|---|
| Question | When do the largest European companies have to start checking their supply chains for human rights and environmental harm? |
| Mode | ask (standalone; no chat history, no persona) |
| Execution | local via Ollama 0.35.0 |
| Network at run time | **offline** |
| Model | `gemma4:e2b-it-qat` (digest `07ea59a47401`, 4.6B, Q4_0) |
| Embedding model | `embeddinggemma` (digest `85462619ee72`) |
| Retrieval | hybrid, top 5 source passages |
| Time | 2026-09-29 22:49:05 PDT |

## Retrieved passages

**[1] Global Sustainability Reporting Briefing, p.3, "7. Corporate Sustainability Due Diligence Directive (CSDDD)"**  
`vault/raw/Global_Sustainability_Reporting_Standards_Executive_Briefing.pdf` · id `reporting-briefing:s09c1` · BM25 rank 1 · vector rank 1 (cosine 0.5475)

> 7. Corporate Sustainability Due Diligence Directive (CSDDD). A conduct obligation, not only a
> disclosure one. Components: Identify, prevent and remediate adverse human rights and environmental
> impacts in the company's own operations and chain of activities, with a risk-based focus. In scope:
> EU companies with more than 5,000 employees and EUR 1.5bn net worldwide turnover, and non-EU
> companies with EUR 1.5bn EU turnover. Compliance is required from 26 July 2029 (Morrison Foerster).
> Enforcement: National supervisory authorities with administrative fines; the Omnibus narrowed the
> liability and penalty provisions (Accountancy Europe).

**[2] ESG Frameworks Comparison, "Table row: CSRD"**  
`vault/raw/ESG_Frameworks.docx` · id `esg-frameworks-table:row03` · BM25 rank 3 · vector rank 3 (cosine 0.4494)

> Framework/Standard: CSRD. Full Name: Corporate Sustainability Reporting Directive. Focus:
> Comprehensive sustainability reporting. Scope: EU companies and non-EU companies operating in the
> EU. Reporting Requirement: Mandatory for large EU companies, phased approach starting in 2024.
> Alignment with Other Standards: Aligned with European Green Deal, GRI. Industry-Specific Guidance:
> No, but includes sector-specific indicators. Key Features: Expands on NFRD, integrates double
> materiality (financial + sustainability impact)

**[3] Global Sustainability Reporting Briefing, p.2, "4. Corporate Sustainability Reporting Directive (CSRD) and ESRS"**  
`vault/raw/Global_Sustainability_Reporting_Standards_Executive_Briefing.pdf` · id `reporting-briefing:s06c1` · BM25 rank 7 · vector rank 2 (cosine 0.4901)

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

**[4] Global Sustainability Reporting Briefing, p.2, "5. EU Taxonomy Regulation"**  
`vault/raw/Global_Sustainability_Reporting_Standards_Executive_Briefing.pdf` · id `reporting-briefing:s07c1` · BM25 rank 2 · vector rank 8 (cosine 0.3569)

> 5. EU Taxonomy Regulation. A classification system defining which economic activities count as
> environmentally sustainable. Components: Six environmental objectives; an activity is "aligned" if
> it substantially contributes to one, does no significant harm to the others and meets minimum social
> safeguards. Companies report the share of turnover, CapEx and OpEx that is eligible and aligned.
> Since January 2026, activities below 10% of a KPI can be excluded from detailed assessment and
> templates are about 64% shorter (BCLP). In scope: Companies subject to CSRD (Article 8), plus
> financial market participants through SFDR. Enforcement: Through the CSRD and SFDR supervisory
> regimes above.

**[5] Global Sustainability Reporting Briefing, pp.2-3, "6. Sustainable Finance Disclosure Regulation (SFDR)"**  
`vault/raw/Global_Sustainability_Reporting_Standards_Executive_Briefing.pdf` · id `reporting-briefing:s08c1` · BM25 rank 5 · vector rank 6 (cosine 0.3668)

> 6. Sustainable Finance Disclosure Regulation (SFDR). Disclosure rules for asset managers, insurers,
> pension funds and advisers. Components: Entity-level principal adverse impact statements and product
> labels under Article 8 ("promotes" ESG) and Article 9 (sustainable objective). SFDR 2.0 would
> replace these with three categories (Sustainable, Transition and ESG Basics), each requiring 70% of
> assets to meet the category's criteria. The Council agreed its position in June 2026 and
> Parliament's committee in September 2026; trilogues are expected to start in October (RankiaPro). In
> scope: Financial market participants and advisers marketing products in the EU, including non-EU
> managers. Enforcement: National financial regulators, with ESMA coordinating; greenwashing in fund
> names and marketing is an active enforcement priority.

## Gemma's answer (verbatim)

The Corporate Sustainability Due Diligence Directive (CSDDD) requires companies to identify, prevent, and remediate adverse human rights and environmental impacts in their own operations and chain of activities, with a risk-based focus [1]. Compliance with the CSDDD is required starting 26 July 2029 [1].

## Citations

- [1] Global Sustainability Reporting Briefing, p.3, "7. Corporate Sustainability Due Diligence Directive (CSDDD)" → `vault/raw/Global_Sustainability_Reporting_Standards_Executive_Briefing.pdf`

## Automatic checks

- Status: **cited** (every factual sentence cites a retrieved passage)
- Citations that point to no passage: none
- Sentences without a citation: 0
- Numbers in the answer:
  - 26: in a cited passage
  - 2029: in a cited passage

## Timing and memory

- Retrieval: 1.91 s
- Model: 6.57 s total, first token after 4.33 s, model load 0.02 s
- Tokens: 1223 prompt, 67 output (29.8 tokens/s)
- Prompt size: 786 words
- Loaded in Ollama: `gemma4:e2b-it-qat` 1.66 GB (1.66 GB in GPU memory, context 4096)
- Loaded in Ollama: `embeddinggemma:latest` 0.68 GB (0.68 GB in GPU memory, context 2048)
- Harness process peak memory: 29.5 MB

## Assessment (written by hand after opening the cited pages)

- Retrieval: yes. The CSDDD section (briefing p.3) ranked 1st, even though the question never says "CSDDD" or "due diligence" and the source says "chain of activities" rather than "supply chains".
- Answer: the 26 July 2029 compliance date is correct and supported by [1]. It leaves out the size thresholds (more than 5,000 employees and EUR 1.5bn turnover, or EUR 1.5bn EU turnover for non-EU companies), which is the "largest companies" part of the question.
- Citations: correct. [1] points to the briefing, p.3, section 7.
- Verdict: **partial pass**. Retrieval worked on reworded language; the answer is accurate but incomplete.
