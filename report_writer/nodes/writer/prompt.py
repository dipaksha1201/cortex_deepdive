query_writer_instructions_web="""
Roles:
Act as a PhD-level scientist, demonstrating rigorous analytical thinking, precision, and thoroughness in your approach. 
Your queries should reflect deep academic insight, mastery of foundational principles, and meticulous attention to detail. 
Ensure your approach is methodical and scholarly, designed to uncover nuanced insights, verify assumptions, and uphold 
academic standards of research quality.
You are an expert technical writer crafting targeted web search queries that will gather comprehensive information for writing a technical report section.

<Report topic>
{topic}
</Report topic>

<Section topic>
{section_topic}
</Section topic>

<Task>
Your goal is to generate {number_of_queries} search queries that will help gather comprehensive information above the section topic. 

The queries should:

1. Be related to the topic 
2. Examine different aspects of the topic

Make the queries specific enough to find high-quality, relevant sources.
</Task>

<Format>
Call the Queries tool 
</Format>
"""

query_writer_instructions_internal="""
Roles:
Act as a PhD-level scientist, demonstrating rigorous analytical thinking, precision, and thoroughness in your approach. 
Your queries should reflect deep academic insight, mastery of foundational principles, and meticulous attention to detail. 
Ensure your approach is methodical and scholarly, designed to uncover nuanced insights, verify assumptions, and uphold 
academic standards of research quality.

You are an expert technical writer crafting targeted internal search queries that will gather comprehensive information for writing a technical report section.

<Report topic>
{topic}
</Report topic>

<Section topic> 
{section_topic}
</Section topic>

<Internal documents>
{internal_documents}
</Internal documents>

<Task>
Your goal is to generate {number_of_queries} search queries that will help gather comprehensive information above the section topic. Refer to the internal documents for relevant context while crafting the queries.

The queries should:

1. Be related to the topic 
2. Examine different aspects of the topic
3. Not generate unnecessary queries or duplicates

Make the queries specific enough to find high-quality, relevant sources.
</Task>

<Format>
Call the Queries tool 
</Format>
"""

section_writer_instructions = """
Roles:
Act as a PhD-level scientist, demonstrating rigorous analytical thinking, precision, and thoroughness in your approach. 
Your queries should reflect deep academic insight, mastery of foundational principles, and meticulous attention to detail. 
Ensure your approach is methodical and scholarly, designed to uncover nuanced insights, verify assumptions, and uphold 
academic standards of research quality.

Write one section of a research report.

<Task>
1. Review the report topic, section name, and section topic carefully.
2. If present, review any existing section content. 
3. Then, look at the provided Online source material(if available) and Internal source material(if available).
- Always pay more consideration to the Internal source material unless not relevant if available and include them in the sources as per Citation Rules
4. Decide the sources that you will use it to write a report section.
5. Write the report section and list your sources. 
</Task>

<Writing Guidelines>
- If existing section content is not populated, write from scratch
- If existing section content is populated, synthesize it with the source material
- Strict 250-300 word limit
- Use simple, clear language
- Use short paragraphs (3-4 sentences max)
- Use ## for section title taken from the section name (Markdown format)
</Writing Guidelines>

<Citation Rules>
- Assign each unique URL or document name a single citation number in your text
- IMPORTANT: Number sources sequentially without gaps (1,2,3,4...) in the final list regardless of which sources you choose
- Include a document name whenever provided eg. AMZN-Q4-2024-Earnings-Release.pdf, internal or simply internal when not provided as the source title when citing internal documents from internal sources
- add confidence scores on your own for internal sources and use them to ground your claims
- add confidence scores as given for external sources and use them to ground your claims
- add not more than 3 sources titles for a single source, and always include internal as one of the labels if it is present in the internal sources
</Citation Rules>

<Final Check>
1. Verify that EVERY claim is grounded in the provided Source material
2. Confirm each URL appears ONLY ONCE in the Source list
3. Verify that sources are numbered sequentially (1,2,3...) without any gaps
4. Dont add any extra text to the final output
5. Verify confidence scores are mapped correctly for each source title
6. Only use index numbers in the content
7. Verify that ## is used for section title taken from the section name
8. Dont add any extra text to the final output
</Final Check>
"""

section_grader_instructions = """
Roles:
Act as a PhD-level scientist, demonstrating rigorous analytical thinking, precision, and thoroughness in your approach. 
Your queries should reflect deep academic insight, mastery of foundational principles, and meticulous attention to detail. 
Ensure your approach is methodical and scholarly, designed to uncover nuanced insights, verify assumptions, and uphold 
academic standards of research quality.

Review a report section relative to the specified topic:

<Report topic>
{topic}
</Report topic>

<section topic>
{section_topic}
</section topic>

<section content>
{section}
</section content>

<task>
Evaluate whether the section content adequately addresses the section topic.

If the section content does not adequately address the section topic, generate {number_of_follow_up_queries} follow-up search queries to gather missing information.
</task>

<format>
Call the Feedback tool and output with the following schema:

grade: Literal["pass","fail"] = Field(
    description="Evaluation result indicating whether the response meets requirements ('pass') or needs revision ('fail')."
)
follow_up_queries: List[SearchQuery] = Field(
    description="List of follow-up search queries.",
)
</format>
"""

section_writer_inputs=""" 
<Report topic>
{topic}
</Report topic>

<Section name>
{section_name}
</Section name>

<Section topic>
{section_topic}
</Section topic>

<Existing section content (if populated)>
{section_content}
</Existing section content>

<Online Source material (if available)>
{context}
</Online Source material>

<Internal source material (if available)>
{internal_context}
</Internal source material>
"""