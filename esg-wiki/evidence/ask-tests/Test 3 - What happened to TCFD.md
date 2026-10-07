# Test 3 - What happened to TCFD

**Test type:** question that connects two sources  
**Expected behavior:** Combine the Novata article and the briefing, citing both.  
**Expected answer (written before running):** The TCFD disbanded in October 2023; the IFRS Foundation incorporated its recommendations into IFRS S1 and S2, which use the four TCFD pillars. SB 261 reports may follow TCFD or ISSB, and TCFD-aligned disclosures are mandatory in jurisdictions such as the UK, Japan and New Zealand.  
**Expected source:** `vault/raw/Novata_news.pdf`, pp.3-4, section "TCFD"  
**Expected source:** `vault/raw/Global_Sustainability_Reporting_Standards_Executive_Briefing.pdf`, p.1, section 1 "ISSB Standards (IFRS S1 and S2)"; pp.3-4, section 8 (SB 261)  
**Expected passage(s) in retrieval:** `novata-esg-guide:s09c1` → rank 1, `reporting-briefing:s02c1` → rank not retrieved  
**Expected passage cited in answer:** novata-esg-guide:s09c1  
**Automatic answer check:** pass (citation status and expected-passage citation only; the human assessment below decides)

| Field | Value |
|---|---|
| Question | What happened to the TCFD, and where do its recommendations live on today? |
| Mode | ask (standalone; no chat history, no persona) |
| Execution | local via Ollama 0.35.0 |
| Network at run time | **offline** |
| Model | `gemma4:e2b-it-qat` (digest `07ea59a47401`, 4.6B, Q4_0) |
| Embedding model | `embeddinggemma` (digest `85462619ee72`) |
| Retrieval | hybrid, top 5 source passages |
| Time | 2026-09-29 22:49:13 PDT |

## Retrieved passages

**[1] Novata ESG Standards and Frameworks Guide, pp.3-4, "TCFD"**  
`vault/raw/Novata_news.pdf` · id `novata-esg-guide:s09c1` · BM25 rank 1 · vector rank 1 (cosine 0.6362)

> The Task Force for Climate-Related Disclosures (TCFD), established by the Financial Stability Board
> in 2015, was developed to guide disclosure recommendations for climate-related financial
> information. It enables companies to be more transparent on their climate-related risk exposures to
> investors, lenders and insurance underwriters. The TCFD is comprised of 11 recommendations
> structured around four pillars: governance, strategy, risk management, and metrics/targets. While
> the TCFD disbanded in October 2023, the IFRS foundation officially incorporated the full TCFD
> recommendations in its publication of IFRS S1 and S2 standards. TCFD as a framework continues to be
> the blueprint for many emerging frameworks and regulations, including California’s SB 261. TCFD-
> aligned disclosures are now mandatory in many jurisdictions globally, including the UK, Japan, and
> New Zealand.

**[2] ESG Frameworks Comparison, "Table row: TCFD"**  
`vault/raw/ESG_Frameworks.docx` · id `esg-frameworks-table:row04` · BM25 rank 2 · vector rank 2 (cosine 0.5708)

> Framework/Standard: TCFD. Full Name: Task Force on Climate-related Financial Disclosures. Focus:
> Climate-related financial risk. Scope: Global. Reporting Requirement: Voluntary, but increasingly
> adopted in mandatory disclosure regimes. Alignment with Other Standards: Aligned with SASB, CDP,
> GRI. Industry-Specific Guidance: No, general recommendations for all sectors. Key Features:
> Emphasizes financial impact of climate risks, scenario analysis

**[3] ESG Frameworks Comparison, "Table row: CDP"**  
`vault/raw/ESG_Frameworks.docx` · id `esg-frameworks-table:row06` · BM25 rank 3 · vector rank 4 (cosine 0.3345)

> Framework/Standard: CDP. Full Name: Carbon Disclosure Project. Focus: Environmental impact,
> particularly carbon emissions. Scope: Global. Reporting Requirement: Voluntary, but used by
> investors and governments. Alignment with Other Standards: Aligned with SBTi, TCFD, GRI. Industry-
> Specific Guidance: No, broad coverage across sectors. Key Features: Focuses on environmental
> disclosures, especially climate and water security

**[4] ESG Frameworks Comparison, "Table row: NFRD"**  
`vault/raw/ESG_Frameworks.docx` · id `esg-frameworks-table:row08` · BM25 rank 4 · vector rank 3 (cosine 0.3545)

> Framework/Standard: NFRD. Full Name: Non-Financial Reporting Directive. Focus: Sustainability-
> related disclosures for large companies. Scope: EU. Reporting Requirement: Mandatory for large EU
> public-interest entities. Alignment with Other Standards: Aligned with GRI, TCFD. Industry-Specific
> Guidance: No, broad applicability across sectors. Key Features: Predecessor to CSRD, focuses on non-
> financial reporting requirements in the EU

**[5] Novata ESG Standards and Frameworks Guide, p.3, "What Are ESG Frameworks?"**  
`vault/raw/Novata_news.pdf` · id `novata-esg-guide:s07c1` · BM25 rank 8 · vector rank 8 (cosine 0.2957)

> ESG frameworks provide a broad, contextual approach to ESG reporting. Rather than prescribing
> specific metrics, frameworks define the themes, objectives, and scope of sustainability reporting,
> guiding companies on what topics to address, the data to collect, and how reporting should be
> presented. ESG frameworks are largely voluntary, and widely accepted frameworks include the Task
> Force on Climate-Related Financial Disclosure (TCFD), the Carbon Disclosure Project (CDP), or the
> UN’s Sustainable Development Goals (SDGs).

## Gemma's answer (verbatim)

The Task Force for Climate-Related Disclosures (TCFD) disbanded in October 2023 [1]. The IFRS foundation officially incorporated the full TCFD recommendations in its publication of IFRS S1 and S2 standards [1]. TCFD as a framework continues to be the blueprint for many emerging frameworks and regulations, including California’s SB 261 [1]. TCFD-aligned disclosures are now mandatory in many jurisdictions globally, such as the UK, Japan, and New Zealand [1].

## Citations

- [1] Novata ESG Standards and Frameworks Guide, pp.3-4, "TCFD" → `vault/raw/Novata_news.pdf`

## Automatic checks

- Status: **cited** (every factual sentence cites a retrieved passage)
- Citations that point to no passage: none
- Sentences without a citation: 0
- Numbers in the answer:
  - 2023: in a cited passage
  - 261: in a cited passage

## Timing and memory

- Retrieval: 0.08 s
- Model: 7.31 s total, first token after 3.5 s, model load 0.01 s
- Tokens: 969 prompt, 109 output (28.5 tokens/s)
- Prompt size: 614 words
- Loaded in Ollama: `gemma4:e2b-it-qat` 1.66 GB (1.66 GB in GPU memory, context 4096)
- Loaded in Ollama: `embeddinggemma:latest` 0.68 GB (0.68 GB in GPU memory, context 2048)
- Harness process peak memory: 29.5 MB

## Assessment (written by hand after opening the cited pages)

- Retrieval: partly. The Novata TCFD section (pp.3-4) ranked 1st, but the briefing's ISSB section (p.1), which says IFRS S1 and S2 use the four TCFD pillars, was not in the top 5. The other four slots went to rows of my comparison table.
- Answer: every claim (disbanded October 2023, incorporated into IFRS S1 and S2, blueprint for SB 261, mandatory in the UK, Japan and New Zealand) is supported by Novata pp.3-4.
- Citations: correct, but all four sentences cite the same single passage [1].
- Verdict: **partial pass**. The answer is accurate but does not connect two sources, which was the point of this test. See the Reflection in the README.
