# Evidence and Source Use

The AI coworker should not just give an answer. It should show what
information it used. Answer the five questions below for your prototype.

## 1. What data does the AI use?

*(List the structured data your AI reads — CSVs, database tables, API
responses. Point to files in `data/` where applicable.)*

## 2. What documents does the AI use?

*(List the proprietary documents in your `rag/knowledge_base/`. What kind
of internal knowledge do they represent — policies, SOPs, product specs?)*

## 3. What tools or Python functions does the AI use?

*(List the MCP tools in `mcp_servers/` and the deterministic helpers in
`automations/`. One line per tool: name + what it does.)*

## 4. How does the user see the evidence?

*(Describe the Evidence screen in your UI. How are retrieved documents
displayed — with passage highlighting? With source links? Are tool
outputs shown as tables, JSON, or rendered prose? Can the user tell at a
glance whether the evidence supports the AI's output?)*

## 5. What happens if the evidence is missing, weak, or conflicting?

*(Describe the fallback behavior. Does the workflow block on approval?
Surface a warning? Ask the user for more input? Escalate? Be specific —
this is one of the most common real-world failure modes.)*
