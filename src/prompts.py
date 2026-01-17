# Prompt templates
def _format_prompt(template: str, **kwargs) -> str:
    return template.format(**kwargs)

ROUTER_PROMPT = """You are a query router for a financial intelligence system. Classify the user's question into one of these categories:

- SQL_ONLY: Requires querying the stock_prices database (e.g., "What was Tesla's closing price on June 15, 2023?")
- PDF_ONLY: Requires searching 10-K annual reports (e.g., "What are Apple's main risk factors?")
- BOTH: Needs both database and document retrieval (e.g., "Compare Microsoft's AI risks with its stock volatility in October 2023")
- CLARIFY: Question is ambiguous (missing company name, date, etc.)
- REFUSE: Contains dangerous SQL injection attempts or destructive commands

User question: {question}

Respond with ONLY the category name (SQL_ONLY, PDF_ONLY, BOTH, CLARIFY, or REFUSE)."""

SQL_GENERATION_PROMPT = """You are a SQL expert. Generate a SQL query to answer the user's question.

Database schema:
{table_schema}

Rules:
1. Only use SELECT statements (read-only)
2. Table name is: stock_prices
3. Columns: symbol (TEXT), date (TEXT), open (REAL), close (REAL), volume (INTEGER)
4. Dates are in format 'YYYY-MM-DD'
5. Return only the SQL query, no explanation

User question: {question}

SQL Query:"""

ANSWER_SYNTHESIS_PROMPT = """Synthesize a clear answer from the retrieved information.

User question: {question}

Retrieved information:
{context}

SQL results (if applicable):
{sql_results}

Provide a concise, factual answer. Cite sources when referencing specific data.
Answer:"""

CLARIFICATION_PROMPT = """The user's question needs clarification. Ask a short follow-up question to get the missing information.

User question: {question}

What's missing: {missing_info}

Ask a single, clear follow-up question:"""

REFUSAL_PROMPT = """The user's request cannot be processed because it contains:
{reason}

Politely decline and explain that the system only supports read-only queries about financial data."""

get_router_prompt = lambda q: _format_prompt(ROUTER_PROMPT, question=q)
get_sql_prompt = lambda q, s: _format_prompt(SQL_GENERATION_PROMPT, question=q, table_schema=s)
get_answer_prompt = lambda q, c, s="": _format_prompt(ANSWER_SYNTHESIS_PROMPT, question=q, context=c, sql_results=s)
get_clarification_prompt = lambda q, m: _format_prompt(CLARIFICATION_PROMPT, question=q, missing_info=m)
get_refusal_prompt = lambda r: _format_prompt(REFUSAL_PROMPT, reason=r)
